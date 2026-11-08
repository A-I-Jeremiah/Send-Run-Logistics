"""
Evaluation helpers.

Primary protocol: single 80/20 hold-out split (random_state=42) reporting
train and test R², MAE, RMSE for the rule-based baseline and XGBoost.
"""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, (str(REPO_ROOT)))

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from app.ml.baseline import calculate_baseline_price


def _metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }


def baseline_predictions(df: pd.DataFrame) -> np.ndarray:
    """Vector of baseline fares for every row."""
    preds = []
    for row in df.itertuples():
        is_weekend = bool(getattr(row, "is_weekend", 0))
        # is_weekend may be 0/1 int after engineering
        if hasattr(row, "day_name") and str(getattr(row, "day_name", "")) in ("Saturday", "Sunday"):
            is_weekend = True
        is_festive = bool(getattr(row, "is_festive_period", False))
        # object dtype True/False from survey
        if isinstance(getattr(row, "is_festive_period", False), str):
            is_festive = str(row.is_festive_period).lower() in ("true", "1", "yes")

        weight_kg = float(getattr(row, "weight_kg", 10.0))
        distance_km = float(getattr(row, "distance_km", 150.0))
        vehicle_type = str(getattr(row, "vehicle_type", "big_bus"))
        route_risk = int(getattr(row, "route_risk", 3))
        fuel = float(getattr(row, "fuel_price_per_litre", 1050.0))

        preds.append(
            calculate_baseline_price(
                weight_kg=weight_kg,
                distance_km=distance_km,
                vehicle_type=vehicle_type,
                route_risk=route_risk,
                is_weekend=is_weekend,
                is_festive=is_festive,
                fuel_price_per_litre=fuel,
            )["total"]
        )
    return np.asarray(preds, dtype=float)


def evaluate_holdout(
    df: pd.DataFrame,
    model,
    feature_cols: list[str],
    target_col: str = "price",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """
    80/20 split, random_state=42.
    Reports train/test metrics for XGBoost and the rule-based baseline.
    """
    X = df[feature_cols]
    y = df[target_col].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    # Same indices for baseline
    train_idx = X_train.index
    test_idx = X_test.index

    # --- XGBoost ---
    model.fit(X_train, y_train)
    pred_train = model.predict(X_train)
    pred_test = model.predict(X_test)
    ml_train = _metrics(y_train, pred_train)
    ml_test = _metrics(y_test, pred_test)

    # --- Baseline on the same partitions ---
    y_base_all = baseline_predictions(df)
    bl_train = _metrics(y.loc[train_idx], y_base_all[df.index.get_indexer(train_idx)])
    bl_test = _metrics(y.loc[test_idx], y_base_all[df.index.get_indexer(test_idx)])

    def _fmt(m):
        return f"R²={m['r2']:.4f}  MAE={m['mae']:,.2f}  RMSE={m['rmse']:,.2f}"

    print("\n===== BASELINE PROTOCOL (80/20, random_state=42) =====")
    print(f"Train n={len(y_train)}, Test n={len(y_test)}")
    print(f"Baseline  Train  {_fmt(bl_train)}")
    print(f"Baseline  Test   {_fmt(bl_test)}")
    print(f"XGBoost   Train  {_fmt(ml_train)}")
    print(f"XGBoost   Test   {_fmt(ml_test)}")

    return {
        "baseline": {"train": bl_train, "test": bl_test},
        "xgboost": {"train": ml_train, "test": ml_test},
        "n_train": len(y_train),
        "n_test": len(y_test),
        "model": model,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
    }


# Backwards-compatible name used by older train.py callers
def evaluate_model_vs_baseline(df, pipeline, kfold=None):
    """Deprecated KFold path — prefer evaluate_holdout."""
    from app.ml.feature_engineering import PAPER_FEATURES

    feature_cols = [c for c in PAPER_FEATURES if c in df.columns]
    return evaluate_holdout(df, pipeline, feature_cols)
