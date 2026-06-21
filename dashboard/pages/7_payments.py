"""Page 7 – Payments & Cost Reconciliation"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.utils import show_banner, show_footer, get_session, season_selector, badge_html
from backend.models import Grower, Paddock, Contract, HarvestRecord, CropCost

st.set_page_config(page_title="Payments - AgroCMS", layout="wide")
show_banner()
st.title("Payments & Cost Reconciliation")

season = season_selector("payments_season")

# Budget benchmarks ($/ha) used for budget vs actual comparison
BUDGET_BENCHMARKS = {
    "seed":         200.0,
    "fertiliser":   375.0,
    "pesticide":    105.0,
    "contractor":   275.0,
    "irrigation":   100.0,
    "harvest_levy":   0.0,   # % of revenue; computed separately
    "admin":        1_200.0 / 50,  # ~$24/ha
}
HARVEST_LEVY_RATE = 0.03


@st.cache_data(ttl=300)
def load_payments(season: str):
    sess = get_session()
    try:
        contracts = sess.query(Contract).filter(Contract.season == season).all()
        if not contracts:
            return None

        rows = []
        cost_type_rows = []

        for c in contracts:
            g = sess.get(Grower, c.grower_id)
            if not g:
                continue

            # ── Harvest / payment ────────────────────────────────────────
            harvests = [h for h in c.harvest_records]

            def pad_area(pid):
                p = sess.get(Paddock, pid)
                return p.area_ha if p else 0

            actual_yield_kg = sum(h.yield_kg_ha * pad_area(h.paddock_id)
                                  for h in harvests if h.yield_kg_ha)
            gross_payment   = actual_yield_kg * c.price_per_kg
            recon_done      = all(h.harvest_reconciliation_submitted for h in harvests) if harvests else False
            pay_status      = "PAID" if (recon_done and harvests) else ("PENDING" if harvests else "OVERDUE")

            # ── Costs ─────────────────────────────────────────────────────
            costs    = sess.query(CropCost).filter(CropCost.contract_id == c.id).all()
            total_costs = sum(co.amount for co in costs)
            costs_by_type = {co.cost_type: co.amount for co in costs}

            # Harvest levy (3% of gross payment); already in costs
            harvest_levy_actual = costs_by_type.get("harvest_levy", 0)

            net_payment = gross_payment - total_costs
            cost_per_ha = total_costs / c.area_contracted_ha if c.area_contracted_ha else 0
            cost_per_kg = total_costs / actual_yield_kg if actual_yield_kg else 0
            gross_margin_pct = (net_payment / gross_payment * 100) if gross_payment else 0

            # Budget vs actual
            budget_total = (
                sum(BUDGET_BENCHMARKS.get(ct, 0) * c.area_contracted_ha for ct in BUDGET_BENCHMARKS)
                + gross_payment * HARVEST_LEVY_RATE
            )
            budget_variance = total_costs - budget_total

            rows.append({
                "grower_id":         g.id,
                "Grower":            g.name,
                "Region":            g.region,
                "Variety":           c.variety,
                "Contracted (ha)":   round(c.area_contracted_ha, 1),
                "Yield (kg)":        round(actual_yield_kg, 1),
                "Price ($/kg)":      round(c.price_per_kg, 2),
                "Gross Payment":     round(gross_payment),
                "Total Costs":       round(total_costs),
                "Net Payment":       round(net_payment),
                "Cost/ha":           round(cost_per_ha),
                "Cost/kg":           round(cost_per_kg, 2),
                "Gross Margin %":    round(gross_margin_pct, 1),
                "Budget Total":      round(budget_total),
                "Budget Variance":   round(budget_variance),
                "Payment Status":    pay_status,
            })

            # Per cost type
            for ct, amt in costs_by_type.items():
                cost_type_rows.append({
                    "Grower": g.name,
                    "Region": g.region,
                    "Cost Type": ct.replace("_", " ").title(),
                    "Amount ($)": round(amt),
                    "Per Ha ($/ha)": round(amt / c.area_contracted_ha, 2) if c.area_contracted_ha else 0,
                    "Budget ($/ha)": round(BUDGET_BENCHMARKS.get(ct, 0), 2),
                })

        return pd.DataFrame(rows), pd.DataFrame(cost_type_rows)
    finally:
        sess.close()


result = load_payments(season)
if result is None:
    st.warning("No contract data found for this season.")
    st.stop()

df, cost_df = result

# ── KPI strip ─────────────────────────────────────────────────────────────────
total_gross   = df["Gross Payment"].sum()
total_costs_s = df["Total Costs"].sum()
total_net     = df["Net Payment"].sum()
avg_margin    = df["Gross Margin %"].mean()
avg_cost_ha   = df["Cost/ha"].mean()
n_pending     = int((df["Payment Status"] == "PENDING").sum())

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Grower Payments", f"${total_gross:,.0f}",
          help="Sum of gross payments = yield × price for all growers")
k2.metric("Total Season Costs",    f"${total_costs_s:,.0f}")
k3.metric("Net to Growers",        f"${total_net:,.0f}")
k4.metric("Avg Gross Margin",      f"{avg_margin:.1f}%")
k5.metric("Avg Cost / ha",         f"${avg_cost_ha:,.0f}")
k6.metric("Pending Payments",      n_pending,
          delta=f"{n_pending} awaiting reconciliation" if n_pending else None,
          delta_color="inverse")

st.divider()

# ── Charts row 1 ──────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Gross Payment by Region")
    reg_df = df.groupby("Region")[["Gross Payment", "Total Costs", "Net Payment"]].sum().reset_index()
    fig = go.Figure()
    fig.add_bar(x=reg_df["Region"], y=reg_df["Gross Payment"],
                name="Gross Payment", marker_color="#2d6a4f")
    fig.add_bar(x=reg_df["Region"], y=reg_df["Total Costs"],
                name="Total Costs", marker_color="#c62828")
    fig.add_bar(x=reg_df["Region"], y=reg_df["Net Payment"],
                name="Net to Growers", marker_color="#1565c0")
    fig.update_layout(
        barmode="group",
        xaxis_title="Region", yaxis_title="AUD ($)",
        height=340, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
    )
    st.plotly_chart(fig, width="stretch")

with col2:
    st.subheader("Cost per Hectare by Region ($/ha)")
    reg_cost_df = df.groupby("Region")["Cost/ha"].mean().reset_index()
    fig2 = px.bar(
        reg_cost_df.sort_values("Cost/ha"),
        x="Cost/ha", y="Region", orientation="h",
        color="Cost/ha",
        color_continuous_scale=["#2e7d32", "#f9a825", "#c62828"],
        labels={"Cost/ha": "Avg Cost per Ha ($/ha)"},
    )
    total_budget_ha = sum(
        BUDGET_BENCHMARKS[k] for k in BUDGET_BENCHMARKS if k not in ("admin", "harvest_levy")
    )
    fig2.add_vline(x=total_budget_ha, line_dash="dash", line_color="#555",
                   annotation_text=f"Budget ${total_budget_ha:.0f}/ha")
    fig2.update_layout(
        coloraxis_showscale=False,
        height=340, margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig2, width="stretch")

# ── Budget vs Actual by cost type ─────────────────────────────────────────────
st.subheader("Budget vs Actual: Cost Categories")

if not cost_df.empty:
    bva = (
        cost_df.groupby("Cost Type")
        .agg({"Per Ha ($/ha)": "mean", "Budget ($/ha)": "mean"})
        .reset_index()
        .rename(columns={"Per Ha ($/ha)": "Actual ($/ha)", "Budget ($/ha)": "Budget ($/ha)"})
    )

    fig3 = go.Figure()
    fig3.add_bar(x=bva["Cost Type"], y=bva["Budget ($/ha)"],
                 name="Budget ($/ha)", marker_color="#90a4ae")
    fig3.add_bar(x=bva["Cost Type"], y=bva["Actual ($/ha)"],
                 name="Actual ($/ha)", marker_color="#2d6a4f")
    fig3.update_layout(
        barmode="group",
        xaxis_title="Cost Category", yaxis_title="$/ha",
        height=320, margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
    )
    st.plotly_chart(fig3, width="stretch")
    st.caption(
        "Budget benchmarks: Seed $200/ha · Fertiliser $375/ha · Pesticide $105/ha · "
        "Contractor $275/ha · Irrigation $100/ha · Harvest Levy 3% of gross payment. "
        "Actuals are from itemised CropCost records."
    )

st.divider()

# ── Grower-level payment table ─────────────────────────────────────────────────
st.subheader("Grower Payment Summary")

badge_cols_set = {"Payment Status"}
disp_cols = [
    "Grower", "Region", "Variety",
    "Contracted (ha)", "Yield (kg)", "Price ($/kg)",
    "Gross Payment", "Total Costs", "Net Payment",
    "Cost/ha", "Gross Margin %", "Budget Variance", "Payment Status",
]

header  = "| " + " | ".join(disp_cols) + " |"
sep     = "|" + "|".join(["---"] * len(disp_cols)) + "|"
md_rows = [header, sep]

for _, row in df.sort_values("Region").iterrows():
    cells = []
    for col in disp_cols:
        val = row[col]
        if col in badge_cols_set:
            cells.append(badge_html(str(val)))
        elif col in ("Gross Payment", "Total Costs", "Net Payment"):
            cells.append(f"${val:,.0f}")
        elif col == "Budget Variance":
            colour = "#c62828" if val > 0 else "#2e7d32"
            sign   = "+" if val > 0 else ""
            cells.append(
                f'<span style="color:{colour};font-weight:600">{sign}${abs(val):,.0f}</span>'
            )
        elif col == "Gross Margin %":
            colour = "#2e7d32" if val >= 30 else ("#e65100" if val >= 15 else "#c62828")
            cells.append(f'<span style="color:{colour};font-weight:600">{val:.1f}%</span>')
        elif col == "Yield (kg)":
            cells.append(f"{val:,.1f}")
        elif col in ("Cost/ha",):
            cells.append(f"${val:,.0f}")
        else:
            cells.append(str(val))
    md_rows.append("| " + " | ".join(cells) + " |")

st.markdown("\n".join(md_rows), unsafe_allow_html=True)
st.caption(
    "Budget Variance = actual costs minus budgeted costs (positive = over budget, "
    "shown in red). Gross Margin = (Gross Payment − Total Costs) / Gross Payment."
)

# ── Pending payments ───────────────────────────────────────────────────────────
pending_df = df[df["Payment Status"].isin(["PENDING", "OVERDUE"])][
    ["Grower", "Region", "Gross Payment", "Net Payment", "Payment Status"]
]
if not pending_df.empty:
    st.divider()
    st.subheader("Pending & Overdue Payments")
    st.dataframe(
        pending_df.style.format({"Gross Payment": "${:,.0f}", "Net Payment": "${:,.0f}"}),
        use_container_width=True, hide_index=True,
    )

# ── Export ─────────────────────────────────────────────────────────────────────
buf = io.StringIO()
df.to_csv(buf, index=False)
st.download_button(
    "📥 Export Payment Summary (CSV)",
    data=buf.getvalue().encode(),
    file_name=f"payments_{season}.csv",
    mime="text/csv",
)

show_footer()
