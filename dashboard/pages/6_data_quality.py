"""Page 6 – Data Quality & System Checks"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import io
import csv
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime

from dashboard.utils import show_banner, show_footer, get_session, season_selector, badge_html
from backend.models import (
    Grower, Paddock, Contract, SowingRecord, HarvestRecord,
    PesticideApplication, CropCost,
)

st.set_page_config(page_title="Data Quality - AgroCMS", layout="wide")
show_banner()
st.title("Data Quality & System Checks")

season = season_selector("dq_season")
today  = date.today()

st.markdown(
    "Automated validation checks simulating CMS/FOMA system integrity workflows. "
    "Checks run across growers, paddocks, contracts, sowing declarations, harvest records, "
    "pesticide logs, and payment data."
)


@st.cache_data(ttl=300)
def run_dq_checks(season: str):
    sess = get_session()
    issues = []

    try:
        growers           = sess.query(Grower).all()
        season_contracts  = sess.query(Contract).filter(Contract.season == season).all()
        sc_ids            = {c.id for c in season_contracts}
        sc_by_grower      = {}
        for c in season_contracts:
            sc_by_grower.setdefault(c.grower_id, []).append(c)

        total_records = 0

        # ── G1: Missing licence number ─────────────────────────────────────
        for g in growers:
            total_records += 1
            if not g.licence_no or g.licence_no.strip() == "":
                issues.append({
                    "Category": "Grower Record",
                    "Check": "Missing Licence Number",
                    "Entity": g.name,
                    "Region": g.region,
                    "Severity": "CRITICAL",
                    "Detail": "Licence number is null or blank",
                    "Recommended Action": "Update grower record with valid PACB licence number",
                    "Due Date": str(today),
                })

        # ── G2: Expired licence ────────────────────────────────────────────
        for g in growers:
            if g.licence_expiry and g.licence_expiry < today:
                total_records += 1
                days_expired = (today - g.licence_expiry).days
                issues.append({
                    "Category": "Grower Record",
                    "Check": "Expired Licence",
                    "Entity": g.name,
                    "Region": g.region,
                    "Severity": "CRITICAL",
                    "Detail": f"Licence expired {days_expired} day(s) ago ({g.licence_expiry})",
                    "Recommended Action": "Cease all operations. Lodge renewal application immediately.",
                    "Due Date": str(today),
                })
            elif g.licence_expiry and (g.licence_expiry - today).days <= 30:
                days_left = (g.licence_expiry - today).days
                issues.append({
                    "Category": "Grower Record",
                    "Check": "Licence Expiring Soon",
                    "Entity": g.name,
                    "Region": g.region,
                    "Severity": "WARNING",
                    "Detail": f"Licence expires in {days_left} day(s) ({g.licence_expiry})",
                    "Recommended Action": "Submit licence renewal application",
                    "Due Date": str(g.licence_expiry - timedelta(days=14)),
                })

        # ── G3: Suspended grower with active contracts ─────────────────────
        for g in growers:
            if g.status == "suspended" and g.id in sc_by_grower:
                issues.append({
                    "Category": "Grower Record",
                    "Check": "Suspended Grower: Active Contract",
                    "Entity": g.name,
                    "Region": g.region,
                    "Severity": "CRITICAL",
                    "Detail": f"Grower status = suspended but has contract for {season}",
                    "Recommended Action": "Review grower status and contract validity with compliance team",
                    "Due Date": str(today),
                })

        # ── P1: Missing paddock coordinates ────────────────────────────────
        paddocks = sess.query(Paddock).all()
        for pad in paddocks:
            total_records += 1
            if not pad.geojson_coords or not pad.lat or not pad.lon:
                g = sess.get(Grower, pad.grower_id)
                issues.append({
                    "Category": "Paddock Record",
                    "Check": "Missing Spatial Coordinates",
                    "Entity": f"{pad.name} (Grower: {g.name if g else '?'})",
                    "Region": g.region if g else "–",
                    "Severity": "WARNING",
                    "Detail": "GeoJSON boundary or lat/lon centre point is missing",
                    "Recommended Action": "Update paddock record with GPS-surveyed coordinates",
                    "Due Date": "Before next sowing season",
                })

        # ── S1: Missing sowing declaration ─────────────────────────────────
        sowings = sess.query(SowingRecord).filter(
            SowingRecord.contract_id.in_(sc_ids)
        ).all()
        total_records += len(sowings)
        for s in sowings:
            if not s.sowing_declaration_lodged:
                c = sess.get(Contract, s.contract_id)
                g = sess.get(Grower, c.grower_id) if c else None
                pad = sess.get(Paddock, s.paddock_id)
                issues.append({
                    "Category": "Sowing Declaration",
                    "Check": "Missing Sowing Declaration",
                    "Entity": g.name if g else "?",
                    "Region": g.region if g else "–",
                    "Severity": "CRITICAL",
                    "Detail": (
                        f"Paddock: {pad.name if pad else '?'}; "
                        f"Sow date: {s.sow_date}; Declaration not lodged"
                    ),
                    "Recommended Action": "Lodge sowing declaration with PACB within 7 days of sowing",
                    "Due Date": str(s.sow_date + timedelta(days=7)),
                })

        # ── S2: Sown area exceeds contracted area ──────────────────────────
        for c in season_contracts:
            g = sess.get(Grower, c.grower_id)
            c_sows = [s for s in sowings if s.contract_id == c.id]
            sown_ha = sum(
                (sess.get(Paddock, s.paddock_id).area_ha or 0) for s in c_sows
            )
            total_records += 1
            if sown_ha > c.area_contracted_ha * 1.10:
                excess = sown_ha - c.area_contracted_ha
                issues.append({
                    "Category": "Contract / Sowing",
                    "Check": "Sown Area Exceeds Contract",
                    "Entity": g.name if g else "?",
                    "Region": g.region if g else "–",
                    "Severity": "WARNING",
                    "Detail": (
                        f"Sown: {sown_ha:.1f} ha vs contracted: "
                        f"{c.area_contracted_ha:.1f} ha "
                        f"(+{excess:.1f} ha excess)"
                    ),
                    "Recommended Action": "Review and amend contract or lodge area variation notice",
                    "Due Date": "Before harvest",
                })

        # ── H1: Sowing record with no harvest record ───────────────────────
        harvests = sess.query(HarvestRecord).filter(
            HarvestRecord.contract_id.in_(sc_ids)
        ).all()
        total_records += len(harvests)
        harv_pad_ids = {h.paddock_id for h in harvests}
        for s in sowings:
            if s.paddock_id not in harv_pad_ids:
                c = sess.get(Contract, s.contract_id)
                g = sess.get(Grower, c.grower_id) if c else None
                pad = sess.get(Paddock, s.paddock_id)
                issues.append({
                    "Category": "Harvest Record",
                    "Check": "No Harvest Record for Sown Paddock",
                    "Entity": g.name if g else "?",
                    "Region": g.region if g else "–",
                    "Severity": "WARNING",
                    "Detail": (
                        f"Paddock {pad.name if pad else '?'} sown {s.sow_date} "
                        "No harvest record found"
                    ),
                    "Recommended Action": "Confirm harvest date or submit crop loss report",
                    "Due Date": "Ongoing",
                })

        # ── H2: Missing harvest reconciliation ─────────────────────────────
        for h in harvests:
            if not h.harvest_reconciliation_submitted:
                c = sess.get(Contract, h.contract_id)
                g = sess.get(Grower, c.grower_id) if c else None
                pad = sess.get(Paddock, h.paddock_id)
                issues.append({
                    "Category": "Harvest Record",
                    "Check": "Missing Harvest Reconciliation",
                    "Entity": g.name if g else "?",
                    "Region": g.region if g else "–",
                    "Severity": "CRITICAL",
                    "Detail": (
                        f"Paddock: {pad.name if pad else '?'}; "
                        f"Harvest: {h.harvest_date}"
                    ),
                    "Recommended Action": "Submit harvest reconciliation form within 14 days of harvest",
                    "Due Date": str(h.harvest_date + timedelta(days=14)) if h.harvest_date else "Overdue",
                })

        # ── H3: Yield outside expected range ──────────────────────────────
        for h in harvests:
            if h.yield_kg_ha is not None and not (8.0 <= h.yield_kg_ha <= 14.0):
                c = sess.get(Contract, h.contract_id)
                g = sess.get(Grower, c.grower_id) if c else None
                issues.append({
                    "Category": "Harvest Record",
                    "Check": "Yield Outside Expected Range",
                    "Entity": g.name if g else "?",
                    "Region": g.region if g else "–",
                    "Severity": "WARNING",
                    "Detail": (
                        f"Recorded yield {h.yield_kg_ha:.2f} kg/ha; "
                        "expected range 8–14 kg/ha"
                    ),
                    "Recommended Action": "Verify field measurement; correct if data entry error",
                    "Due Date": "Immediate",
                })

        # ── PS1: Pesticide application – missing applicator ────────────────
        pest_apps = sess.query(PesticideApplication).all()
        total_records += len(pest_apps)
        for a in pest_apps:
            if not a.applicator_id or a.applicator_id.strip() == "":
                pad = sess.get(Paddock, a.paddock_id)
                g   = sess.get(Grower, pad.grower_id) if pad else None
                issues.append({
                    "Category": "Pesticide Log",
                    "Check": "Missing Pesticide Applicator ID",
                    "Entity": g.name if g else "?",
                    "Region": g.region if g else "–",
                    "Severity": "WARNING",
                    "Detail": (
                        f"Application of {a.chemical_name} on {a.applied_date} "
                        "Applicator ID not recorded"
                    ),
                    "Recommended Action": "Update pesticide log with licensed applicator ID",
                    "Due Date": "Before submission",
                })

        # ── PS2: Withholding period breach ─────────────────────────────────
        for a in pest_apps:
            wh_end = a.applied_date + timedelta(days=a.withholding_days)
            pad    = sess.get(Paddock, a.paddock_id)
            g      = sess.get(Grower, pad.grower_id) if pad else None
            for h in sess.query(HarvestRecord).filter(
                HarvestRecord.paddock_id == a.paddock_id,
                HarvestRecord.contract_id.in_(sc_ids),
            ).all():
                if h.harvest_date and h.harvest_date < wh_end:
                    days_short = (wh_end - h.harvest_date).days
                    issues.append({
                        "Category": "Pesticide Log",
                        "Check": "Withholding Period Breach",
                        "Entity": g.name if g else "?",
                        "Region": g.region if g else "–",
                        "Severity": "CRITICAL",
                        "Detail": (
                            f"{a.chemical_name} applied {a.applied_date} "
                            f"(WHP {a.withholding_days}d, expires {wh_end}); "
                            f"harvested {h.harvest_date} ({days_short}d early)"
                        ),
                        "Recommended Action": "Report to PACB immediately; batch may require re-testing",
                        "Due Date": str(today),
                    })

        # ── C1: Crop cost record without harvest record ─────────────────────
        costs = sess.query(CropCost).filter(CropCost.contract_id.in_(sc_ids)).all()
        total_records += len(costs)
        cost_cids = {cost.contract_id for cost in costs}
        harv_cids = {h.contract_id for h in harvests}
        for cid in cost_cids - harv_cids:
            c = sess.get(Contract, cid)
            g = sess.get(Grower, c.grower_id) if c else None
            issues.append({
                "Category": "Payment / Cost",
                "Check": "Cost Record Without Harvest Record",
                "Entity": g.name if g else "?",
                "Region": g.region if g else "–",
                "Severity": "WARNING",
                "Detail": "Crop cost entries exist but no corresponding harvest record found",
                "Recommended Action": "Verify harvest status; may indicate in-progress crop",
                "Due Date": "Confirm before payment processing",
            })

    finally:
        sess.close()

    return pd.DataFrame(issues), total_records


issues_df, total_records = run_dq_checks(season)

# ── KPI strip ─────────────────────────────────────────────────────────────────
n_critical = int((issues_df["Severity"] == "CRITICAL").sum()) if not issues_df.empty else 0
n_warning  = int((issues_df["Severity"] == "WARNING").sum())  if not issues_df.empty else 0
n_issues   = len(issues_df)
clean_pct  = max(0, (total_records - n_issues) / total_records * 100) if total_records else 100

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Records Checked", f"{total_records:,}")
k2.metric("Critical Issues",       n_critical,
          delta=f"{n_critical} require action" if n_critical else None,
          delta_color="inverse")
k3.metric("Warning Issues",        n_warning)
k4.metric("Clean Records",         f"{clean_pct:.1f}%")
k5.metric("Last Validation Run",   str(datetime.now().strftime("%Y-%m-%d %H:%M")))

st.divider()

if issues_df.empty:
    st.success("All checks passed; no data quality issues found.", icon="✅")
else:
    # ── Tabs by category ──────────────────────────────────────────────────────
    cats = ["All"] + sorted(issues_df["Category"].unique().tolist())
    tab_labels = [f"{c} ({len(issues_df) if c == 'All' else (issues_df['Category'] == c).sum()})"
                  for c in cats]
    tabs = st.tabs(tab_labels)

    badge_cols_set = {"Severity"}
    display_cols   = ["Check", "Entity", "Region", "Severity", "Detail", "Recommended Action", "Due Date"]

    for tab, cat in zip(tabs, cats):
        with tab:
            sub = issues_df if cat == "All" else issues_df[issues_df["Category"] == cat]
            if sub.empty:
                st.success("No issues in this category.")
                continue
            header  = "| " + " | ".join(display_cols) + " |"
            sep     = "|" + "|".join(["---"] * len(display_cols)) + "|"
            md_rows = [header, sep]
            for _, row in sub.sort_values("Severity").iterrows():
                cells = [
                    badge_html(str(row[c])) if c in badge_cols_set else str(row[c])
                    for c in display_cols
                ]
                md_rows.append("| " + " | ".join(cells) + " |")
            st.markdown("\n".join(md_rows), unsafe_allow_html=True)

    st.divider()

    # ── Download exceptions report ─────────────────────────────────────────────
    buf = io.StringIO()
    issues_df.to_csv(buf, index=False)
    st.download_button(
        "📥 Download DQ Exceptions Report (CSV)",
        data=buf.getvalue().encode(),
        file_name=f"data_quality_exceptions_{season}.csv",
        mime="text/csv",
    )

    # ── Summary by category ────────────────────────────────────────────────────
    st.subheader("Issues by Category")
    cat_summary = (
        issues_df.groupby(["Category", "Severity"])
        .size()
        .reset_index(name="Count")
        .pivot(index="Category", columns="Severity", values="Count")
        .fillna(0)
        .astype(int)
        .reset_index()
    )
    st.dataframe(cat_summary, use_container_width=True, hide_index=True)

st.caption(
    "Checks run automatically against the live CMS database. "
    "All issues identified are based on synthetic data and are for demonstration purposes only. "
    f"Season: {season}"
)

show_footer()
