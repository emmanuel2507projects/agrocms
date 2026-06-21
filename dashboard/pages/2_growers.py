"""Page 2 – Growers"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from dashboard.utils import (
    show_banner, show_footer, get_session,
    season_selector, badge_html, perf_band, REGIONS,
)
from backend.models import Grower, Paddock, Contract, HarvestRecord, SowingRecord

st.set_page_config(page_title="Growers – AgroCMS", layout="wide")
show_banner()
st.title("Grower Management")

season = season_selector("growers_season")
today  = date.today()

# ── Filters ────────────────────────────────────────────────────────────────────
fcol1, fcol2, fcol3, fcol4 = st.columns(4)
region_filter   = fcol1.selectbox("Region",      ["All"] + REGIONS, key="g_region")
variety_filter  = fcol2.selectbox("Variety",     ["All", "Norman", "Latex"], key="g_variety")
perf_filter     = fcol3.selectbox("Performance", ["All", "Above Target", "Watch Zone", "Under Target"], key="g_perf")
status_filter   = fcol4.selectbox("Grower Status", ["All", "Active", "Suspended"], key="g_status")


@st.cache_data(ttl=300)
def load_growers(season: str):
    sess = get_session()
    try:
        growers = sess.query(Grower).order_by(Grower.region, Grower.name).all()
        rows = []
        for g in growers:
            contracts = [c for c in g.contracts if c.season == season]
            if not contracts:
                continue  # skip growers with no contract this season

            contracted_ha = sum(c.area_contracted_ha for c in contracts)
            variety       = contracts[0].variety
            price_per_kg  = contracts[0].price_per_kg
            contract_ids  = [c.id for c in contracts]

            # Sowing records
            sowings = sess.query(SowingRecord).filter(
                SowingRecord.contract_id.in_(contract_ids)
            ).all()
            sown_ha = sum(
                (sess.get(Paddock, s.paddock_id).area_ha or 0) for s in sowings
            )

            # Harvest records
            harvests = sess.query(HarvestRecord).filter(
                HarvestRecord.contract_id.in_(contract_ids)
            ).all()

            def pad_area(pid):
                p = sess.get(Paddock, pid)
                return p.area_ha if p else 0

            harvested_ha   = sum(pad_area(h.paddock_id) for h in harvests)
            actual_yield_kg = sum(h.yield_kg_ha * pad_area(h.paddock_id) for h in harvests
                                  if h.yield_kg_ha)

            # Fulfilment vs contracted target at industry benchmark
            target_kg      = contracted_ha * 10.5   # kg/ha benchmark
            fulfilment_pct = (actual_yield_kg / target_kg * 100) if target_kg else 0

            avg_yield_kg_ha = (actual_yield_kg / harvested_ha) if harvested_ha else 0
            payment_aud     = actual_yield_kg * price_per_kg

            # Licence status
            if g.licence_expiry is None:
                lic_status = "AMBER"
            elif g.licence_expiry < today:
                lic_status = "RED"
            elif (g.licence_expiry - today).days <= 30:
                lic_status = "AMBER"
            else:
                lic_status = "GREEN"

            # Sowing declaration
            decl_ok = all(s.sowing_declaration_lodged for s in sowings) if sowings else False
            # Harvest reconciliation
            recon_ok = all(h.harvest_reconciliation_submitted for h in harvests) if harvests else True
            compliance_issues = []
            if not decl_ok:   compliance_issues.append("Sowing decl. missing")
            if not recon_ok:  compliance_issues.append("Harvest recon. missing")
            if lic_status == "RED":   compliance_issues.append("Licence expired")
            if lic_status == "AMBER": compliance_issues.append("Licence expiring")

            band = perf_band(fulfilment_pct)

            rows.append({
                "grower_id":        g.id,
                "Grower":           g.name,
                "Region":           g.region,
                "Variety":          variety,
                "Grower Status":    g.status.title(),
                "Contracted (ha)":  round(contracted_ha, 1),
                "Sown (ha)":        round(sown_ha, 1),
                "Harvested (ha)":   round(harvested_ha, 1),
                "Yield (kg/ha)":    round(avg_yield_kg_ha, 2),
                "Fulfilment %":     round(fulfilment_pct, 1),
                "Performance":      band,
                "Lic. Status":      lic_status,
                "Sowing Decl.":     "GREEN" if decl_ok else "RED",
                "Harvest Recon.":   "GREEN" if recon_ok else "RED",
                "Payment (AUD)":    round(payment_aud),
                "Price ($/kg)":     round(price_per_kg, 2),
                "Issues":           "; ".join(compliance_issues) if compliance_issues else "N/A",
                "Licence Expiry":   str(g.licence_expiry) if g.licence_expiry else "N/A",
            })

        return pd.DataFrame(rows)
    finally:
        sess.close()


df = load_growers(season)

if df.empty:
    st.warning("No grower contract data found for the selected season.")
    st.stop()

# ── Apply filters ─────────────────────────────────────────────────────────────
if region_filter  != "All":
    df = df[df["Region"] == region_filter]
if variety_filter != "All":
    df = df[df["Variety"] == variety_filter]
if perf_filter    != "All":
    band_map = {"Above Target": "GREEN", "Watch Zone": "AMBER", "Under Target": "RED"}
    df = df[df["Performance"] == band_map[perf_filter]]
if status_filter  != "All":
    df = df[df["Grower Status"] == status_filter.title()]

# ── KPI cards ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Growers (shown)",   len(df))
k2.metric("Above Target",      int((df["Performance"] == "GREEN").sum()))
k3.metric("Watch Zone",        int((df["Performance"] == "AMBER").sum()))
k4.metric("Under Target",      int((df["Performance"] == "RED").sum()))
k5.metric("Avg Fulfilment",    f"{df['Fulfilment %'].mean():.1f}%")
k6.metric("Total Payment",     f"${df['Payment (AUD)'].sum():,.0f}")

st.divider()

# ── Grower table with badge columns ───────────────────────────────────────────
st.subheader("Grower Performance & Compliance Status")

badge_cols = {"Performance", "Lic. Status", "Sowing Decl.", "Harvest Recon.", "Grower Status"}
display_cols = [
    "Grower", "Region", "Variety", "Grower Status",
    "Contracted (ha)", "Sown (ha)", "Harvested (ha)",
    "Yield (kg/ha)", "Fulfilment %", "Performance",
    "Lic. Status", "Sowing Decl.", "Harvest Recon.",
    "Payment (AUD)", "Issues",
]

header = "| " + " | ".join(display_cols) + " |"
sep    = "|" + "|".join(["---"] * len(display_cols)) + "|"
md_rows = [header, sep]

for _, row in df.iterrows():
    cells = []
    for col in display_cols:
        val = row[col]
        if col in badge_cols:
            cells.append(badge_html(str(val)))
        elif col == "Fulfilment %":
            colour = "#2e7d32" if val >= 100 else ("#e65100" if val >= 85 else "#c62828")
            cells.append(
                f'<span style="color:{colour};font-weight:600">{val:.1f}%</span>'
            )
        elif col == "Payment (AUD)":
            cells.append(f"${val:,.0f}")
        elif col == "Yield (kg/ha)":
            cells.append(f"{val:.2f}")
        elif col in ("Contracted (ha)", "Sown (ha)", "Harvested (ha)"):
            cells.append(f"{val:.1f}")
        else:
            cells.append(str(val))
    md_rows.append("| " + " | ".join(cells) + " |")

st.markdown("\n".join(md_rows), unsafe_allow_html=True)
st.caption(
    "Performance: GREEN ≥100% · AMBER 85–99% · RED <85% of contracted target "
    f"(benchmark: 10.5 kg/ha). Season: {season}."
)

st.divider()

# ── Fulfilment distribution chart ─────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Fulfilment % by Grower")
    plot_df = df[["Grower", "Fulfilment %", "Region", "Performance"]].copy()
    colour_map = {"GREEN": "#2e7d32", "AMBER": "#e65100", "RED": "#c62828"}
    plot_df["colour"] = plot_df["Performance"].map(colour_map)
    fig = px.bar(
        plot_df.sort_values("Fulfilment %"),
        x="Fulfilment %", y="Grower", orientation="h",
        color="Performance",
        color_discrete_map=colour_map,
        labels={"Fulfilment %": "Fulfilment % of Contracted Target"},
    )
    fig.add_vline(x=100, line_dash="dash", line_color="#1a1a1a",
                  annotation_text="100% target")
    fig.add_vline(x=85, line_dash="dot", line_color="#e65100",
                  annotation_text="85% threshold")
    fig.update_layout(height=max(300, len(df) * 22 + 60),
                      margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig, width="stretch")

with col_b:
    st.subheader("Average Yield by Region (kg/ha)")
    region_df = df.groupby("Region")["Yield (kg/ha)"].mean().reset_index()
    fig2 = px.bar(
        region_df.sort_values("Yield (kg/ha)"),
        x="Yield (kg/ha)", y="Region", orientation="h",
        color="Yield (kg/ha)",
        color_continuous_scale=["#c62828", "#f9a825", "#2e7d32"],
        range_color=[9.0, 12.0],
        labels={"Yield (kg/ha)": "Avg Yield (kg/ha)"},
    )
    fig2.add_vline(x=10.5, line_dash="dash", line_color="#555",
                   annotation_text="Benchmark 10.5")
    fig2.update_layout(
        coloraxis_showscale=False,
        height=300, margin=dict(l=0, r=10, t=10, b=0),
    )
    st.plotly_chart(fig2, width="stretch")

# ── Expandable per-grower detail ───────────────────────────────────────────────
st.divider()
st.subheader("Grower Detail")

for _, row in df.iterrows():
    label_colour = (
        "🟢" if row["Performance"] == "GREEN" else
        "🟡" if row["Performance"] == "AMBER" else "🔴"
    )
    with st.expander(
        f"{label_colour} {row['Grower']} | {row['Region']} "
        f"| Fulfilment: {row['Fulfilment %']:.1f}% "
        f"| Payment: ${row['Payment (AUD)']:,.0f}"
    ):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Contracted Area", f"{row['Contracted (ha)']:.1f} ha")
        c2.metric("Sown Area",       f"{row['Sown (ha)']:.1f} ha")
        c3.metric("Harvested Area",  f"{row['Harvested (ha)']:.1f} ha")
        c4.metric("Yield (kg/ha)",   f"{row['Yield (kg/ha)']:.2f}")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Fulfilment",      f"{row['Fulfilment %']:.1f}%")
        c6.metric("Price ($/kg)",    f"${row['Price ($/kg)']:.2f}")
        c7.metric("Payment (AUD)",   f"${row['Payment (AUD)']:,.0f}")
        c8.metric("Licence Expiry",  row["Licence Expiry"])

        if row["Issues"] != "N/A":
            st.warning(f"**Compliance Issues:** {row['Issues']}", icon="⚠️")
        else:
            st.success("No compliance issues for this season.", icon="✅")

show_footer()
