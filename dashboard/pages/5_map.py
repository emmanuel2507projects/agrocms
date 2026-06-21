"""Page 5 – Paddock Map (Folium)"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium import Popup

from dashboard.utils import show_banner, show_footer, get_session, season_selector, REGIONS
from backend.models import Paddock, Grower, HarvestRecord, Contract, SowingRecord
from datetime import date

st.set_page_config(page_title="Map – AgroCMS", layout="wide")
show_banner()
st.title("Paddock Map")

season = season_selector("map_season")
today  = date.today()

# ── Filters ────────────────────────────────────────────────────────────────────
fc1, fc2, fc3, fc4, fc5 = st.columns(5)
region_filter  = fc1.selectbox("Region",             ["All"] + REGIONS, key="map_region")
variety_filter = fc2.selectbox("Variety",            ["All", "Norman", "Latex"], key="map_variety")
perf_filter    = fc3.selectbox("Yield Performance",  ["All", "Above Average", "Average", "Below Average", "No Data"], key="map_perf")
harv_filter    = fc4.selectbox("Harvest Status",     ["All", "Harvested", "Pending"], key="map_harv")
comp_filter    = fc5.selectbox("Compliance Status",  ["All", "Compliant", "Pending"], key="map_comp")


@st.cache_data(ttl=300)
def load_map_data(season: str):
    sess = get_session()
    try:
        all_harvests = sess.query(HarvestRecord).all()
        all_yields   = [h.yield_kg_ha for h in all_harvests if h.yield_kg_ha]
        global_avg   = sum(all_yields) / len(all_yields) if all_yields else 10.5

        season_contracts    = sess.query(Contract).filter(Contract.season == season).all()
        season_contract_ids = {c.id for c in season_contracts}
        variety_by_contract = {c.id: c.variety for c in season_contracts}
        grower_by_contract  = {c.id: c.grower_id for c in season_contracts}

        features = []
        for pad in sess.query(Paddock).all():
            if not pad.geojson_coords:
                continue

            grower = sess.get(Grower, pad.grower_id)

            sow = (
                sess.query(SowingRecord)
                .filter(
                    SowingRecord.paddock_id == pad.id,
                    SowingRecord.contract_id.in_(season_contract_ids),
                )
                .first()
            )
            harv = (
                sess.query(HarvestRecord)
                .filter(
                    HarvestRecord.paddock_id == pad.id,
                    HarvestRecord.contract_id.in_(season_contract_ids),
                )
                .order_by(HarvestRecord.harvest_date.desc())
                .first()
            )

            variety      = variety_by_contract.get(sow.contract_id, "–") if sow else "–"
            yield_val    = harv.yield_kg_ha  if harv else None
            alk_idx      = harv.morphine_content_pct if harv else None
            loss_kg      = harv.loss_kg      if harv else 0
            loss_reason  = harv.loss_reason  if harv else None
            harv_date    = str(harv.harvest_date) if harv else None
            sow_date_str = str(sow.sow_date) if sow else None

            # Compliance
            recon_ok    = bool(harv.harvest_reconciliation_submitted) if harv else False
            comp_status = "Compliant" if recon_ok else "Pending"

            # Lic status for grower
            if grower and grower.licence_expiry:
                if grower.licence_expiry < today:
                    lic_status = "Expired"
                elif (grower.licence_expiry - today).days <= 30:
                    lic_status = "Expiring Soon"
                else:
                    lic_status = "Current"
            else:
                lic_status = "Unknown"

            # Colour by yield vs global average
            if yield_val is None:
                colour     = "#9e9e9e"
                perf_label = "No Data"
            elif yield_val >= global_avg * 1.05:
                colour     = "#2e7d32"
                perf_label = "Above Average"
            elif yield_val >= global_avg * 0.95:
                colour     = "#f9a825"
                perf_label = "Average"
            else:
                colour     = "#c62828"
                perf_label = "Below Average"

            harv_status = "Harvested" if harv else "Pending"

            features.append({
                "coords":      json.loads(pad.geojson_coords),
                "colour":      colour,
                "perf_label":  perf_label,
                "harv_status": harv_status,
                "comp_status": comp_status,
                "variety":     variety,
                "region":      grower.region if grower else "–",
                # popup fields
                "paddock_id":   pad.id,
                "paddock_name": pad.name,
                "grower_name":  grower.name if grower else "–",
                "licence_no":   grower.licence_no if grower else "–",
                "lic_status":   lic_status,
                "area_ha":      pad.area_ha,
                "soil_type":    pad.soil_type or "–",
                "yield_kg_ha":  yield_val,
                "alk_idx":      alk_idx,
                "sow_date":     sow_date_str,
                "harv_date":    harv_date,
                "loss_kg":      loss_kg or 0,
                "loss_reason":  loss_reason or "–",
                "lat":          pad.lat,
                "lon":          pad.lon,
            })

        return features, global_avg
    finally:
        sess.close()


features, global_avg = load_map_data(season)

if not features:
    st.warning("No paddock data found. Run `python backend/seed_data.py` first.")
    st.stop()

# ── Apply filters ──────────────────────────────────────────────────────────────
visible = features
if region_filter  != "All":
    visible = [f for f in visible if f["region"] == region_filter]
if variety_filter != "All":
    visible = [f for f in visible if f["variety"] == variety_filter]
if perf_filter    != "All":
    visible = [f for f in visible if f["perf_label"] == perf_filter]
if harv_filter    != "All":
    visible = [f for f in visible if f["harv_status"] == harv_filter]
if comp_filter    != "All":
    visible = [f for f in visible if f["comp_status"] == comp_filter]

# ── Summary strip ──────────────────────────────────────────────────────────────
s1, s2, s3, s4 = st.columns(4)
s1.metric("Paddocks Shown",     len(visible))
s2.metric("Harvested",          sum(1 for f in visible if f["harv_status"] == "Harvested"))
s3.metric("Above Average",      sum(1 for f in visible if f["perf_label"] == "Above Average"))
s4.metric("Global Avg Yield",   f"{global_avg:.2f} kg/ha")

# ── Folium map ─────────────────────────────────────────────────────────────────
m = folium.Map(location=[-41.48, 146.9], zoom_start=9, tiles="CartoDB positron")

for f in visible:
    ring = f["coords"]
    folium_coords = [[c[1], c[0]] for c in ring[:-1]]

    yield_str = f"{f['yield_kg_ha']:.2f} kg/ha" if f["yield_kg_ha"] else "No harvest data"
    alk_str   = f"{f['alk_idx']:.3f}" if f["alk_idx"] else "–"
    loss_str  = (f"{f['loss_kg']:.1f} kg ({f['loss_reason']})"
                 if f["loss_kg"] > 0 else "None recorded")

    popup_html = f"""
    <div style="font-family:Arial;font-size:12px;min-width:210px;line-height:1.6">
      <b style="font-size:13px">{f['paddock_name']}</b> &nbsp;
      <span style="color:#666;font-size:11px">ID: {f['paddock_id']}</span><br>
      <b>Grower:</b> {f['grower_name']}<br>
      <b>Licence:</b> {f['licence_no']}
      <span style="color:{'#c62828' if f['lic_status']=='Expired' else '#2e7d32'}">
        ({f['lic_status']})</span><br>
      <b>Region:</b> {f['region']} &nbsp;|&nbsp; <b>Variety:</b> {f['variety']}<br>
      <b>Area:</b> {f['area_ha']:.1f} ha &nbsp;|&nbsp; <b>Soil:</b> {f['soil_type']}<br>
      <hr style="margin:4px 0">
      <b>Sowing Date:</b> {f['sow_date'] or '–'}<br>
      <b>Harvest Date:</b> {f['harv_date'] or 'Pending'}<br>
      <b>Harvest Status:</b> {f['harv_status']}<br>
      <b>Yield:</b> {yield_str}<br>
      <b>Alkaloid Index:</b> {alk_str}<br>
      <b>Crop Loss:</b> {loss_str}<br>
      <hr style="margin:4px 0">
      <b>Compliance:</b>
      <span style="color:{'#2e7d32' if f['comp_status']=='Compliant' else '#e65100'}">
        {f['comp_status']}</span>
    </div>
    """

    folium.Polygon(
        locations=folium_coords,
        color=f["colour"], weight=1.5,
        fill=True, fill_color=f["colour"], fill_opacity=0.55,
        popup=Popup(popup_html, max_width=250),
        tooltip=f"{f['paddock_name']} | {f['grower_name']} | {yield_str}",
    ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
     background:white;padding:12px 16px;border-radius:8px;
     border:1px solid #ccc;font-family:Arial;font-size:12px;
     box-shadow:2px 2px 6px rgba(0,0,0,0.15);">
  <b style="font-size:13px">Yield Performance</b><br>
  <span style="background:#2e7d32;display:inline-block;width:14px;height:14px;
        border-radius:3px;margin:3px 6px 0 0;vertical-align:middle"></span>Above average (&ge;105%)<br>
  <span style="background:#f9a825;display:inline-block;width:14px;height:14px;
        border-radius:3px;margin:3px 6px 0 0;vertical-align:middle"></span>Average (95–105%)<br>
  <span style="background:#c62828;display:inline-block;width:14px;height:14px;
        border-radius:3px;margin:3px 6px 0 0;vertical-align:middle"></span>Below average (&lt;95%)<br>
  <span style="background:#9e9e9e;display:inline-block;width:14px;height:14px;
        border-radius:3px;margin:3px 6px 0 0;vertical-align:middle"></span>No harvest data<br>
  <hr style="margin:6px 0">
  <span style="font-size:11px;color:#888">Click any paddock for detail</span>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

st_folium(m, width="100%", height=580, returned_objects=[])

st.caption(
    f"Season: {season} · Benchmark: {global_avg:.2f} kg/ha (global avg across all seasons) · "
    "Showing " + str(len(visible)) + f" of {len(features)} paddocks based on active filters. · "
    "Coordinates are synthetic but placed in the Northern Tasmania region for demonstration purposes."
)

show_footer()
