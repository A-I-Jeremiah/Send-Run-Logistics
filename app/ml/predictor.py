import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.ml.baseline import calculate_baseline_price
from app.config import get_settings
from app.ml.feature_engineering import (
    FEATURE_COLUMNS,
    PAPER_CATEGORICAL_FEATURES,
    PAPER_NUMERICAL_FEATURES,
)

# Category → number mappings
SIZE_MAP = {
    "envelope":    2_625,
    "small":       30_000,
    "medium":      70_000,
    "large":       175_000,
    "extra_large": 360_000,
}

WEIGHT_MAP = {
    "very_light": 1.0,
    "light":      3.5,
    "medium":     10.0,
    "heavy":      22.0,
    "very_heavy": 40.0,
}

logger = logging.getLogger(__name__)


class PricingPredictor:
    def __init__(self):
        settings = get_settings()
        model_path = Path(settings.ML_MODEL_PATH)
        self.pipeline = None
        self.model_feature_columns: list[str] | None = None
        self.artifact_format: str | None = None
        self.model_available = False

        if not model_path.exists():
            return

        try:
            artifact = joblib.load(model_path)
            if isinstance(artifact, dict):
                pipeline = artifact.get("pipeline")
                numerical = artifact.get("numerical_features")
                categorical = artifact.get("categorical_features")
                if pipeline is None or not isinstance(numerical, list) or not isinstance(categorical, list):
                    raise ValueError("Training artifact is missing its pipeline or feature lists")
                if numerical != PAPER_NUMERICAL_FEATURES or categorical != PAPER_CATEGORICAL_FEATURES:
                    raise ValueError("Training artifact uses an unsupported survey feature schema")

                feature_columns = numerical + categorical
                self._validate_feature_names(pipeline, feature_columns)
                self.artifact_format = "survey"
            elif callable(getattr(artifact, "predict", None)):
                pipeline = artifact
                feature_columns = list(getattr(pipeline, "feature_names_in_", FEATURE_COLUMNS))
                if feature_columns != FEATURE_COLUMNS:
                    raise ValueError(f"Unsupported model feature schema: {feature_columns}")
                self.artifact_format = "online"
            else:
                raise ValueError("Model artifact does not contain a prediction pipeline")

            self.pipeline = pipeline
            self.model_feature_columns = feature_columns
            self.model_available = True
        except Exception:
            logger.exception("Could not load compatible pricing model from %s; using baseline", model_path)

    @staticmethod
    def _validate_feature_names(pipeline, feature_columns: list[str]) -> None:
        if not callable(getattr(pipeline, "predict", None)):
            raise ValueError("Training artifact pipeline has no predict method")
        fitted_columns = getattr(pipeline, "feature_names_in_", None)
        if fitted_columns is not None and list(fitted_columns) != feature_columns:
            raise ValueError("Training artifact feature metadata does not match the fitted pipeline")

    @staticmethod
    def _baseline_result(baseline: dict) -> dict:
        total = baseline["total"]
        return {
            "predicted_price": total,
            "price_breakdown": baseline["breakdown"],
            "confidence_band": {
                "low": round(total * 0.85, 2),
                "high": round(total * 1.15, 2),
            },
            "model_used": "baseline",
        }

    def _build_model_features(
        self,
        package_size: str,
        package_weight: str,
        distance_km: float,
        vehicle_type: str,
        route_risk: int,
        day_of_week: int,
        is_festive_period: bool,
        fuel_price_per_litre: float,
        weight_kg: float,
        volume_cm3: float,
        density: float,
        is_weekend: bool,
        vehicle_type_encoded: int,
    ) -> pd.DataFrame:
        if self.artifact_format == "online":
            values = {
                "weight_kg": weight_kg,
                "volume_cm3": volume_cm3,
                "density": density,
                "distance_km": distance_km,
                "day_of_week": day_of_week,
                "is_weekend": int(is_weekend),
                "is_festive_period": int(is_festive_period),
                "fuel_price_per_litre": fuel_price_per_litre,
                "vehicle_type_encoded": vehicle_type_encoded,
                "route_risk": route_risk,
                "weight_distance": weight_kg * distance_km,
                "fuel_distance": fuel_price_per_litre * distance_km,
            }
            return pd.DataFrame([values], columns=self.model_feature_columns)

        if self.artifact_format == "survey":
            # Match the vehicle label correction used by train.load_modelling_frame.
            model_vehicle_type = {"small_car": "big_bus", "big_bus": "small_car"}[vehicle_type]
            values = dict.fromkeys(self.model_feature_columns, np.nan)
            values.update(
                {
                    "day_of_the_week": day_of_week,
                    "fuel_price_per_litre": fuel_price_per_litre,
                    "weight_kg": weight_kg,
                    "volume_cm3": volume_cm3,
                    "density": density,
                    "is_weekend": int(is_weekend),
                    "vehicle_type_encoded": 0 if model_vehicle_type == "small_car" else 1,
                    "is_festive_period": is_festive_period,
                    "parcel_weight": package_weight,
                    "package_size": package_size,
                    "vehicle_type": model_vehicle_type,
                    "day_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day_of_week],
                }
            )
            return pd.DataFrame([values], columns=self.model_feature_columns)

        raise ValueError("No supported pricing model is loaded")

    def predict(
        self,
        package_size: str,
        package_weight: str,
        distance_km: float,
        vehicle_type: str,
        route_risk: int,
        day_of_week: int,
        is_festive_period: bool,
        fuel_price_per_litre: float,
    ) -> dict:
        # Convert categories to numbers
        weight_kg = WEIGHT_MAP[package_weight]
        volume_cm3 = SIZE_MAP[package_size]
        density = weight_kg / (volume_cm3 / 1_000_000)
        is_weekend = day_of_week in (5, 6)
        vehicle_type_encoded = 0 if vehicle_type == "small_car" else 1

        # Baseline always runs — fallback + comparison
        baseline = calculate_baseline_price(
            weight_kg=weight_kg,
            distance_km=distance_km,
            vehicle_type=vehicle_type,
            route_risk=route_risk,
            is_weekend=is_weekend,
            is_festive=is_festive_period,
            fuel_price_per_litre=fuel_price_per_litre,
        )

        if not self.model_available:
            return self._baseline_result(baseline)

        try:
            features = self._build_model_features(
                package_size=package_size,
                package_weight=package_weight,
                distance_km=distance_km,
                vehicle_type=vehicle_type,
                route_risk=route_risk,
                day_of_week=day_of_week,
                is_festive_period=is_festive_period,
                fuel_price_per_litre=fuel_price_per_litre,
                weight_kg=weight_kg,
                volume_cm3=volume_cm3,
                density=density,
                is_weekend=is_weekend,
                vehicle_type_encoded=vehicle_type_encoded,
            )
            predicted = float(self.pipeline.predict(features)[0])
            if not np.isfinite(predicted):
                raise ValueError("Pricing model returned a non-finite prediction")
            predicted = max(predicted, 200)
        except Exception:
            logger.exception("Pricing model inference failed; disabling it and using baseline")
            self.model_available = False
            self.pipeline = None
            return self._baseline_result(baseline)

        return {
            "predicted_price": round(predicted, 2),
            "price_breakdown": {
                **baseline["breakdown"],
                "ml_adjustment": round(predicted - baseline["total"], 2),
            },
            "confidence_band": {
                "low": round(predicted * 0.90, 2),
                "high": round(predicted * 1.10, 2),
            },
            "model_used": "xgboost",
        }


pricing_predictor = PricingPredictor()