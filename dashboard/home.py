"""AgroCMS - homepage"""

import sys
import base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from dashboard.utils import apply_css

apply_css()


@st.cache_data(ttl=3600)
def load_hero_backdrop() -> str:
    image_path = Path(__file__).parent.parent / "assets" / "field-analytics-banner.png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
a.mod-link {
    text-decoration: none; color: inherit; display: block;
    outline-offset: 3px; border-radius: 10px;
}
a.mod-link:focus-visible { outline: 2px solid #2d6a4f; }
.module-grid {
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;
    margin-bottom: 12px;
}
.mod-card {
    background: #f8f9fa; border-radius: 8px;
    padding: 12px 14px; border-top: 2px solid rgba(45,106,79,0.55);
    height: 178px; box-sizing: border-box; cursor: pointer;
    transition: background 0.14s ease, box-shadow 0.14s ease, transform 0.14s ease;
    position: relative; overflow: hidden;
}
.mod-card:hover {
    background: #edf7f0; border-top-color: #2d6a4f;
    box-shadow: 0 3px 10px rgba(0,0,0,0.07); transform: translateY(-2px);
}
.mod-card:active { transform: translateY(0); }
.mod-badge {
    display: inline-block; padding: 3px 6px; margin-bottom: 6px;
    border-radius: 4px; background: #e8f2eb; color: #2d6a4f;
    font-size: 13px; font-weight: 800; letter-spacing: 0.06em; line-height: 1;
}
.mod-title { font-weight: 700; font-size: 20px; margin-bottom: 6px; color: #1a1a1a; line-height: 1.25; }
.mod-desc  { font-size: 17px; color: #66706b; line-height: 1.5; }
.mod-open  {
    font-size: 0.75rem; color: #2d6a4f; font-weight: 600;
    margin-top: 8px; opacity: 0;
    transition: opacity 0.14s ease; display: block;
}
.mod-card:hover .mod-open { opacity: 1; }
.mod-watermark {
    position: absolute; right: -4px; bottom: -5px; width: 82px; height: 64px;
    opacity: 0.065; color: #2d6a4f; pointer-events: none;
}
.mod-card > :not(.mod-watermark) { position: relative; z-index: 1; }
@media (max-width: 900px) { .module-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }

.hero-shell { position: relative; overflow: hidden; }
.hero-shell::after {
    content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none;
    background-image: linear-gradient(rgba(45,106,79,0.045) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(45,106,79,0.045) 1px, transparent 1px);
    background-size: 36px 36px;
    mask-image: linear-gradient(to right, transparent 0%, black 48%, black 100%);
}
.hero-backdrop {
    position: absolute; inset: 0 -4% 0 auto; width: 88%; height: 100%; z-index: 0;
    object-fit: cover; object-position: center right; opacity: 0.44;
    filter: saturate(1.08) contrast(1.04);
    -webkit-mask-image: linear-gradient(to right, transparent 0%, black 27%, black 100%);
    mask-image: linear-gradient(to right, transparent 0%, black 27%, black 100%);
}
.hero-content { position: relative; z-index: 1; }
.home-disclaimer { color: #6b746f; font-size: 15px; line-height: 1.55; margin-top: 14px; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
_pill = ("background:#e8f5e9;color:#1b5e20;border:1px solid #a5d6a7;"
         "border-radius:20px;padding:4px 13px;font-size:0.82rem;font-weight:600;"
         "display:inline-block;margin:3px 7px 3px 0")

st.markdown(f"""
<div class="hero-shell" style="background:linear-gradient(135deg,#f0f7f4 0%,#ffffff 65%);border-radius:16px;padding:38px 30px 32px;border:1px solid #ddeee6;margin-bottom:20px">
<img class="hero-backdrop" src="{load_hero_backdrop()}" alt="">
<div class="hero-content">
<div style="display:flex;align-items:flex-start;gap:24px;flex-wrap:wrap">
<div style="flex:1.8;min-width:260px">
<div style="font-size:2.8rem;font-weight:900;color:#1a2744;letter-spacing:-2px;line-height:1;margin-bottom:9px">Agro<span style="color:#2d6a4f">CMS</span></div>
<p style="font-size:22px;color:#2d6a4f;font-weight:600;margin:0 0 12px 0">Crop Performance and Compliance Dashboard</p>
<p style="font-size:18px;color:#444;line-height:1.6;margin:0 0 18px 0;max-width:520px">A synthetic portfolio project demonstrating field operations reporting, compliance monitoring, payment reconciliation, data quality checks, GIS mapping, and yield forecasting for a regulated crop management workflow.</p>
<div>
<span style="{_pill}">Data integrity</span>
<span style="{_pill}">Operational reporting</span>
<span style="{_pill}">Actionable insights</span>
</div>
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

# ── Visual separator ────────────────────────────────────────────────────────────
# ── Recommended review path ────────────────────────────────────────────────────
# ── Module cards ──────────────────────────────────────────────────────────────
st.markdown(
    "<div style='font-size:26px;font-weight:700;margin:8px 0 16px 0;color:#1a1a1a'>"
    "Dashboard Modules</div>",
    unsafe_allow_html=True,
)

_modules = [
    ("KPI", "Season Performance", "Season KPIs, regional yield and harvest progress.", "/overview", "line_chart"),
    ("GROWERS", "Grower Contracts", "Contract fulfilment, filters and payment status.", "/growers", "table_grid"),
    ("COMPLIANCE", "Compliance Readiness", "Licence tracking, statutory reporting and exceptions.", "/compliance", "checkmark"),
    ("QUALITY", "Data Quality Checks", "CMS validation checks and exception reporting.", "/data_quality", "validation_grid"),
    ("COSTS", "Payment Reconciliation", "Crop payments, cost breakdown and budget variance.", "/payments", "ledger"),
    ("ML", "Yield Forecasting", "Forecast scenarios, confidence intervals and drivers.", "/forecast", "trend_line"),
    ("GIS", "Paddock Mapping", "Paddock detail, location view and yield overlay.", "/map", "contour"),
    ("DOCS", "Methodology", "Data model, assumptions and compliance rules.", "/methodology", "network"),
]

_watermarks = {
    "line_chart": '<svg viewBox="0 0 100 70" fill="none" stroke="currentColor" stroke-width="3"><path d="M6 58L29 43 48 50 68 24 94 12"/><path d="M6 62H96"/></svg>',
    "table_grid": '<svg viewBox="0 0 100 70" fill="none" stroke="currentColor" stroke-width="2"><rect x="14" y="12" width="72" height="48" rx="3"/><path d="M14 28H86M14 44H86M38 12V60M62 12V60"/></svg>',
    "checkmark": '<svg viewBox="0 0 100 70" fill="none" stroke="currentColor" stroke-width="5"><circle cx="54" cy="35" r="24"/><path d="M40 35L50 45 69 24"/></svg>',
    "validation_grid": '<svg viewBox="0 0 100 70" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 15H82V55H18zM18 28H82M18 41H82M39 15V55M61 15V55"/><path d="M25 22l3 3 6-7M47 35l3 3 6-7M69 48l3 3 6-7"/></svg>',
    "ledger": '<svg viewBox="0 0 100 70" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 13H82V57H18zM30 25H70M30 36H70M30 47H58"/><path d="M72 13V57"/></svg>',
    "trend_line": '<svg viewBox="0 0 100 70" fill="none" stroke="currentColor" stroke-width="3"><path d="M8 58C24 53 28 45 42 47S61 34 72 29 84 17 94 11"/><path d="M8 62H96" stroke-width="2" stroke-dasharray="4 4"/></svg>',
    "contour": '<svg viewBox="0 0 100 70" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 52c15-24 29 8 43-17s28 8 43-19M8 63c17-25 31 5 45-18s28 5 39-13M17 12c12 4 18 20 31 13s14-21 34-12"/></svg>',
    "network": '<svg viewBox="0 0 100 70" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 21L49 13 77 29 62 52 29 49zM22 21l7 28m20-36l13 39m15-23L29 49"/><circle cx="22" cy="21" r="4" fill="currentColor"/><circle cx="49" cy="13" r="4" fill="currentColor"/><circle cx="77" cy="29" r="4" fill="currentColor"/><circle cx="62" cy="52" r="4" fill="currentColor"/><circle cx="29" cy="49" r="4" fill="currentColor"/></svg>',
}

_module_html = "".join(
    f'<a href="{url}" class="mod-link" aria-label="Open {title}">'
    f'<div class="mod-card">'
    f'<span class="mod-watermark">{_watermarks[watermark]}</span>'
    f'<span class="mod-badge">{badge}</span>'
    f'<div class="mod-title">{title}</div>'
    f'<div class="mod-desc">{desc}</div>'
    f'<span class="mod-open">Open module &#8594;</span>'
    f'</div></a>'
    for badge, title, desc, url, watermark in _modules
)
st.markdown(f'<div class="module-grid">{_module_html}</div>', unsafe_allow_html=True)

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="home-disclaimer">Synthetic portfolio project. Not affiliated with '
    'Extractas Bioscience, PACB, the Department of Health, or any regulator. '
    'All data is generated for demonstration purposes.</div>',
    unsafe_allow_html=True,
)
