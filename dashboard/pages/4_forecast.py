"""Page 4 – Yield Forecast (ML)"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import io
import pickle
import csv
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

from dashboard.utils import show_banner, show_footer, get_session, REGIONS
from backend.models import HarvestRecord, Paddock, Grower, Contract
from ml.features import WEATHER, single_row, VARIETY_MAP, SOIL_MAP, REGION_MAP

st.set_page_config(page_title="Forecast – AgroCMS", layout="wide")
show_banner()
st.title("Yield Forecast")

MODEL_PATH = Path(__file__).parent.parent.parent / "ml" / "model.pkl"

# Historical input ranges from training data
HIST_RANGES = {
    "rainfall_mm":    (555, 740),
    "avg_temp_c":     (11.5, 14.1),
    "seed_rate_kg_ha":(1.2, 1.8),
    "area_ha":        (15.0, 75.0),
}


@st.cache_resource
def load_model():
    if not MODEL_PATH.exists():
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


model_data = load_model()

if model_data is None:
    st.error("Model not found. Run `python ml/train.py` to train the model first.", icon="⚠️")
    st.stop()

model  = model_data["model"]
rmse   = model_data.get("val_rmse") or model_data.get("train_rmse", 0.6)
feat_imp = model_data.get("feature_importances", {})

# Pretty feature labels
FEAT_LABELS = {
    "soil_type_enc":       "Soil type",
    "variety_enc":         "Crop variety",
    "rainfall_mm":         "Seasonal rainfall",
    "area_ha":             "Paddock area",
    "sow_date_dayofyear":  "Sowing date",
    "seed_deviation":      "Seed rate (deviation from optimal)",
    "region_enc":          "Region",
    "temp_deviation":      "Temperature (deviation from optimal)",
    "season_year":         "Season year",
}

st.success(
    f"Model: HistGradientBoostingRegressor | "
    f"Train R²: {model_data['train_r2']:.3f} | "
    f"Val R²: {model_data.get('val_r2', 'N/A'):.3f} | "
    f"Val RMSE: {rmse:.3f} kg/ha | "
    f"Trained: {model_data.get('trained_on', 'unknown')}",
    icon="✅",
)
st.caption(
    "⚠️ This is an illustrative ML model trained on synthetically generated data. "
    "Predictions should not be used for real-world agronomic decisions."
)
st.divider()

# ── Input form ────────────────────────────────────────────────────────────────
left, right = st.columns([1, 1.5])

with left:
    st.subheader("Forecast Inputs")
    with st.form("forecast_form"):
        variety   = st.selectbox("Variety",   list(VARIETY_MAP.keys()))
        soil_type = st.selectbox("Soil Type", list(SOIL_MAP.keys()))
        region    = st.selectbox("Region",    list(REGION_MAP.keys()))
        area_ha   = st.number_input("Paddock Area (ha)", min_value=5.0, max_value=200.0,
                                     value=35.0, step=0.5)
        sow_date  = st.date_input(
            "Planned Sow Date",
            value=date(2025, 11, 15),
            min_value=date(2024, 10, 1),
            max_value=date(2025, 12, 31),
        )
        season_year_fc = sow_date.year
        default_wx = WEATHER.get((region, season_year_fc), {"rainfall_mm": 630, "avg_temp_c": 12.5})

        rainfall  = st.slider("Seasonal Rainfall (mm)",  400, 900,
                               value=int(default_wx["rainfall_mm"]), step=10)
        avg_temp  = st.slider("Avg Growing Temp (°C)",   8.0, 18.0,
                               value=float(default_wx["avg_temp_c"]), step=0.1)
        seed_rate = st.slider("Seed Rate (kg/ha)",        1.0, 2.0, value=1.5, step=0.05)
        price_kg  = st.slider("Assumed Price ($/kg)",    50.0, 90.0, value=65.0, step=1.0)
        submitted = st.form_submit_button("Run Forecast", type="primary")

# ── Results ───────────────────────────────────────────────────────────────────
with right:
    if not submitted:
        st.info("Fill in the inputs on the left and click **Run Forecast**.")
        st.stop()

    # ── Range warnings ────────────────────────────────────────────────────────
    warnings = []
    if not (HIST_RANGES["rainfall_mm"][0] <= rainfall <= HIST_RANGES["rainfall_mm"][1]):
        warnings.append(
            f"Rainfall {rainfall} mm is outside the training range "
            f"({HIST_RANGES['rainfall_mm'][0]}–{HIST_RANGES['rainfall_mm'][1]} mm). "
            "Extrapolated predictions may be less reliable."
        )
    if not (HIST_RANGES["avg_temp_c"][0] <= avg_temp <= HIST_RANGES["avg_temp_c"][1]):
        warnings.append(
            f"Temperature {avg_temp} °C is outside the training range "
            f"({HIST_RANGES['avg_temp_c'][0]}–{HIST_RANGES['avg_temp_c'][1]} °C)."
        )
    if not (HIST_RANGES["seed_rate_kg_ha"][0] <= seed_rate <= HIST_RANGES["seed_rate_kg_ha"][1]):
        warnings.append(
            f"Seed rate {seed_rate} kg/ha is outside the training range "
            f"({HIST_RANGES['seed_rate_kg_ha'][0]}–{HIST_RANGES['seed_rate_kg_ha'][1]} kg/ha)."
        )
    for w in warnings:
        st.warning(w, icon="⚠️")

    # ── Base prediction ────────────────────────────────────────────────────────
    X    = single_row(variety, soil_type, region, area_ha, sow_date,
                      rainfall, avg_temp, seed_rate, season_year_fc)
    pred = float(model.predict(X)[0])
    ci_lo = max(8.0, pred - 1.645 * rmse)
    ci_hi = min(14.0, pred + 1.645 * rmse)
    rev   = pred * area_ha * price_kg

    # ── Scenario comparison ───────────────────────────────────────────────────
    opt_sow  = sow_date - timedelta(days=14) if sow_date.month >= 11 else sow_date
    cons_sow = sow_date + timedelta(days=14)

    scenarios = {
        "Conservative": {
            "rainfall": max(400, rainfall * 0.85),
            "temp":     avg_temp + 1.0,
            "seed":     1.2,
            "sow":      cons_sow,
        },
        "Base": {
            "rainfall": rainfall,
            "temp":     avg_temp,
            "seed":     seed_rate,
            "sow":      sow_date,
        },
        "Optimistic": {
            "rainfall": min(900, rainfall * 1.15),
            "temp":     avg_temp,
            "seed":     1.5,   # optimal seed rate for Tasmanian poppy
            "sow":      opt_sow,
        },
    }

    sc_preds = {}
    for sc_name, sc in scenarios.items():
        Xs = single_row(variety, soil_type, region, area_ha, sc["sow"],
                        sc["rainfall"], sc["temp"], sc["seed"], season_year_fc)
        sc_preds[sc_name] = float(model.predict(Xs)[0])

    # ── KPI metrics ───────────────────────────────────────────────────────────
    st.subheader("Forecast Result")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Predicted Yield (kg/ha)", f"{pred:.2f}")
    m2.metric("90% CI (kg/ha)",          f"{ci_lo:.1f} – {ci_hi:.1f}")
    m3.metric("Est. Total Yield",        f"{pred * area_ha / 1000:.2f} t")
    m4.metric("Est. Revenue",            f"${rev:,.0f}")

    # ── Plain-English summary ─────────────────────────────────────────────────
    hist_bench = 10.5
    delta_pct  = (pred - hist_bench) / hist_bench * 100
    sign       = "above" if delta_pct >= 0 else "below"
    abs_pct    = abs(delta_pct)

    # Use an HTML card; bare $...$ in Streamlit markdown is parsed as LaTeX
    st.markdown(
        f"<div style='background:#f0f7f4;border-left:4px solid #2d6a4f;"
        f"padding:14px 18px;border-radius:0 6px 6px 0;margin:14px 0;font-size:0.97rem'>"
        f"<strong>Forecast summary:</strong> For a <strong>{variety}</strong> crop on "
        f"<strong>{soil_type}</strong> in the <strong>{region}</strong> region "
        f"({area_ha:.0f} ha), the model forecasts <strong>{pred:.2f} kg/ha</strong> "
        f"({abs_pct:.1f}% {sign} the industry benchmark of {hist_bench} kg/ha). "
        f"At ${price_kg:.0f}/kg the estimated revenue is <strong>${rev:,.0f}</strong>. "
        f"The 90% confidence interval is <strong>{ci_lo:.1f} to {ci_hi:.1f} kg/ha</strong> "
        f"(&plusmn;{1.645 * rmse:.2f} kg/ha, based on model validation RMSE)."
        f"</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Historical comparison chart ────────────────────────────────────────────
    @st.cache_data(ttl=600)
    def hist_data(variety, region, soil_type):
        sess = get_session()
        try:
            matched, all_soils = [], []
            for h in sess.query(HarvestRecord).all():
                pad    = sess.get(Paddock, h.paddock_id)
                grower = sess.get(Grower, pad.grower_id) if pad else None
                c      = sess.get(Contract, h.contract_id)
                if c and grower and c.variety == variety and grower.region == region and h.yield_kg_ha:
                    all_soils.append({"season": c.season, "yield_kg_ha": h.yield_kg_ha,
                                      "soil_type": pad.soil_type})
                    if pad.soil_type == soil_type:
                        matched.append({"season": c.season, "yield_kg_ha": h.yield_kg_ha})
            return pd.DataFrame(matched), pd.DataFrame(all_soils)
        finally:
            sess.close()

    hist_df, hist_all = hist_data(variety, region, soil_type)

    if not hist_df.empty:
        avg_val   = hist_df["yield_kg_ha"].mean()
        bench_lbl = f"Hist. avg ({soil_type}): {avg_val:.2f} kg/ha"
        box_src   = hist_df
    elif not hist_all.empty:
        avg_val   = hist_all["yield_kg_ha"].mean()
        bench_lbl = f"Hist. avg (all soils): {avg_val:.2f} kg/ha"
        box_src   = hist_all
    else:
        avg_val   = 10.5
        bench_lbl = "Industry avg: 10.5 kg/ha"
        box_src   = pd.DataFrame()

    col_chart, col_sc = st.columns([2, 1])

    with col_chart:
        st.subheader(f"Historical vs Forecast: {variety} / {region} / {soil_type}")
        fig = go.Figure()
        if not box_src.empty:
            for s in sorted(box_src["season"].unique()):
                sub = box_src[box_src["season"] == s]
                fig.add_trace(go.Box(
                    y=sub["yield_kg_ha"], name=s,
                    marker_color="#2d6a4f", showlegend=True,
                    boxpoints="all", jitter=0.3, pointpos=-1.8, marker_size=5,
                ))
        fig.add_trace(go.Scatter(
            x=["Forecast"], y=[pred], mode="markers",
            marker=dict(color="#1565c0", size=14, symbol="diamond"),
            error_y=dict(type="data", symmetric=False,
                         array=[ci_hi - pred], arrayminus=[pred - ci_lo],
                         color="#1565c0", thickness=2.5, width=10),
            name="Forecast (base)",
        ))
        fig.add_hline(y=avg_val, line_dash="dash", line_color="#f57f17",
                      annotation_text=bench_lbl, annotation_position="top left")
        all_vals = list(box_src["yield_kg_ha"]) if not box_src.empty else [pred]
        y_min = max(0, min(min(all_vals), ci_lo) - 1)
        y_max = max(max(all_vals), ci_hi) + 1
        fig.update_layout(
            yaxis=dict(title="Yield (kg/ha)", range=[y_min, y_max]),
            height=360, margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "Box plots = historical yield distribution for the same variety and region. "
            "Diamond = base forecast. Error bars = 90% confidence interval."
        )

    with col_sc:
        st.subheader("Scenario Comparison")
        sc_df = pd.DataFrame([
            {"Scenario": k, "Yield (kg/ha)": v, "Revenue": v * area_ha * price_kg}
            for k, v in sc_preds.items()
        ])
        fig_sc = px.bar(
            sc_df, x="Scenario", y="Yield (kg/ha)",
            color="Scenario",
            color_discrete_map={
                "Conservative": "#c62828",
                "Base":          "#2d6a4f",
                "Optimistic":    "#1565c0",
            },
            text="Yield (kg/ha)",
        )
        fig_sc.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig_sc.add_hline(y=hist_bench, line_dash="dash", line_color="#555",
                         annotation_text="Benchmark")
        fig_sc.update_layout(
            height=360, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(title="Yield (kg/ha)", range=[8, max(sc_preds.values()) + 1.5]),
            showlegend=False,
        )
        st.plotly_chart(fig_sc, width="stretch")
        for _, r in sc_df.iterrows():
            st.markdown(
                f"**{r['Scenario']}:** {r['Yield (kg/ha)']:.2f} kg/ha "
                f"→ ${r['Revenue']:,.0f}"
            )
        st.caption(
            "Optimistic: +15% rainfall, optimal seed rate. "
            "Conservative: −15% rainfall, 1.2 kg/ha seed rate."
        )

    # ── Feature driver chart ───────────────────────────────────────────────────
    if feat_imp:
        st.divider()
        st.subheader("Forecast Drivers (Permutation Feature Importance)")
        imp_df = (
            pd.DataFrame({"feature": list(feat_imp.keys()), "importance": list(feat_imp.values())})
            .replace({"feature": FEAT_LABELS})
            .sort_values("importance")
        )
        fig_imp = px.bar(
            imp_df, x="importance", y="feature", orientation="h",
            color="importance",
            color_continuous_scale=["#e0e0e0", "#2d6a4f"],
            labels={"importance": "Importance (permutation)", "feature": ""},
        )
        fig_imp.update_layout(
            coloraxis_showscale=False,
            height=300, margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_imp, width="stretch")
        st.caption(
            "Permutation importance: how much model accuracy drops when each feature is "
            "randomly shuffled. Higher = more influential. Soil type and crop variety are "
            "the dominant drivers in this synthetic dataset."
        )

    # ── Export ────────────────────────────────────────────────────────────────
    st.divider()
    export_rows = [
        ["Parameter", "Value"],
        ["Variety", variety], ["Soil Type", soil_type], ["Region", region],
        ["Area (ha)", area_ha], ["Sow Date", str(sow_date)],
        ["Rainfall (mm)", rainfall], ["Avg Temp (°C)", avg_temp],
        ["Seed Rate (kg/ha)", seed_rate], ["Season Year", season_year_fc],
        [],
        ["Scenario", "Yield (kg/ha)", "Revenue (AUD)"],
    ] + [
        [k, f"{v:.3f}", f"{v * area_ha * price_kg:.0f}"]
        for k, v in sc_preds.items()
    ] + [
        [],
        ["90% CI Low (kg/ha)", f"{ci_lo:.2f}"],
        ["90% CI High (kg/ha)", f"{ci_hi:.2f}"],
        ["Model RMSE (kg/ha)", f"{rmse:.3f}"],
        ["Model Val R²", f"{model_data.get('val_r2', 'N/A')}"],
    ]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(export_rows)
    st.download_button(
        "📥 Export Forecast (CSV)",
        data=buf.getvalue().encode(),
        file_name=f"forecast_{variety}_{region}_{season_year_fc}.csv",
        mime="text/csv",
    )

show_footer()
