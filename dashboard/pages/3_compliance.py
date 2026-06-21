"""Page 3 – Compliance"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import io
import csv
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from dashboard.utils import show_banner, show_footer, get_session, season_selector, badge_html
from backend.models import (
    Grower, Contract, SowingRecord, HarvestRecord, PesticideApplication, Paddock,
)
from reports.generate import licence_report_pdf, harvest_report_pdf, pesticide_log_pdf

st.set_page_config(page_title="Compliance – AgroCMS", layout="wide")
show_banner()
st.title("Compliance & Statutory Reporting")

season = season_selector("compliance_season")
today  = date.today()


@st.cache_data(ttl=300)
def load_compliance(season: str):
    sess = get_session()
    try:
        growers = sess.query(Grower).order_by(Grower.region, Grower.name).all()
        rows    = []
        issues  = []

        for g in growers:
            contracts    = [c for c in g.contracts if c.season == season]
            contract_ids = [c.id for c in contracts]

            # ── Licence status ───────────────────────────────────────────────
            if g.licence_expiry is None:
                lic_status = "AMBER"
                lic_note   = "Expiry not recorded"
            elif g.licence_expiry < today:
                lic_status = "RED"
                lic_note   = f"EXPIRED {g.licence_expiry}"
            elif (g.licence_expiry - today).days <= 30:
                lic_status = "AMBER"
                days_left  = (g.licence_expiry - today).days
                lic_note   = f"Expires in {days_left}d ({g.licence_expiry})"
            else:
                lic_status = "GREEN"
                lic_note   = str(g.licence_expiry)

            # ── Sowing declaration ──────────────────────────────────────────
            if not contract_ids:
                sow_status = "RED"
            else:
                sows = sess.query(SowingRecord).filter(
                    SowingRecord.contract_id.in_(contract_ids)
                ).all()
                if not sows:
                    sow_status = "AMBER"
                elif all(s.sowing_declaration_lodged for s in sows):
                    sow_status = "GREEN"
                else:
                    sow_status = "RED"

            # ── Harvest reconciliation ──────────────────────────────────────
            if not contract_ids:
                harv_status = "RED"
            else:
                harvs = sess.query(HarvestRecord).filter(
                    HarvestRecord.contract_id.in_(contract_ids)
                ).all()
                if not harvs:
                    harv_status = "AMBER"
                elif all(h.harvest_reconciliation_submitted for h in harvs):
                    harv_status = "GREEN"
                else:
                    harv_status = "RED"

            # ── Pesticide log / withholding period ─────────────────────────
            pad_ids = [p.id for p in g.paddocks]
            if not pad_ids:
                pest_status = "RED"
            else:
                apps = sess.query(PesticideApplication).filter(
                    PesticideApplication.paddock_id.in_(pad_ids)
                ).all()
                if not apps:
                    pest_status = "AMBER"
                else:
                    breaches = 0
                    for app in apps:
                        wh_end = app.applied_date + timedelta(days=app.withholding_days)
                        for h in sess.query(HarvestRecord).filter(
                            HarvestRecord.paddock_id == app.paddock_id,
                            HarvestRecord.contract_id.in_(contract_ids),
                        ).all():
                            if h.harvest_date and h.harvest_date < wh_end:
                                breaches += 1
                    pest_status = "RED" if breaches > 0 else "GREEN"

            # ── Crop loss report (synthetic: RED if loss_reason set) ────────
            loss_status = "GREEN"
            if contract_ids:
                for h in sess.query(HarvestRecord).filter(
                    HarvestRecord.contract_id.in_(contract_ids)
                ).all():
                    if h.loss_kg and h.loss_kg > 0 and h.loss_reason:
                        loss_status = "AMBER"
                        break

            fully = all(
                s == "GREEN"
                for s in [lic_status, sow_status, harv_status, pest_status]
            )

            row = {
                "grower_id":      g.id,
                "Grower":         g.name,
                "Region":         g.region,
                "Licence No.":    g.licence_no,
                "Licence Expiry": lic_note,
                "Licence":        lic_status,
                "Sowing Decl.":   sow_status,
                "Harvest Recon.": harv_status,
                "Pest. Log":      pest_status,
                "Crop Loss Rpt":  loss_status,
                "Fully Compliant": fully,
            }
            rows.append(row)

            # ── Build exceptions list ────────────────────────────────────────
            if lic_status == "RED":
                issues.append({
                    "Grower": g.name, "Region": g.region,
                    "Issue Type": "Expired Licence",
                    "Severity": "CRITICAL",
                    "Detail": lic_note,
                    "Action Required": "Cease operations; licence renewal required immediately",
                    "Due Date": str(today),
                })
            elif lic_status == "AMBER":
                issues.append({
                    "Grower": g.name, "Region": g.region,
                    "Issue Type": "Licence Expiring Soon",
                    "Severity": "AMBER",
                    "Detail": lic_note,
                    "Action Required": "Submit licence renewal application",
                    "Due Date": str(g.licence_expiry - timedelta(days=14)) if g.licence_expiry else "N/A",
                })
            if sow_status == "RED":
                issues.append({
                    "Grower": g.name, "Region": g.region,
                    "Issue Type": "Missing Sowing Declaration",
                    "Severity": "CRITICAL",
                    "Detail": f"One or more sowing declarations not lodged ({season})",
                    "Action Required": "Lodge sowing declaration with PACB within 7 days of sowing",
                    "Due Date": "Overdue",
                })
            if harv_status == "RED":
                issues.append({
                    "Grower": g.name, "Region": g.region,
                    "Issue Type": "Missing Harvest Reconciliation",
                    "Severity": "CRITICAL",
                    "Detail": f"Harvest reconciliation not submitted ({season})",
                    "Action Required": "Submit harvest reconciliation report",
                    "Due Date": "Overdue",
                })
            if pest_status == "RED":
                issues.append({
                    "Grower": g.name, "Region": g.region,
                    "Issue Type": "Withholding Period Breach",
                    "Severity": "CRITICAL",
                    "Detail": "Harvest recorded before pesticide withholding period expired",
                    "Action Required": "Review pesticide application records and harvest dates",
                    "Due Date": "Immediate",
                })

        return pd.DataFrame(rows), pd.DataFrame(issues)
    finally:
        sess.close()


df, issues_df = load_compliance(season)

n_compliant = int(df["Fully Compliant"].sum()) if not df.empty else 0
n_total     = len(df)
n_critical  = int((issues_df["Severity"] == "CRITICAL").sum()) if not issues_df.empty else 0
n_amber     = int((issues_df["Severity"] == "AMBER").sum())    if not issues_df.empty else 0

# ── KPI strip ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Reporting Readiness",  f"{n_compliant} / {n_total}",
          help="Growers fully compliant across all statutory checks")
k2.metric("Critical Issues",      n_critical,
          delta=f"{n_critical} require immediate action" if n_critical else None,
          delta_color="inverse")
k3.metric("Amber Alerts",         n_amber)
k4.metric("Licence Issues",
          int((df["Licence"] != "GREEN").sum()) if not df.empty else 0)
k5.metric("Pesticide Breaches",
          int((df["Pest. Log"] == "RED").sum()) if not df.empty else 0)

st.divider()

# ── Action required section ────────────────────────────────────────────────────
if not issues_df.empty:
    st.subheader("⚠️ Action Required")
    tab_crit, tab_amber = st.tabs([
        f"Critical Issues ({n_critical})",
        f"Amber Alerts ({n_amber})",
    ])

    def render_issues(sub_df):
        if sub_df.empty:
            st.success("No issues in this category.")
            return
        badge_c = {"Severity"}
        cols    = ["Grower", "Region", "Issue Type", "Severity", "Detail", "Action Required", "Due Date"]
        header  = "| " + " | ".join(cols) + " |"
        sep     = "|" + "|".join(["---"] * len(cols)) + "|"
        rows    = [header, sep]
        for _, r in sub_df.iterrows():
            cells = []
            for col in cols:
                cells.append(badge_html(str(r[col])) if col in badge_c else str(r[col]))
            rows.append("| " + " | ".join(cells) + " |")
        st.markdown("\n".join(rows), unsafe_allow_html=True)

    with tab_crit:
        render_issues(issues_df[issues_df["Severity"] == "CRITICAL"])
    with tab_amber:
        render_issues(issues_df[issues_df["Severity"] == "AMBER"])

    # Download exceptions CSV
    csv_buf = io.StringIO()
    issues_df.to_csv(csv_buf, index=False)
    st.download_button(
        "📥 Download Compliance Exceptions (CSV)",
        data=csv_buf.getvalue().encode(),
        file_name=f"compliance_exceptions_{season}.csv",
        mime="text/csv",
    )
    st.divider()
else:
    st.success("No compliance exceptions found for this season.", icon="✅")

# ── Full compliance status table ───────────────────────────────────────────────
st.subheader("Statutory Reporting Status: All Growers")
st.caption(
    "Statutory checks: Licence · Sowing Declaration · Harvest Reconciliation · "
    "Pesticide Log · Crop Loss Report. "
    "GREEN = compliant · AMBER = attention required · RED = non-compliant / overdue."
)

if not df.empty:
    display_cols = [
        "Grower", "Region", "Licence No.", "Licence Expiry",
        "Licence", "Sowing Decl.", "Harvest Recon.", "Pest. Log", "Crop Loss Rpt",
    ]
    badge_cols = {"Licence", "Sowing Decl.", "Harvest Recon.", "Pest. Log", "Crop Loss Rpt"}
    header = "| " + " | ".join(display_cols) + " |"
    sep    = "|" + "|".join(["---"] * len(display_cols)) + "|"
    md_rows = [header, sep]
    for _, row in df.iterrows():
        cells = [badge_html(str(row[c])) if c in badge_cols else str(row[c])
                 for c in display_cols]
        md_rows.append("| " + " | ".join(cells) + " |")
    st.markdown("\n".join(md_rows), unsafe_allow_html=True)

st.divider()

# ── Statutory report PDF downloads ────────────────────────────────────────────
st.subheader("Generate Statutory Reports")
st.caption("Generate PDF-format statutory reports for regulatory submission.")

grower_names    = df["Grower"].tolist() if not df.empty else []
selected_grower = st.selectbox("Select Grower", grower_names, key="pdf_grower")

if selected_grower:
    gid = int(df.loc[df["Grower"] == selected_grower, "grower_id"].iloc[0])

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**Licence Status Report**")
        st.caption("Summary of licence, contract details, and paddock allocations.")
        if st.button("Generate Licence Report", key="btn_lic"):
            with st.spinner("Generating report..."):
                sess = get_session()
                try:
                    g  = sess.get(Grower, gid)
                    cs = [c for c in g.contracts if c.season == season]
                    pdf_bytes = licence_report_pdf(g, cs, g.paddocks, season)
                finally:
                    sess.close()
            st.download_button(
                "📄 Download Licence Report",
                data=pdf_bytes,
                file_name=f"licence_{selected_grower.replace(' ','_')}_{season}.pdf",
                mime="application/pdf",
            )

    with col_b:
        st.markdown("**Harvest Reconciliation Report**")
        st.caption("Paddock-level yield summary for statutory submission.")
        if st.button("Generate Harvest Report", key="btn_harv"):
            with st.spinner("Generating report..."):
                sess = get_session()
                try:
                    g         = sess.get(Grower, gid)
                    contracts = [c for c in g.contracts if c.season == season]
                    cids      = [c.id for c in contracts]
                    harvests  = sess.query(HarvestRecord).filter(
                        HarvestRecord.contract_id.in_(cids)
                    ).all()
                    for h in harvests:
                        pad       = sess.get(Paddock, h.paddock_id)
                        contract  = sess.get(Contract, h.contract_id)
                        h.area_ha = pad.area_ha if pad else 0
                        h.variety = contract.variety if contract else "N/A"
                        h.paddock_name = pad.name if pad else "N/A"
                    price     = contracts[0].price_per_kg if contracts else 65.0
                    pdf_bytes = harvest_report_pdf(g, harvests, season, price)
                finally:
                    sess.close()
            st.download_button(
                "📄 Download Harvest Report",
                data=pdf_bytes,
                file_name=f"harvest_{selected_grower.replace(' ','_')}_{season}.pdf",
                mime="application/pdf",
            )

    with col_c:
        st.markdown("**Pesticide Use Log**")
        st.caption("Chemical application records including withholding period compliance.")
        if st.button("Generate Pesticide Log", key="btn_pest"):
            with st.spinner("Generating report..."):
                sess = get_session()
                try:
                    g         = sess.get(Grower, gid)
                    pad_ids   = [p.id for p in g.paddocks]
                    contracts = [c for c in g.contracts if c.season == season]
                    cids      = [c.id for c in contracts]
                    apps      = sess.query(PesticideApplication).filter(
                        PesticideApplication.paddock_id.in_(pad_ids)
                    ).all()

                    class _Proxy:
                        pass

                    enriched = []
                    for a in apps:
                        px_obj = _Proxy()
                        px_obj.applied_date     = a.applied_date
                        px_obj.chemical_name    = a.chemical_name
                        px_obj.rate_L_ha        = a.rate_L_ha
                        px_obj.withholding_days = a.withholding_days
                        pad = sess.get(Paddock, a.paddock_id)
                        px_obj.paddock_name = pad.name if pad else "N/A"
                        harv = (
                            sess.query(HarvestRecord)
                            .filter(
                                HarvestRecord.paddock_id == a.paddock_id,
                                HarvestRecord.contract_id.in_(cids),
                            )
                            .order_by(HarvestRecord.harvest_date.desc())
                            .first()
                        )
                        px_obj.harvest_date = harv.harvest_date if harv else None
                        enriched.append(px_obj)
                    pdf_bytes = pesticide_log_pdf(g, enriched, season)
                finally:
                    sess.close()
            st.download_button(
                "📄 Download Pesticide Log",
                data=pdf_bytes,
                file_name=f"pesticide_{selected_grower.replace(' ','_')}_{season}.pdf",
                mime="application/pdf",
            )

show_footer()
