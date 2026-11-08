from app.ml.predictor import pricing_predictor


def predict_price_for_order(
    package_size: str,
    package_weight: str,
    distance_km: float,
    vehicle_type: str,
    route_risk: int,
    day_of_week: int,
    is_festive_period: bool,
    fuel_price_per_litre: float,
) -> dict:
    return pricing_predictor.predict(
        package_size=package_size,
        package_weight=package_weight,
        distance_km=distance_km,
        vehicle_type=vehicle_type,
        route_risk=route_risk,
        day_of_week=day_of_week,
        is_festive_period=is_festive_period,
        fuel_price_per_litre=fuel_price_per_litre,
    )