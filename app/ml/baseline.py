"""
Rule-based pricing formula — the benchmark the ML model must beat.

Coefficients:
  B(small_car)=750, B(big_bus)=950
  r_d(small_car)=11 NGN/km, r_d(big_bus)=9 NGN/km
  weight threshold=5 kg; r_w(small_car)=70 NGN/kg, r_w(big_bus)=35 NGN/kg
  F0=1050 NGN/litre; route-risk step=0.09
  weekend uplift=12% of subtotal; festive uplift=25% of subtotal
  hard floor=NGN 1,500

All coefficients were fixed a priori and were not tuned on the test partition.
"""


def calculate_baseline_price(
    weight_kg: float,
    distance_km: float,
    vehicle_type: str,
    route_risk: int,
    is_weekend: bool,
    is_festive: bool,
    fuel_price_per_litre: float,
) -> dict:
    """
    Deterministic baseline fare for a single shipment.

    Formula:
      subtotal = (B_v + r_d_v * d + r_w_v * max(0, w - 5)) * (F / F0)
      demand   = 0.25 * subtotal  if festive
               = 0.12 * subtotal  if weekend
               = 0 otherwise
      price    = max(1500, subtotal + subtotal * ((rho - 1) * 0.09) + demand)
    """
    # --- Coefficients ---
    BASE_RATE = {"small_car": 750.0, "big_bus": 950.0}
    DISTANCE_RATE = {"small_car": 11.0, "big_bus": 9.0}
    WEIGHT_THRESHOLD = 5.0
    WEIGHT_RATE = {"small_car": 70.0, "big_bus": 35.0}
    REFERENCE_FUEL_PRICE = 1050.0  # F0
    RISK_STEP = 0.09
    WEEKEND_UPLIFT = 0.12
    FESTIVE_UPLIFT = 0.25
    PRICE_FLOOR = 1500.0

    if vehicle_type not in BASE_RATE:
        raise ValueError(
            f"Unknown vehicle_type: {vehicle_type!r}. Expected 'small_car' or 'big_bus'."
        )

    base = BASE_RATE[vehicle_type]
    distance_cost = distance_km * DISTANCE_RATE[vehicle_type]
    weight_cost = max(0.0, weight_kg - WEIGHT_THRESHOLD) * WEIGHT_RATE[vehicle_type]

    fuel_multiplier = float(fuel_price_per_litre) / REFERENCE_FUEL_PRICE
    subtotal = (base + distance_cost + weight_cost) * fuel_multiplier

    risk_surcharge = subtotal * ((int(route_risk) - 1) * RISK_STEP)

    if is_festive:
        demand_surcharge = subtotal * FESTIVE_UPLIFT
    elif is_weekend:
        demand_surcharge = subtotal * WEEKEND_UPLIFT
    else:
        demand_surcharge = 0.0

    raw = subtotal + risk_surcharge + demand_surcharge
    total = max(PRICE_FLOOR, raw)

    return {
        "total": round(total, 2),
        "breakdown": {
            "base_fare": round(base, 2),
            "distance_cost": round(distance_cost, 2),
            "weight_cost": round(weight_cost, 2),
            "fuel_multiplier": round(fuel_multiplier, 4),
            "risk_surcharge": round(risk_surcharge, 2),
            "demand_surcharge": round(demand_surcharge, 2),
            "price_floor_applied": raw < PRICE_FLOOR,
        },
    }
