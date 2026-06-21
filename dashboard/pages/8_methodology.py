"""Page 8 – Methodology & About This Project"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dashboard.utils import show_banner, show_footer

st.set_page_config(page_title="Methodology - AgroCMS", layout="wide")
show_banner()
st.title("Methodology & About This Project")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Project Overview",
    "Data Model",
    "Synthetic Data",
    "ML Forecasting",
    "Compliance Rules",
])

# ── Tab 1: Project Overview ────────────────────────────────────────────────────
with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
## Purpose

AgroCMS is a **portfolio project** that simulates an operational analytics dashboard for a
pharmaceutical poppy crop management system. It is designed to demonstrate the skills and
domain knowledge relevant to a **Field Operations Data Analyst** role in a regulated
agricultural environment.

The project does **not** represent any real company, operator, or regulatory system.

---

## Business Problem Simulated

A pharmaceutical crop processor requires end-to-end operational visibility across **20 contracted
growers**, **50 paddocks**, and **3 growing seasons**. Field operations staff need a single
system to track sowing declarations, harvest reconciliation, pesticide compliance, grower
payments, and data quality. All workflows are subject to regulatory reporting obligations.

**Key operational questions this system answers:**

- Which growers are meeting their contracted yield targets?
- Are all statutory sowing declarations and harvest reconciliations lodged on time?
- Are there any pesticide withholding period breaches before harvest?
- Which payments are pending or overdue, and what is the budget vs actual cost variance?
- What data quality issues exist in the CMS that need resolution?
- What yield should we forecast for the coming season given current conditions?

---

## Crop Operations Workflow

The dashboard represents the operational sequence from grower contracts through sowing,
field monitoring, compliance checks, harvest reconciliation, payment review, and yield
forecasting. Each stage uses the same synthetic grower, paddock, contract, and season data
so a reviewer can trace a record across the application.

1. **Grower contracts** establish the season, variety, contracted area, and price.
2. **Sowing records** capture field activity and declaration status.
3. **Field monitoring** brings paddock locations and crop data into view.
4. **Compliance checks** identify licence, reporting, and pesticide log exceptions.
5. **Harvest reconciliation** compares harvested area and yield with contracted targets.
6. **Payment review** reconciles grower payments, costs, and budget variance.
7. **Forecasting** tests crop yield under conservative, base, and optimistic scenarios.

---

## Target Role Alignment

| Skill Area | Demonstrated By |
|---|---|
| Crop management systems | Multipage CMS dashboard with contracts, paddocks, seasons |
| Field operations reporting | Sowing declarations, harvest reconciliation, pesticide logs |
| Statutory compliance | Licence status, withholding period breach detection |
| Grower payment reconciliation | Contracted vs actual yield, cost-per-ha modelling |
| Data quality checks | Automated validation checks across all entity types |
| Yield forecasting / ML | HistGBR with monotonic constraints and confidence intervals |
| Spatial data | Folium choropleth map with paddock polygons and popups |
| PDF reporting | Jinja2/WeasyPrint statutory report generation |
| Python / SQL | SQLAlchemy ORM, Streamlit, pandas, plotly |

---

## Technical Stack

| Layer | Technology |
|---|---|
| Backend / ORM | Python, SQLAlchemy 2.0, SQLite |
| Dashboard | Streamlit 1.x multipage app |
| Visualisation | Plotly Express and Graph Objects |
| Machine Learning | scikit-learn HistGradientBoostingRegressor |
| Geospatial | Folium and streamlit-folium |
| PDF Reports | Jinja2 and WeasyPrint (HTML fallback) |
| Data Storage | SQLite (single file, portable) |
| Reproducibility | Fixed random seed (42) throughout |

---

## Tools and Skills

| Skill | What is demonstrated |
|---|---|
| Data modelling | SQLAlchemy ORM, 7-table relational schema with foreign keys and cascades |
| Python and SQL | ETL pipelines, complex joins, aggregations, data quality checks |
| Streamlit | Multipage dashboard with interactive filters, session caching and form widgets |
| Machine learning | HistGradientBoosting with monotonic constraints, permutation importance, cross-validation |
| Geospatial | Folium choropleth map, paddock polygon rendering, rich popups |
| PDF reporting | Jinja2 templates, WeasyPrint statutory report generation |
| Compliance logic | Licence expiry tracking, withholding period breach detection, exception triage |
| Financial reconciliation | Payment calculation, cost-per-ha analysis, budget vs actual variance |

---

## Data Model Summary

| Table | Rows | Description |
|---|---|---|
| `growers` | 20 | Contracted growers across 5 regions |
| `paddocks` | 50 | Physical paddocks with GeoJSON coordinates |
| `contracts` | 60 | One contract per grower per season |
| `sowing_records` | 150 | Sowing declaration dates and seed rates |
| `harvest_records` | 145 | Yield, alkaloid index, losses and reconciliation status |
| `pesticide_applications` | 455 | Chemical applications with withholding periods |
| `crop_costs` | 420 | Seven itemised cost categories per contract |

See the **Data Model** tab for the full schema and relationship diagram.
""")

    with col_b:
        st.markdown("""
## Limitations & Assumptions

- All data is **synthetically generated** and does not represent real growers, yields,
  or regulatory decisions.
- Coordinate polygons are approximately placed in the Northern Tasmania region
  using a mathematical model; they are not based on real cadastral data.
- The ML model is trained on ~100 synthetic training records and is intended as an
  **illustrative proof-of-concept**, not a production forecasting system.
- Compliance rules are simplified representations of statutory obligations and do
  not constitute legal or regulatory advice.
- Financial figures (prices, costs, payments) are generated within realistic
  Tasmanian industry ranges but are not sourced from any real dataset.
- The Alkaloid Index is a synthetic proxy metric; it does not represent real alkaloid
  content measurements.

---

## Acknowledgements

This project draws on publicly available information about the Tasmanian poppy industry,
including production area estimates and general agronomic benchmarks published by the
Tasmanian Department of Primary Industries and Water, and Poppy Australia.

The project is **not affiliated with** and makes no representation about:
- Extractas Bioscience Pty Ltd
- Tasmanian Alkaloids Pty Ltd
- Poppy Australia Pty Ltd
- PACB (Poppy Advisory and Control Board)
- Any real regulatory authority
""")

# ── Tab 2: Data Model ──────────────────────────────────────────────────────────
with tab2:
    st.markdown("""
## Database Schema

AgroCMS uses a **7-table relational schema** implemented with SQLAlchemy ORM backed by SQLite.

```
growers
  ├── id (PK)          name          licence_no       region
  ├── status           contact_email  licence_expiry
  ├── → paddocks (1:N)
  └── → contracts (1:N)

paddocks
  ├── id (PK)          grower_id (FK)   name          area_ha
  ├── soil_type        geojson_coords   lat           lon
  ├── → sowing_records (1:N)
  ├── → harvest_records (1:N)
  └── → pesticide_applications (1:N)

contracts
  ├── id (PK)          grower_id (FK)   season        variety
  ├── area_contracted_ha                price_per_kg
  ├── → sowing_records (1:N)
  ├── → harvest_records (1:N)
  └── → crop_costs (1:N)

sowing_records
  ├── id (PK)          paddock_id (FK)  contract_id (FK)
  ├── sow_date         seed_rate_kg_ha  status
  └── sowing_declaration_lodged

harvest_records
  ├── id (PK)          paddock_id (FK)  contract_id (FK)
  ├── harvest_date     yield_kg_ha      morphine_content_pct
  ├── loss_kg          loss_reason
  └── harvest_reconciliation_submitted

pesticide_applications
  ├── id (PK)          paddock_id (FK)
  ├── applied_date     chemical_name    rate_L_ha
  ├── withholding_days applicator_id
  └── [withholding period end = applied_date + withholding_days]

crop_costs
  ├── id (PK)          contract_id (FK)
  ├── cost_type        amount           recorded_date
  └── [types: seed, fertiliser, pesticide, contractor, irrigation, harvest_levy, admin]
```

## Key Relationships

- **1 Grower → N Contracts** (one per season)
- **1 Grower → N Paddocks** (physical fields; persist across seasons)
- **1 Contract → N Sowing Records** (one per paddock farmed under that contract)
- **1 Contract → N Harvest Records** (one per paddock harvested)
- **1 Contract → N Crop Costs** (one row per cost category)
- **1 Paddock → N Pesticide Applications** (across all seasons)

## Key Calculations

| Metric | Formula |
|---|---|
| Actual Yield (kg) | Σ (yield_kg_ha × paddock.area_ha) for all harvests |
| Contracted Target (kg) | contract.area_contracted_ha × 10.5 kg/ha benchmark |
| Fulfilment % | Actual Yield ÷ Contracted Target × 100 |
| Gross Payment | Σ (yield_kg_ha × area_ha × price_per_kg) |
| Cost per ha | Total CropCosts ÷ area_contracted_ha |
| Withholding breach | harvest_date < applied_date + withholding_days |
""")

# ── Tab 3: Synthetic Data ──────────────────────────────────────────────────────
with tab3:
    st.markdown("""
## Synthetic Data Generation

All data is generated in `backend/seed_data.py` using a fixed random seed (42)
for full reproducibility.

### Coverage

| Entity | Count | Notes |
|---|---|---|
| Growers | 20 | 4 per region; 1 suspended |
| Paddocks | 50 | 10 growers with 3 paddocks; 10 growers with 2 |
| Seasons | 3 | 2022-23, 2023-24, 2024-25 |
| Contracts | 60 | 1 per grower per season |
| Sowing Records | 150 | 1 per paddock per season |
| Harvest Records | 145 | ~5% of 2024-25 paddocks in-progress (no harvest yet) |
| Pesticide Applications | 455 | 2–4 per paddock per season |
| Crop Cost Rows | 420 | 7 cost types × 60 contracts |

### Yield Formula

```python
base     = {"Norman": 10.5, "Latex": 9.8}[variety]       # kg/ha
soil_mod = {"Red Ferrosol": 0.8, "Brown Dermosol": 0.0,
            "Grey Vertosol": -0.5}[soil_type]
rain_mod = (rainfall_mm - 650) × 0.003
temp_mod = -|avg_temp_c - 12.0| × 0.08
seed_mod = -|seed_rate_kg_ha - 1.5| × 0.5
noise    = Gaussian(0, 0.45)

yield_kg_ha = clip(base + soil_mod + rain_mod + temp_mod + seed_mod + noise, 8.0, 14.0)
```

### Intentional Data Quality Issues

The synthetic dataset deliberately includes a small number of data quality issues
to demonstrate the Data Quality module:

| Issue | How introduced |
|---|---|
| Expired licences | 2 growers (indices 18–19) have past expiry dates |
| Expiring licences | 2 growers (indices 2, 11) expire within 30 days |
| Missing sowing declaration | Growers where `grower_id % 7 == 0` for current season |
| Missing harvest reconciliation | Growers where `grower_id % 11 == 0` for current season |
| Missing harvest records | ~15% of 2024-25 paddocks randomly skipped |
| Suspended grower with contract | 1 grower (Wendy Farrell) is suspended |

### Regions & Weather

| Region | Lat/Lon centre | Rainfall range (mm) | Avg Temp (°C) |
|---|---|---|---|
| Westbury | -41.53, 146.85 | 585–695 | 12.3–13.0 |
| Deloraine | -41.52, 146.65 | 640–720 | 11.8–12.4 |
| Longford | -41.60, 147.11 | 560–610 | 13.2–13.8 |
| Perth | -41.57, 147.18 | 555–605 | 13.5–14.1 |
| Latrobe | -41.24, 146.42 | 695–740 | 11.5–12.0 |
""")

# ── Tab 4: ML Forecasting ──────────────────────────────────────────────────────
with tab4:
    st.markdown("""
## Yield Forecasting Model

### Algorithm

**HistGradientBoostingRegressor** (scikit-learn 1.5): a histogram-based gradient boosting
regressor that supports native monotonic constraints.

```python
model = HistGradientBoostingRegressor(
    max_iter=200,
    max_depth=4,
    learning_rate=0.05,
    random_state=42,
    min_samples_leaf=8,
    monotonic_cst={
        "rainfall_mm":    +1,   # more rainfall → higher yield
        "temp_deviation": -1,   # deviation from 12.5°C → lower yield
        "seed_deviation": -1,   # deviation from 1.5 kg/ha → lower yield
    },
)
```

### Features

| Feature | Type | Note |
|---|---|---|
| `soil_type_enc` | Categorical | Red Ferrosol=0, Brown Dermosol=1, Grey Vertosol=2 |
| `variety_enc` | Categorical | Norman=0, Latex=1 |
| `rainfall_mm` | Continuous | Seasonal rainfall; monotonic (+) constraint |
| `area_ha` | Continuous | Paddock area |
| `sow_date_dayofyear` | Continuous | Day of year (1–365) |
| `temp_deviation` | Engineered | \|avg_temp_c − 12.5\|; monotonic (−) constraint |
| `seed_deviation` | Engineered | \|seed_rate − 1.5\|; monotonic (−) constraint |
| `region_enc` | Categorical | Encoded 0–4 |
| `season_year` | Continuous | 2022, 2023, 2024 |

### Feature Engineering Rationale

Raw temperature and seed rate were replaced by **deviation from optimal** to ensure the model
learns the correct agronomic direction (both have a non-monotonic U-shaped effect with a known
optimum). The monotonic constraints enforce that higher deviation always leads to lower yield,
preventing the model from learning spurious backwards shapes from the small training dataset.

### Performance

| Split | Records | R² | RMSE |
|---|---|---|---|
| Train (2022-23, 2023-24) | 97 | 0.938 | 0.216 kg/ha |
| Validation (2024-25) | 48 | 0.704 | 0.468 kg/ha |

### Confidence Intervals

The 90% CI is computed as:

```
CI_low  = max(8.0, prediction − 1.645 × RMSE)
CI_high = min(14.0, prediction + 1.645 × RMSE)
```

This assumes normally distributed residuals and uses the validation RMSE (0.468 kg/ha),
giving a 90% CI half-width of ±0.770 kg/ha.

### Limitations

- Trained on only ~100 synthetic records; not suitable for real-world use
- Soil type and variety account for >65% of model variance; weather features are less influential
- The model does not capture within-season dynamics (dry spells, frosts, pests)
- Training data range: rainfall 555–740 mm, temperature 11.5–14.1°C; extrapolation beyond these
  ranges may produce unreliable predictions
""")

# ── Tab 5: Compliance Rules ────────────────────────────────────────────────────
with tab5:
    st.markdown("""
## Compliance Rules Implemented

The following compliance checks are implemented in the Compliance and Data Quality pages.
All rules are simplified representations of statutory obligations in the Tasmanian
pharmaceutical poppy industry.

### Licence Management

| Check | Rule | Severity |
|---|---|---|
| Licence valid | `licence_expiry > today` | GREEN |
| Licence expiring | `licence_expiry within 30 days` | AMBER: renewal required |
| Licence expired | `licence_expiry < today` | RED: operations must cease |
| Missing licence number | `licence_no IS NULL` | CRITICAL |

### Sowing Declarations

| Check | Rule | Severity |
|---|---|---|
| Declaration lodged | `sowing_declaration_lodged = 1` | GREEN |
| Declaration missing | `sowing_declaration_lodged = 0` | CRITICAL: lodge within 7 days of sowing |
| No sowing record | No `SowingRecord` for this season | AMBER |

### Harvest Reconciliation

| Check | Rule | Severity |
|---|---|---|
| Reconciliation submitted | `harvest_reconciliation_submitted = 1` | GREEN |
| Reconciliation missing | `harvest_reconciliation_submitted = 0` | CRITICAL: submit within 14 days |
| No harvest record | Sowing record exists but no harvest | WARNING: may be in-progress or crop loss |

### Pesticide Compliance

| Check | Rule | Severity |
|---|---|---|
| No withholding breach | `harvest_date >= applied_date + withholding_days` | GREEN |
| Withholding period breach | `harvest_date < applied_date + withholding_days` | CRITICAL |
| No pesticide records | No `PesticideApplication` records for paddock | AMBER |
| Missing applicator ID | `applicator_id IS NULL` | WARNING |

### Data Integrity

| Check | Rule | Severity |
|---|---|---|
| Sown area within contract | Paddock areas ≤ contracted area × 1.10 | Pass/Warning |
| Yield in valid range | 8.0 ≤ yield_kg_ha ≤ 14.0 | Pass/Warning |
| Missing coordinates | `geojson_coords IS NULL` or `lat/lon IS NULL` | WARNING |
| Cost without harvest | CropCost exists but no HarvestRecord | WARNING |

### Performance Bands (Growers Page)

| Band | Rule | Display |
|---|---|---|
| Above Target (GREEN) | Fulfilment ≥ 100% | Green badge |
| Watch Zone (AMBER) | 85% ≤ Fulfilment < 100% | Amber badge |
| Under Target (RED) | Fulfilment < 85% | Red badge |

Fulfilment = Actual Yield (kg) ÷ (Contracted Area (ha) × 10.5 kg/ha benchmark) × 100
""")

show_footer()
