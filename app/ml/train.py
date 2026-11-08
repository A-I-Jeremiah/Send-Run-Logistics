"""
Train XGBoost and report metrics.

XGBoost uses the modelling notebook protocol (main.ipynb).

"""
from __future__ import annotations

import joblib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from app.ml.baseline import calculate_baseline_price
from app.ml.data_collection.pipeline import (
    NOTEBOOK_FUEL_BY_DATE,
    resolve_survey_path,
)
from app.ml.feature_engineering import (
    CORRIDOR_DISTANCE_KM,
    CORRIDOR_ROUTE_RISK,
    PAPER_CATEGORICAL_FEATURES,
    PAPER_NUMERICAL_FEATURES,
    SIZE_MAP,
    WEIGHT_MAP,
)

TARGET_COLUMN = "price_ngn"

def _metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }


def load_modelling_frame(survey_path: str | None = None) -> pd.DataFrame:
    """Notebook cells 4 + 6 preprocessing (XGBoost path)."""
    path = resolve_survey_path(survey_path)
    df = pd.read_excel(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by="date").reset_index(drop=True)
    df = df[df["age_group"] != "unknown"].copy()
    df["vehicle_type"] = df["vehicle_type"].replace(
        {"small_car": "big_bus", "big_bus": "small_car"}
    )

    df["weight_kg"] = df["parcel_weight"].map(WEIGHT_MAP)  # leave "very heavy" as NaN
    df["volume_cm3"] = df["package_size"].map(
        {k: v["volume_cm3"] for k, v in SIZE_MAP.items()}
    )
    df["density"] = df["weight_kg"] / (df["volume_cm3"] / 1_000_000)
    df["is_weekend"] = df["day_of_the_week"].isin([5, 6]).astype(int)
    df["vehicle_type_encoded"] = df["vehicle_type"].map(
        {"small_car": 0, "big_bus": 1}
    )
    df["fuel_price_per_litre"] = (
        df["date"].dt.strftime("%Y/%m/%d").map(NOTEBOOK_FUEL_BY_DATE)
    )
    df["distance_km"] = df["destination"].map(CORRIDOR_DISTANCE_KM).fillna(150.0)
    df["route_risk"] = df["destination"].map(CORRIDOR_ROUTE_RISK).fillna(3).astype(int)
    return df


def load_baseline_frame(survey_path: str | None = None) -> pd.DataFrame:
    """
    Frame for baseline metrics
    """
    path = resolve_survey_path(survey_path)
    df = pd.read_excel(path)
    df = df[df["age_group"] != "unknown"].copy().reset_index(drop=True)
    df["vehicle_type"] = df["vehicle_type"].replace(
        {"small_car": "big_bus", "big_bus": "small_car"}
    )
    # Include spaced "very heavy" → 40 so all 180 rows have weight (MS protocol)
    wmap = {
        "very_light": 1.0,
        "light": 3.5,
        "medium": 10.0,
        "heavy": 22.0,
        "very_heavy": 40.0,
        "very heavy": 40.0,
    }
    df["weight_kg"] = (
        df["parcel_weight"]
        .astype(str)
        .str.lower()
        .str.replace(" ", "_")
        .map({k.replace(" ", "_"): v for k, v in wmap.items()})
        .fillna(10.0)
    )
    df["distance_km"] = df["destination"].map(CORRIDOR_DISTANCE_KM).fillna(150.0)
    df["route_risk"] = df["destination"].map(CORRIDOR_ROUTE_RISK).fillna(3).astype(int)
    df["is_weekend"] = df["day_name"].isin(["Saturday", "Sunday"])
    # Survey fuel column as collected (not notebook remap)
    return df


def baseline_vector(df: pd.DataFrame) -> np.ndarray:
    preds = []
    for r in df.itertuples():
        preds.append(
            calculate_baseline_price(
                weight_kg=float(r.weight_kg),
                distance_km=float(r.distance_km),
                vehicle_type=str(r.vehicle_type),
                route_risk=int(r.route_risk),
                is_weekend=bool(r.is_weekend),
                is_festive=False,
                fuel_price_per_litre=float(r.fuel_price_per_litre),
            )["total"]
        )
    return np.asarray(preds, dtype=float)


def evaluate_baseline_(survey_path: str | None = None) -> dict:
    df = load_baseline_frame(survey_path)
    y = df["price_ngn"].values.astype(float)
    y_base = baseline_vector(df)

    rng = np.random.RandomState(42)
    perm = rng.permutation(len(df))
    n_test = int(0.2 * len(df))
    test_idx, train_idx = perm[:n_test], perm[n_test:]

    train_m = _metrics(y[train_idx], y_base[train_idx])
    test_m = _metrics(y[test_idx], y_base[test_idx])
    return {"train": train_m, "test": test_m, "n_train": len(train_idx), "n_test": len(test_idx)}


def build_pipeline(
    numerical_features: list[str],
    categorical_features: list[str],
) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline([("imputer", SimpleImputer(strategy="mean"))]),
                numerical_features,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical_features,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "regressor",
                XGBRegressor(
                    n_estimators=700,
                    max_depth=3,
                    learning_rate=0.01,
                    subsample=0.7,
                    colsample_bytree=0.7,
                    reg_alpha=0.1,
                    reg_lambda=1.0,
                    eval_metric="mae",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def train_and_save(
    data_path: str | None = None,
    output_path: str = "trained_models/pricing_pipeline.joblib",
    survey_path: str | None = None,
) -> Pipeline:
    # --- Baseline ---
    bl = evaluate_baseline_(survey_path)

    # --- XGBoost ---
    df = load_modelling_frame(survey_path)
    print(f"Loaded modelling frame n={len(df)}")

    numerical = list(PAPER_NUMERICAL_FEATURES)
    categorical = list(PAPER_CATEGORICAL_FEATURES)
    X = df[numerical + categorical]
    y = df[TARGET_COLUMN].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipeline = build_pipeline(numerical, categorical)
    pipeline.fit(X_train, y_train)
    pred_tr = pipeline.predict(X_train)
    pred_te = pipeline.predict(X_test)
    ml_train = _metrics(y_train, pred_tr)
    ml_test = _metrics(y_test, pred_te)

    def fmt(m):
        return f"R²={m['r2']:.4f}  MAE={m['mae']:,.2f}  RMSE={m['rmse']:,.2f}"

    print("\n===== RESULTS =====")
    print(f"Baseline  Train  {fmt(bl['train'])}")
    print(f"Baseline  Test   {fmt(bl['test'])}")
    
    print(f"XGBoost   Train  {fmt(ml_train)}")
    print(f"XGBoost   Test   {fmt(ml_test)}")
    
    pipeline.fit(X, y)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "numerical_features": numerical,
            "categorical_features": categorical,
            "holdout_metrics": {
                "baseline_train": bl["train"],
                "baseline_test": bl["test"],
                "xgboost_train": ml_train,
                "xgboost_test": ml_test,
            },
        },
        out,
    )
    print(f"\nPipeline saved to {out}")
    return pipeline


if __name__ == "__main__":
    train_and_save()
