"""
Feature engineering for the waybill pricing model.

Mappings and cleaning steps follow the modelling notebook (main.ipynb).
"""
from __future__ import annotations

import pandas as pd
import numpy as np


SIZE_MAP = {
    "envelope":    {"length": 35, "width": 25, "height": 3,  "volume_cm3": 2_625},
    "small":       {"length": 40, "width": 30, "height": 25, "volume_cm3": 30_000},
    "medium":      {"length": 50, "width": 40, "height": 35, "volume_cm3": 70_000},
    "large":       {"length": 70, "width": 50, "height": 50, "volume_cm3": 175_000},
    "extra_large": {"length": 100, "width": 60, "height": 60, "volume_cm3": 360_000},
}

# Exact notebook keys only. Label "very heavy" (space) is left as NaN
# and mean-imputed inside the sklearn pipeline (14 rows in the survey).
WEIGHT_MAP = {
    "very_light": 1.0,
    "light":      3.5,
    "medium":     10.0,
    "heavy":      22.0,
    "very_heavy": 40.0,
}

# representative Akure → destination distances and route-risk
CORRIDOR_DISTANCE_KM = {
    "Ondo": 48.2,
    "Owo": 56.3,
    "Ilesha": 75.0,
    "Ado-Ekiti": 85.0,
    "Ife": 95.0,
    "Osogbo": 110.0,
    "Benin": 180.0,
    "Ibadan": 198.0,
    "Warri": 280.0,
    "Lagos": 311.0,
    "Abuja": 520.0,
}

CORRIDOR_ROUTE_RISK = {
    "Ondo": 2,
    "Owo": 2,
    "Ilesha": 2,
    "Ado-Ekiti": 2,
    "Ife": 2,
    "Osogbo": 2,
    "Benin": 3,
    "Ibadan": 3,
    "Warri": 4,
    "Lagos": 4,
    "Abuja": 5,
}


# ---------------------------------------------------------------------------
# Feature sets used by the published notebook
# ---------------------------------------------------------------------------
# Numerical features fed to tree models (imputed only; no scaling)
PAPER_NUMERICAL_FEATURES = [
    "day_of_the_week",
    "fuel_price_per_litre",
    "weight_kg",
    "volume_cm3",
    "density",
    "is_weekend",
    "vehicle_type_encoded",
]

# Categorical features one-hot encoded for tree models
PAPER_CATEGORICAL_FEATURES = [
    "is_festive_period",
    "qualitative_suggested_improvements",
    "overall_system_impression",
    "pricing_determination_metric",
    "top_challenge",
    "weather_delay_experience",
    "tracking_status",
    "parcel_weight",
    "package_size",
    "vehicle_type",
    "respondent_type",
    "age_group",
    "destination",
    "day_name",
    "origin_park",
]

PAPER_FEATURES = PAPER_NUMERICAL_FEATURES + PAPER_CATEGORICAL_FEATURES

# Narrow numeric feature set used by the online predictor (API path)
FEATURE_COLUMNS = [
    "weight_kg",
    "volume_cm3",
    "density",
    "distance_km",
    "day_of_week",
    "is_weekend",
    "is_festive_period",
    "fuel_price_per_litre",
    "vehicle_type_encoded",
    "route_risk",
    "weight_distance",
    "fuel_distance",
]

TARGET_COLUMN = "price"


def apply_vehicle_label_swap(df: pd.DataFrame) -> pd.DataFrame:
    """label-swap correction."""
    df = df.copy()
    if "vehicle_type" in df.columns:
        df["vehicle_type"] = df["vehicle_type"].replace(
            {"small_car": "big_bus", "big_bus": "small_car"}
        )
    return df


def drop_unknown_age(df: pd.DataFrame) -> pd.DataFrame:
    """Exclude records with age_group == 'unknown' (200 → 180)."""
    if "age_group" in df.columns:
        return df[df["age_group"] != "unknown"].copy()
    return df.copy()


def engineer_features(df: pd.DataFrame, apply_cleaning: bool = True) -> pd.DataFrame:
    """
    Build engineered columns used by both the paper protocol and the API.

    Parameters
    ----------
    apply_cleaning :
        If True, drop unknown age and apply vehicle label swap.
        Set False when loading CSV already cleaned by pipeline.build_master_dataset().
    """
    df = df.copy()

    if apply_cleaning:
        df = drop_unknown_age(df)
        df = apply_vehicle_label_swap(df)

    # --- column aliases so notebook names and pipeline names both work ---
    if "parcel_weight" not in df.columns and "package_weight" in df.columns:
        df["parcel_weight"] = df["package_weight"]
    if "package_weight" not in df.columns and "parcel_weight" in df.columns:
        df["package_weight"] = df["parcel_weight"]

    if "day_of_the_week" not in df.columns and "day_of_week" in df.columns:
        df["day_of_the_week"] = df["day_of_week"]
    if "day_of_week" not in df.columns and "day_of_the_week" in df.columns:
        df["day_of_week"] = df["day_of_the_week"]

    if "price" not in df.columns and "price_ngn" in df.columns:
        df["price"] = df["price_ngn"]
    if "price_ngn" not in df.columns and "price" in df.columns:
        df["price_ngn"] = df["price"]

    # Weight / volume maps
    weight_col = "parcel_weight" if "parcel_weight" in df.columns else "package_weight"
    if weight_col in df.columns:
        # Match notebook: map known labels only; leave NaN for SimpleImputer
        df["weight_kg"] = df[weight_col].map(WEIGHT_MAP)

    if "package_size" in df.columns:
        # Match notebook: leave unmapped sizes as NaN for imputer
        df["volume_cm3"] = df["package_size"].map(
            {k: v["volume_cm3"] for k, v in SIZE_MAP.items()}
        )

    if "weight_kg" in df.columns and "volume_cm3" in df.columns:
        df["density"] = df["weight_kg"] / (df["volume_cm3"] / 1_000_000)

    # Temporal
    if "day_of_the_week" in df.columns:
        df["is_weekend"] = df["day_of_the_week"].isin([5, 6]).astype(int)
    elif "day_name" in df.columns:
        df["is_weekend"] = df["day_name"].isin(["Saturday", "Sunday"]).astype(int)
    else:
        df["is_weekend"] = 0

    if "is_festive_period" not in df.columns:
        df["is_festive_period"] = False
    # Keep as native type for one-hot; also numeric flag for API features
    df["is_festive_period"] = df["is_festive_period"].astype(object)

    if "vehicle_type" in df.columns:
        df["vehicle_type_encoded"] = (
            df["vehicle_type"].map({"small_car": 0, "big_bus": 1}).fillna(1).astype(int)
        )

    # Corridor distance / risk from Table 1 when not already present
    if "destination" in df.columns:
        if "distance_km" not in df.columns:
            df["distance_km"] = df["destination"].map(CORRIDOR_DISTANCE_KM)
        if "route_risk" not in df.columns:
            df["route_risk"] = df["destination"].map(CORRIDOR_ROUTE_RISK)
        df["distance_km"] = df["distance_km"].fillna(150.0)
        df["route_risk"] = df["route_risk"].fillna(3).astype(int)

    if "weight_kg" in df.columns and "distance_km" in df.columns:
        df["weight_distance"] = df["weight_kg"] * df["distance_km"]
    if "fuel_price_per_litre" in df.columns and "distance_km" in df.columns:
        df["fuel_distance"] = df["fuel_price_per_litre"] * df["distance_km"]

    # Ensure day_of_week numeric for API FEATURE_COLUMNS
    if "day_of_week" not in df.columns and "day_of_the_week" in df.columns:
        df["day_of_week"] = df["day_of_the_week"]
    if "day_of_week" not in df.columns:
        df["day_of_week"] = 0

    return df
