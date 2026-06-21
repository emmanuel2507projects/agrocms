"""
Feature engineering shared between train.py and the forecast page.

Temperature and seed rate are expressed as deviation from their agronomic
optimum (12.5 C and 1.5 kg/ha respectively) so the model learns a
monotonic relationship: more deviation -> lower yield. This prevents the
GBR from fitting backwards shapes when training data is limited.
"""

import pandas as pd

VARIETY_MAP = {"Norman": 0, "Latex": 1}
SOIL_MAP    = {"Red Ferrosol": 0, "Brown Dermosol": 1, "Grey Vertosol": 2}
REGION_MAP  = {"Westbury": 0, "Deloraine": 1, "Longford": 2, "Perth": 3, "Latrobe": 4}

OPTIMAL_TEMP      = 12.5   # degC – Northern Tasmania growing season optimum
OPTIMAL_SEED_RATE = 1.5    # kg/ha

FEATURE_COLS = [
    "variety_enc",
    "soil_type_enc",
    "area_ha",
    "sow_date_dayofyear",
    "rainfall_mm",
    "temp_deviation",       # |avg_temp_c - OPTIMAL_TEMP|  (monotonic: higher = worse)
    "seed_deviation",       # |seed_rate_kg_ha - OPTIMAL_SEED_RATE|  (monotonic: higher = worse)
    "region_enc",
    "season_year",
]

# Seasonal weather lookup – used for training and forecast-page slider defaults
WEATHER = {
    ("Westbury",  2022): {"rainfall_mm": 625, "avg_temp_c": 12.3},
    ("Westbury",  2023): {"rainfall_mm": 695, "avg_temp_c": 13.0},
    ("Westbury",  2024): {"rainfall_mm": 585, "avg_temp_c": 12.7},
    ("Deloraine", 2022): {"rainfall_mm": 680, "avg_temp_c": 11.8},
    ("Deloraine", 2023): {"rainfall_mm": 720, "avg_temp_c": 12.4},
    ("Deloraine", 2024): {"rainfall_mm": 640, "avg_temp_c": 12.1},
    ("Longford",  2022): {"rainfall_mm": 560, "avg_temp_c": 13.2},
    ("Longford",  2023): {"rainfall_mm": 610, "avg_temp_c": 13.8},
    ("Longford",  2024): {"rainfall_mm": 575, "avg_temp_c": 13.5},
    ("Perth",     2022): {"rainfall_mm": 555, "avg_temp_c": 13.5},
    ("Perth",     2023): {"rainfall_mm": 605, "avg_temp_c": 14.1},
    ("Perth",     2024): {"rainfall_mm": 570, "avg_temp_c": 13.9},
    ("Latrobe",   2022): {"rainfall_mm": 740, "avg_temp_c": 11.5},
    ("Latrobe",   2023): {"rainfall_mm": 710, "avg_temp_c": 12.0},
    ("Latrobe",   2024): {"rainfall_mm": 695, "avg_temp_c": 11.8},
}


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    df must contain: variety, soil_type, area_ha, sow_date,
                     rainfall_mm, avg_temp_c, seed_rate_kg_ha,
                     region, season_year
    Returns a DataFrame with FEATURE_COLS.
    """
    out = pd.DataFrame()
    out["variety_enc"]        = df["variety"].map(VARIETY_MAP)
    out["soil_type_enc"]      = df["soil_type"].map(SOIL_MAP)
    out["area_ha"]            = df["area_ha"]
    out["sow_date_dayofyear"] = pd.to_datetime(df["sow_date"]).dt.dayofyear
    out["rainfall_mm"]        = df["rainfall_mm"]
    out["temp_deviation"]     = (df["avg_temp_c"] - OPTIMAL_TEMP).abs()
    out["seed_deviation"]     = (df["seed_rate_kg_ha"] - OPTIMAL_SEED_RATE).abs()
    out["region_enc"]         = df["region"].map(REGION_MAP)
    out["season_year"]        = df["season_year"].astype(int)
    return out[FEATURE_COLS]


def single_row(variety, soil_type, region, area_ha,
               sow_date, rainfall_mm, avg_temp_c,
               seed_rate_kg_ha, season_year) -> pd.DataFrame:
    """Build a single-row feature DataFrame for forecast predictions."""
    row = {
        "variety":          variety,
        "soil_type":        soil_type,
        "area_ha":          area_ha,
        "sow_date":         sow_date,
        "rainfall_mm":      rainfall_mm,
        "avg_temp_c":       avg_temp_c,
        "seed_rate_kg_ha":  seed_rate_kg_ha,
        "region":           region,
        "season_year":      season_year,
    }
    return build_features(pd.DataFrame([row]))
