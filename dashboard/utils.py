"""Shared utilities for all Streamlit dashboard pages."""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from backend.database import SessionLocal

SEASONS = ["2022-23", "2023-24", "2024-25"]
REGIONS = ["Westbury", "Deloraine", "Longford", "Perth", "Latrobe"]

BRAND_GREEN = "#2d6a4f"
BRAND_AMBER = "#e65100"
BRAND_RED   = "#c62828"

_CSS = """
<style>
/* ── Sidebar ── */
[data-testid="stSidebarNavLink"] span {
    font-size: 18px !important;
    font-weight: 500 !important;
}
[data-testid="stSidebarNavLink"] {
    padding: 0.4rem 0.75rem !important;
}
/* ── Metric cards ── */
div[data-testid="metric-container"] {
    background: #ffffff;
    border-radius: 8px;
    padding: 12px 16px !important;
    border-left: 3px solid #2d6a4f;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
}
div[data-testid="metric-container"].amber { border-left-color: #e65100; }
div[data-testid="metric-container"].red   { border-left-color: #c62828; }
/* ── Footer ── */
.page-footer {
    margin-top: 40px;
    padding-top: 12px;
    border-top: 1px solid #e0e0e0;
    font-size: 0.74rem;
    color: #aaa;
    text-align: left;
}
</style>
"""


def apply_css():
    """Inject shared CSS. Call once per page before any other output."""
    st.markdown(_CSS, unsafe_allow_html=True)


def show_banner():
    """Legacy name; now just applies shared CSS. No info banner on inner pages."""
    apply_css()


def show_footer():
    """Render a subtle synthetic-data disclaimer footer."""
    st.markdown(
        '<div class="page-footer">'
        "AgroCMS &middot; Synthetic portfolio project &middot; "
        "Not affiliated with Extractas Bioscience, PACB, or any real regulatory body &middot; "
        "All data is algorithmically generated for demonstration purposes only"
        "</div>",
        unsafe_allow_html=True,
    )


def get_session():
    return SessionLocal()


def season_selector(key: str = "season") -> str:
    return st.selectbox("Season", SEASONS, index=2, key=key)


def badge_html(status: str) -> str:
    cfg = {
        "GREEN":      ("#e8f5e9", "#2e7d32"),
        "AMBER":      ("#fff8e1", "#e65100"),
        "RED":        ("#ffebee", "#c62828"),
        "ACTIVE":     ("#e8f5e9", "#2e7d32"),
        "SUSPENDED":  ("#ffebee", "#c62828"),
        "INACTIVE":   ("#f5f5f5", "#666"),
        "PASS":       ("#e8f5e9", "#2e7d32"),
        "FAIL":       ("#ffebee", "#c62828"),
        "WARNING":    ("#fff8e1", "#e65100"),
        "PAID":       ("#e8f5e9", "#2e7d32"),
        "PENDING":    ("#fff8e1", "#e65100"),
        "OVERDUE":    ("#ffebee", "#c62828"),
        "CRITICAL":   ("#ffebee", "#c62828"),
        "INFO":       ("#e3f2fd", "#1565c0"),
    }
    bg, fg = cfg.get(status.upper(), ("#f5f5f5", "#333"))
    label = status.replace("_", " ").title()
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;'
        f"border-radius:12px;font-weight:600;font-size:0.80em;white-space:nowrap\">"
        f"{label}</span>"
    )


def perf_band(pct: float) -> str:
    """Return GREEN / AMBER / RED performance band string."""
    if pct >= 100:
        return "GREEN"
    if pct >= 85:
        return "AMBER"
    return "RED"
