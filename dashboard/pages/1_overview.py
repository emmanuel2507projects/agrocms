"""Page 1 – Season Overview"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.utils import show_banner, show_footer, get_session, season_selector
from backend.models import Grower, Paddock, Contract, SowingRecord, HarvestRecord

st.set_page_config(page_title="Overview – AgroCMS", layout="wide")
show_banner()
BENCHMARK_YIELD_KG_HA = 10.5
st.markdown("""
<style>
[data-testid="stMetricLabel"] { font-size: 1.08rem !important; }
[data-testid="stMetricValue"] { font-size: 1.9rem !important; }
[data-testid="stCaptionContainer"] { font-size: 0.95rem !important; line-height: 1.45; }
.overview-summary { font-size: 1.08rem; line-height: 1.6; color: #52605a; margin: 2px 0 12px; }
.overview-header { position: relative; height: 132px; overflow: hidden; border-radius: 12px; border: 1px solid #dbe9df; background: #f4f8f5; margin-bottom: 14px; }
.overview-header img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center; opacity: 0.18; }
.overview-header::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(244,248,245,0.97) 0%, rgba(244,248,245,0.78) 48%, rgba(244,248,245,0.45) 100%); }
.overview-header-content { position: relative; z-index: 1; padding: 28px 30px; }
.overview-header-title { color: #1a2744; font-size: 30px; font-weight: 800; line-height: 1.1; }
.overview-header-subtitle { color: #2d6a4f; font-size: 18px; font-weight: 600; margin-top: 7px; }
[data-testid="stMainBlockContainer"] h3 { font-size: 1.35rem !important; }
[data-testid="stMainBlockContainer"] label { font-size: 1rem !important; }
</style>
""", unsafe_allow_html=True)
st.title("Season Overview")

season = season_selector("overview_season")


@st.cache_data(ttl=300)
def load_overview(season: str):
    sess = get_session()
    try:
        contracts = sess.query(Contract).filter(Contract.season == season).all()
        contract_ids = {c.id for c in contracts}
        grower_ids   = {c.grower_id for c in contracts}

        total_contracted_ha = sum(c.area_contracted_ha for c in contracts)

        harvests = sess.query(HarvestRecord).filter(
            HarvestRecord.contract_id.in_(contract_ids)
        ).all()
        sowings = sess.query(SowingRecord).filter(
            SowingRecord.contract_id.in_(contract_ids)
        ).all()

        # Total sown ha = unique paddock areas linked to sowing records.
        sown_pad_ids = {s.paddock_id for s in sowings}
        sown_areas   = [sess.get(Paddock, pid).area_ha for pid in sown_pad_ids
                        if sess.get(Paddock, pid)]
        total_sown_ha = sum(sown_areas)

        # Harvest totals
        def pad_area(pid):
            p = sess.get(Paddock, pid)
            return p.area_ha if p else 0

        def contract_price(cid):
            c = sess.get(Contract, cid)
            return c.price_per_kg if c else 65.0

        harvested_pad_ids = {h.paddock_id for h in harvests}
        harvested_ha = sum(pad_area(pid) for pid in harvested_pad_ids)
        harvest_kg  = sum(h.yield_kg_ha * pad_area(h.paddock_id) for h in harvests)
        harvest_t   = harvest_kg / 1000
        total_rev   = sum(h.yield_kg_ha * pad_area(h.paddock_id) * contract_price(h.contract_id)
                          for h in harvests)
        avg_alk_idx = (sum(h.morphine_content_pct for h in harvests) / len(harvests)
                       if harvests else 0)

        harv_pct = (harvested_ha / total_sown_ha * 100) if total_sown_ha else 0

        # Fulfilment (correct: no × 1000)
        target_kg     = total_contracted_ha * BENCHMARK_YIELD_KG_HA
        fulfilment_pct = (harvest_kg / target_kg * 100) if target_kg else 0

        # Yield by region (area-weighted)
        region_rows = []
        for h in harvests:
            pad    = sess.get(Paddock, h.paddock_id)
            grower = sess.get(Grower, pad.grower_id) if pad else None
            if pad and grower:
                region_rows.append({
                    "region":       grower.region,
                    "yield_kg_ha":  h.yield_kg_ha,
                    "area_ha":      pad.area_ha,
                })

        region_df = pd.DataFrame(region_rows)
        region_agg = pd.DataFrame()
        if not region_df.empty:
            region_df["_wy"] = region_df["yield_kg_ha"] * region_df["area_ha"]
            _agg = region_df.groupby("region").agg(
                _tot_wy=("_wy", "sum"), _tot_ha=("area_ha", "sum")
            ).reset_index()
            _agg["avg_yield_kg_ha"] = _agg["_tot_wy"] / _agg["_tot_ha"]
            region_agg = _agg[["region", "avg_yield_kg_ha"]].rename(
                columns={"region": "region"}
            )
            region_agg["performance"] = pd.cut(
                region_agg["avg_yield_kg_ha"],
                bins=[-float("inf"), BENCHMARK_YIELD_KG_HA - 0.5, BENCHMARK_YIELD_KG_HA, float("inf")],
                labels=["Below benchmark", "Near benchmark", "Above benchmark"],
            )

        # Harvest by variety
        var_rows = []
        for h in harvests:
            c = sess.get(Contract, h.contract_id)
            if c:
                var_rows.append({"variety": c.variety, "yield_kg_ha": h.yield_kg_ha})
        var_df = pd.DataFrame(var_rows)

        # Cumulative harvest progress by date
        cum_rows = []
        for h in harvests:
            pad = sess.get(Paddock, h.paddock_id)
            if pad and h.harvest_date:
                cum_rows.append({"harvest_date": h.harvest_date, "area_ha": pad.area_ha})
        cum_df = pd.DataFrame(cum_rows)
        if not cum_df.empty:
            cum_df = cum_df.sort_values("harvest_date")
            cum_df["cum_area_ha"] = cum_df["area_ha"].cumsum()

        # Grower performance counts
        grower_perfs = []
        for c in contracts:
            harv_c = [h for h in harvests if h.contract_id == c.id]
            act_kg = sum(h.yield_kg_ha * pad_area(h.paddock_id) for h in harv_c)
            tgt_kg = c.area_contracted_ha * BENCHMARK_YIELD_KG_HA
            pct    = (act_kg / tgt_kg * 100) if tgt_kg else 0
            grower_perfs.append(pct)

        return {
            "total_contracted_ha": round(total_contracted_ha, 1),
            "total_sown_ha":       round(total_sown_ha, 1),
            "harvested_ha":        round(harvested_ha, 1),
            "sown_variance_ha":    round(total_sown_ha - total_contracted_ha, 1),
            "harvest_t":           round(harvest_t, 1),
            "harvest_pct":         round(harv_pct, 1),
            "fulfilment_pct":      round(fulfilment_pct, 1),
            "avg_alk_idx":         round(avg_alk_idx, 3),
            "total_rev":           round(total_rev),
            "n_growers":           len(grower_ids),
            "n_above_target":      sum(1 for p in grower_perfs if p >= 100),
            "n_watch":             sum(1 for p in grower_perfs if 85 <= p < 100),
            "n_under":             sum(1 for p in grower_perfs if p < 85),
            "region_agg":          region_agg,
            "var_df":              var_df,
            "cum_df":              cum_df,
        }
    finally:
        sess.close()


data = load_overview(season)

# ── KPI strip ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Contracted Area",    f"{data['total_contracted_ha']:,.1f} ha")
k2.metric(
    "Total Sown Area", f"{data['total_sown_ha']:,.1f} ha",
    delta=(f"{data['sown_variance_ha']:+,.1f} ha vs contract" if data["sown_variance_ha"] else None),
    delta_color="inverse" if data["sown_variance_ha"] > 0 else "normal",
)
k3.metric("Yield (tonnes)",     f"{data['harvest_t']:,.1f} t")
k4.metric("Harvest Completion", f"{data['harvest_pct']:.1f}%")
k5.metric("Production Fulfilment", f"{data['fulfilment_pct']:.1f}%")
k6.metric("Season Revenue",     f"${data['total_rev']:,.0f}")

if data["sown_variance_ha"] > 0:
    st.warning(
        f"Sown area exceeds contracted area by {data['sown_variance_ha']:,.1f} ha. "
        "Review contract amendments or treat this as a compliance exception.",
        icon="⚠️",
    )
st.markdown(
    '<div class="overview-summary">All headline metrics use the selected season. '
    'Production fulfilment compares harvested production with contracted area at the '
    f'{BENCHMARK_YIELD_KG_HA:.1f} kg/ha benchmark. Harvest completion uses harvested area as a share of sown area.</div>',
    unsafe_allow_html=True,
)

st.divider()

# ── Grower performance strip ───────────────────────────────────────────────────
st.markdown("**Grower Performance Summary**")
p1, p2, p3 = st.columns(3)
p1.metric("Above Target (≥100%)", data["n_above_target"],
          help="Growers meeting or exceeding contracted yield target")
p2.metric("Watch Zone (85–99%)", data["n_watch"],
          help="Growers within 15% of target; monitor closely")
p3.metric("Under Target (<85%)", data["n_under"],
          delta=f"{data['n_under']} at risk" if data["n_under"] else None,
          delta_color="inverse",
          help="Growers significantly below contracted target")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Average Yield by Region (kg/ha)")
    if not data["region_agg"].empty:
        fig = px.bar(
            data["region_agg"].sort_values("avg_yield_kg_ha"),
            x="avg_yield_kg_ha", y="region", orientation="h",
            color="performance",
            color_discrete_map={
                "Above benchmark": "#2d6a4f",
                "Near benchmark": "#e8a317",
                "Below benchmark": "#c62828",
            },
            labels={"avg_yield_kg_ha": "Avg Yield (kg/ha)", "region": "Region"},
        )
        fig.add_vline(x=BENCHMARK_YIELD_KG_HA, line_dash="dash", line_color="#52605a",
                      annotation_text=f"Benchmark {BENCHMARK_YIELD_KG_HA:.1f} kg/ha",
                      annotation_position="top right")
        fig.update_layout(
            height=330, margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(title="Avg Yield (kg/ha)", range=[8, 13]),
            legend_title_text="Performance", font=dict(size=14),
        )
        st.plotly_chart(fig, width="stretch")
        st.caption("Area-weighted yield. Green is above benchmark, amber is near benchmark, and red is below benchmark.")
    else:
        st.info("No harvest data yet for this season.")

with col_right:
    st.subheader("Cumulative Harvest Progress (ha)")
    cum_df = data["cum_df"]
    if not cum_df.empty:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=cum_df["harvest_date"],
            y=cum_df["cum_area_ha"],
            mode="lines+markers",
            line=dict(color="#2d6a4f", width=2.5),
            name="Harvested (ha)",
            fill="tozeroy",
            fillcolor="rgba(45,106,79,0.12)",
        ))
        fig2.add_hline(
            y=data["total_contracted_ha"],
            line_dash="dash", line_color="#e65100",
            annotation_text=f"Contracted target: {data['total_contracted_ha']:.0f} ha",
            annotation_position="bottom right",
        )
        fig2.update_layout(
            xaxis_title="Harvest Date",
            yaxis_title="Cumulative Area (ha)",
            height=330,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            font=dict(size=14),
        )
        st.plotly_chart(fig2, width="stretch")
        st.caption("Cumulative harvested area. The dashed line marks the contracted target area.")
    else:
        st.info("No harvest records yet for this season.")

# ── Yield distribution by variety ─────────────────────────────────────────────
if not data["var_df"].empty:
    st.subheader("Yield Distribution by Variety")
    fig3 = px.box(
        data["var_df"], x="variety", y="yield_kg_ha",
        color="variety",
        color_discrete_map={"Norman": "#2d6a4f", "Latex": "#1565c0"},
        points="all",
        labels={"variety": "Variety", "yield_kg_ha": "Yield (kg/ha)"},
    )
    fig3.add_hline(y=BENCHMARK_YIELD_KG_HA, line_dash="dash", line_color="#52605a",
                   annotation_text=f"Benchmark: {BENCHMARK_YIELD_KG_HA:.1f} kg/ha")
    fig3.update_layout(
        height=330,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        font=dict(size=14),
    )
    st.plotly_chart(fig3, width="stretch")
    st.caption(f"Dashed benchmark line: {BENCHMARK_YIELD_KG_HA:.1f} kg/ha contracted production target.")
    st.caption(
        f"Alkaloid Index (avg): {data['avg_alk_idx']:.3f} "
        f"Synthetic proxy metric (0–1 scale; higher = stronger alkaloid profile). "
        "Not a regulatory measurement."
    )

show_footer()
