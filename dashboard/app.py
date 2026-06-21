"""AgroCMS navigation shell."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import DB_PATH, init_db, SessionLocal
from backend.models import Base  # noqa: F401

def _bootstrap_db():
    if not DB_PATH.exists():
        init_db()
        from backend.seed_data import seed
        sess = SessionLocal()
        try:
            seed(sess)
        finally:
            sess.close()

_bootstrap_db()

st.set_page_config(
    page_title="AgroCMS",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("home.py", title="Home", default=True),
    st.Page("pages/1_overview.py", title="Executive Overview", url_path="overview"),
    st.Page("pages/2_growers.py", title="Growers and Contracts", url_path="growers"),
    st.Page("pages/3_compliance.py", title="Compliance", url_path="compliance"),
    st.Page("pages/4_forecast.py", title="Yield Forecast", url_path="forecast"),
    st.Page("pages/5_map.py", title="Paddock Map", url_path="map"),
    st.Page("pages/6_data_quality.py", title="Data Quality", url_path="data_quality"),
    st.Page("pages/7_payments.py", title="Payments", url_path="payments"),
    st.Page("pages/8_methodology.py", title="Methodology", url_path="methodology"),
])
pg.run()
