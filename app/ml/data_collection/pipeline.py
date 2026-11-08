"""
Data pipeline for the waybill pricing study.

Source of truth: Survey_Logistics_Dataset_200 (1).xlsx only (N=200 raw).
Cleaning follows the modelling notebook (main.ipynb):
  - parse dates, sort chronologically
  - drop age_group == 'unknown'  → n = 180
  - vehicle label swap (small_car ↔ big_bus)
  - map parcel_weight / package_size; leave unmapped weights as NaN (imputed later)
  - notebook fuel-price-by-date remap
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.ml.feature_engineering import (
    CORRIDOR_DISTANCE_KM,
    CORRIDOR_ROUTE_RISK,
    apply_vehicle_label_swap,
    drop_unknown_age,
)

DEFAULT_SURVEY_CANDIDATES = [
    "Survey_Logistics_Dataset_200 (1).xlsx",
    "data/Survey_Logistics_Dataset_200 (1).xlsx",
    "../Survey_Logistics_Dataset_200 (1).xlsx",
    "app/data/Survey_Logistics_Dataset_200 (1).xlsx",
]

# Notebook cell 6 fuel map (daily averages from field pump observations)
NOTEBOOK_FUEL_BY_DATE = {
    "2026/06/03": (1300 + 905) / 2,
    "2026/06/04": 905.0,
    "2026/06/05": (1600 + 1300) / 2,
    "2026/06/06": (1350 + 1200) / 2,
    "2026/06/17": (1350 + 1100) / 2,
    "2026/06/18": (1350 + 1100) / 2,
    "2026/06/19": (1595 + 1300) / 2,
    "2026/06/20": (1350 + 1150) / 2,
    "2026/06/21": (1600 + 900) / 2,
}

REQUIRED_COLUMNS = [
    "origin_park",
    "destination",
    "package_size",
    "package_weight",
    "vehicle_type",
    "day_of_week",
    "is_festive_period",
    "fuel_price_per_litre",
    "price",
    "distance_km",
    "route_risk",
]


def resolve_survey_path(survey_path: str | None = None) -> Path:
    if survey_path:
        p = Path(survey_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"Survey file not found: {survey_path}")
    for candidate in DEFAULT_SURVEY_CANDIDATES:
        p = Path(candidate)
        if p.exists():
            return p
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        for name in [
            "Survey_Logistics_Dataset_200 (1).xlsx",
            "Survey_Logistics_Dataset_200.xlsx",
        ]:
            p = parent / name
            if p.exists():
                return p
    raise FileNotFoundError(
        "Could not find Survey_Logistics_Dataset_200 (1).xlsx. "
        "Pass survey_path= explicitly."
    )


def load_field_survey_data(survey_path: str | Path) -> pd.DataFrame:
    path = Path(survey_path)
    df = pd.read_excel(path) if path.suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(path)

    df.columns = (
        df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")
    )
    rename = {
        "parcel_weight": "package_weight",
        "price_ngn": "price",
        "day_of_the_week": "day_of_week",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    # Keep parcel_weight alias for notebook feature list
    if "package_weight" in df.columns and "parcel_weight" not in df.columns:
        df["parcel_weight"] = df["package_weight"]
    if "day_of_week" in df.columns and "day_of_the_week" not in df.columns:
        df["day_of_the_week"] = df["day_of_week"]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        # Notebook cell 4: chronological order (affects train_test_split indices)
        df = df.reset_index(drop=False).rename(columns={"index": "_orig_idx"})
        df = df.sort_values(by=["date", "_orig_idx"], kind="mergesort").drop(columns=["_orig_idx"]).reset_index(drop=True)

    if "is_festive_period" not in df.columns:
        df["is_festive_period"] = False
    else:
        df["is_festive_period"] = df["is_festive_period"].astype(bool)

    # Notebook fuel remap by survey date
    if "date" in df.columns:
        fuel_from_map = df["date"].dt.strftime("%Y/%m/%d").map(NOTEBOOK_FUEL_BY_DATE)
        if "fuel_price_per_litre" in df.columns:
            df["fuel_price_per_litre"] = fuel_from_map.fillna(df["fuel_price_per_litre"])
        else:
            df["fuel_price_per_litre"] = fuel_from_map
    df["fuel_price_per_litre"] = pd.to_numeric(df["fuel_price_per_litre"], errors="coerce")

    if "price" in df.columns:
        df["price"] = pd.to_numeric(
            df["price"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("₦", "", regex=False)
            .str.strip(),
            errors="coerce",
        )

    df["source"] = "field_survey"
    return df


def attach_table1_distances(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["distance_km"] = df["destination"].map(CORRIDOR_DISTANCE_KM)
    df["route_risk"] = df["destination"].map(CORRIDOR_ROUTE_RISK)
    missing = df.loc[df["distance_km"].isna(), "destination"].unique().tolist()
    if missing:
        print(f"  Warning: destinations not in Table 1: {missing}")
    df["distance_km"] = df["distance_km"].fillna(150.0)
    df["route_risk"] = df["route_risk"].fillna(3).astype(int)
    return df


def clean_survey_for_modelling(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)
    df = drop_unknown_age(df).reset_index(drop=True)
    print(f"  After age filter: {len(df)} (dropped {n0 - len(df)} unknown age)")

    df = apply_vehicle_label_swap(df)
    print(
        "  Vehicle counts after label swap:",
        df["vehicle_type"].value_counts().to_dict() if "vehicle_type" in df.columns else {},
    )

    df = attach_table1_distances(df)

    if "price" in df.columns:
        df = df[df["price"].notna() & (df["price"] > 0)].copy()

    present = [c for c in REQUIRED_COLUMNS if c in df.columns]
    df = df.dropna(subset=[c for c in present if c not in ("is_festive_period",)])

    # Preserve chronological order after filters
    if "date" in df.columns:
        df = df.sort_values(by="date").reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    print(f"  Final modelling set: {len(df)} records")
    return df


def build_master_dataset(
    survey_path: str | None = None,
    fuel_csv: str | None = None,
    output_path: str = "data/waybill_pricing_clean.csv",
    include_published_prices: bool = False,
) -> pd.DataFrame:
    if include_published_prices:
        raise ValueError(
            "include_published_prices=True is not supported. "
            "The modelling set is the field survey only."
        )

    print("=== Building Master Dataset (field survey only) ===")
    path = resolve_survey_path(survey_path)
    print(f"  Survey file: {path.resolve()}")

    field_df = load_field_survey_data(path)
    print(f"  Raw field records: {len(field_df)}")

    df = clean_survey_for_modelling(field_df)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"  Saved clean dataset → {out.resolve()}  (n={len(df)})")
    return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--survey", default=None)
    parser.add_argument("--output", default="data/waybill_pricing_clean.csv")
    args = parser.parse_args()
    build_master_dataset(survey_path=args.survey, output_path=args.output)
