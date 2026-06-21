"""
Train the AgroCMS yield-forecasting model.
Run:  python ml/train.py
Outputs: ml/model.pkl
"""

import sys
import pickle
import pandas as pd
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import r2_score, root_mean_squared_error

from backend.database import SessionLocal
from backend.models import HarvestRecord, SowingRecord, Paddock, Grower, Contract
from ml.features import WEATHER, build_features, FEATURE_COLS

SEASON_YEAR = {"2022-23": 2022, "2023-24": 2023, "2024-25": 2024}


def load_dataset(session):
    rows = []
    harvests = session.query(HarvestRecord).all()
    for hr in harvests:
        sow = (
            session.query(SowingRecord)
            .filter(
                SowingRecord.paddock_id  == hr.paddock_id,
                SowingRecord.contract_id == hr.contract_id,
            )
            .first()
        )
        if sow is None:
            continue
        pad      = session.get(Paddock, hr.paddock_id)
        contract = session.get(Contract, hr.contract_id)
        grower   = session.get(Grower, pad.grower_id)
        yr       = SEASON_YEAR.get(contract.season)
        if yr is None:
            continue
        weather = WEATHER.get((grower.region, yr), {})

        rows.append({
            "variety":         contract.variety,
            "soil_type":       pad.soil_type,
            "area_ha":         pad.area_ha,
            "sow_date":        sow.sow_date,
            "rainfall_mm":     weather.get("rainfall_mm", 620),
            "avg_temp_c":      weather.get("avg_temp_c", 12.5),
            "seed_rate_kg_ha": sow.seed_rate_kg_ha or 1.5,
            "region":          grower.region,
            "season_year":     yr,
            "season":          contract.season,
            "yield_kg_ha":     hr.yield_kg_ha,
        })
    return pd.DataFrame(rows)


def main():
    session = SessionLocal()
    try:
        df = load_dataset(session)
    finally:
        session.close()

    if df.empty:
        print("No harvest data found. Run backend/seed_data.py first.")
        sys.exit(1)

    print(f"Dataset: {len(df)} records across seasons {df['season'].unique().tolist()}")

    train_df = df[df["season"].isin(["2022-23", "2023-24"])].copy()
    val_df   = df[df["season"] == "2024-25"].copy()

    X_train = build_features(train_df)
    y_train = train_df["yield_kg_ha"].values
    X_val   = build_features(val_df)
    y_val   = val_df["yield_kg_ha"].values

    # HistGradientBoostingRegressor supports monotonic_cst, enforcing correct
    # agronomic direction for features where the expected relationship is known.
    model = HistGradientBoostingRegressor(
        max_iter=200,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
        min_samples_leaf=8,
        monotonic_cst={
            "rainfall_mm":    1,   # more rainfall -> higher yield
            "temp_deviation": -1,  # more deviation from optimal -> lower yield
            "seed_deviation": -1,  # more deviation from optimal -> lower yield
        },
    )
    model.fit(X_train, y_train)

    train_r2   = r2_score(y_train, model.predict(X_train))
    train_rmse = root_mean_squared_error(y_train, model.predict(X_train))

    if len(val_df) > 0:
        val_r2   = r2_score(y_val, model.predict(X_val))
        val_rmse = root_mean_squared_error(y_val, model.predict(X_val))
        print(f"Train  R2={train_r2:.3f}  RMSE={train_rmse:.3f} kg/ha")
        print(f"Val    R2={val_r2:.3f}    RMSE={val_rmse:.3f} kg/ha")
    else:
        val_r2   = None
        val_rmse = train_rmse
        print(f"Train  R2={train_r2:.3f}  RMSE={train_rmse:.3f} kg/ha  (no 2024-25 harvest data yet)")

    perm = permutation_importance(model, X_train, y_train, n_repeats=10, random_state=42)
    importances = dict(zip(FEATURE_COLS, perm.importances_mean))
    print("\nFeature importances (permutation):")
    for k, v in sorted(importances.items(), key=lambda x: -x[1]):
        print(f"  {k:<25} {v:.3f}")

    model_data = {
        "model":                model,
        "train_r2":             train_r2,
        "val_r2":               val_r2,
        "train_rmse":           train_rmse,
        "val_rmse":             val_rmse,
        "feature_names":        FEATURE_COLS,
        "feature_importances":  importances,
        "trained_on":           str(date.today()),
    }

    out_path = Path(__file__).parent / "model.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(model_data, f)
    print(f"\nModel saved -> {out_path}")


if __name__ == "__main__":
    main()
