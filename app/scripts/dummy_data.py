"""
DEMO / SEED DATA ONLY — NOT used for model training.

The pricing model and baseline evaluation use exclusively:
  Survey_Logistics_Dataset_200 (1).xlsx
via app.ml.data_collection.pipeline.build_master_dataset().

This module may still seed demo routes or UI fixtures. Do not concatenate
its rows into the modelling set.
"""
# ml/dummy_data.py
"""
Dummy dataset for development and testing.
Replace with real field survey data before final training.
"""
import pandas as pd
import random
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

ROUTES = [
    {
        "origin_park": "Ondo Garage Akure",
        "destination": "Ondo Town",
        "origin_lat": 7.2571,
        "origin_lng": 5.2058,
        "destination_lat": 7.0833,
        "destination_lng": 4.8333,
        "distance_km": 48.2,
        "duration_mins": 55,
        "risk": 2,
    },
    {
        "origin_park": "Ondo Garage Akure",
        "destination": "Ore",
        "origin_lat": 7.2571,
        "origin_lng": 5.2058,
        "destination_lat": 6.7450,
        "destination_lng": 4.8760,
        "distance_km": 89.5,
        "duration_mins": 95,
        "risk": 2,
    },
    {
        "origin_park": "South Gate Akure",
        "destination": "Lagos",
        "origin_lat": 7.2571,
        "origin_lng": 5.1950,
        "destination_lat": 6.5244,
        "destination_lng": 3.3792,
        "distance_km": 311.0,
        "duration_mins": 270,
        "risk": 4,
    },
    {
        "origin_park": "South Gate Akure",
        "destination": "Ibadan",
        "origin_lat": 7.2571,
        "origin_lng": 5.1950,
        "destination_lat": 7.3775,
        "destination_lng": 3.9470,
        "distance_km": 198.0,
        "duration_mins": 180,
        "risk": 3,
    },
    {
        "origin_park": "Ondo Garage Akure",
        "destination": "Owo",
        "origin_lat": 7.2571,
        "origin_lng": 5.2058,
        "destination_lat": 7.1962,
        "destination_lng": 5.5868,
        "distance_km": 56.3,
        "duration_mins": 60,
        "risk": 2,
    },
    {
        "origin_park": "Ondo Garage Akure",
        "destination": "Ikare",
        "origin_lat": 7.2571,
        "origin_lng": 5.2058,
        "destination_lat": 7.4951,
        "destination_lng": 5.7480,
        "distance_km": 82.0,
        "duration_mins": 90,
        "risk": 3,
    },
    {
        "origin_park": "South Gate Akure",
        "destination": "Benin",
        "origin_lat": 7.2571,
        "origin_lng": 5.1950,
        "destination_lat": 6.3350,
        "destination_lng": 5.6037,
        "distance_km": 180.0,
        "duration_mins": 165,
        "risk": 3,
    },
    {
        "origin_park": "Ondo Town Park",
        "destination": "Lagos",
        "origin_lat": 7.0833,
        "origin_lng": 4.8333,
        "destination_lat": 6.5244,
        "destination_lng": 3.3792,
        "distance_km": 263.0,
        "duration_mins": 240,
        "risk": 4,
    },
    {
        "origin_park": "Ondo Town Park",
        "destination": "Ore",
        "origin_lat": 7.0833,
        "origin_lng": 4.8333,
        "destination_lat": 6.7450,
        "destination_lng": 4.8760,
        "distance_km": 42.0,
        "duration_mins": 45,
        "risk": 2,
    },
    {
        "origin_park": "Owo Park",
        "destination": "Akure",
        "origin_lat": 7.1962,
        "origin_lng": 5.5868,
        "destination_lat": 7.2571,
        "destination_lng": 5.2058,
        "distance_km": 56.3,
        "duration_mins": 60,
        "risk": 2,
    },
    {
        "origin_park": "Owo Park",
        "destination": "Benin",
        "origin_lat": 7.1962,
        "origin_lng": 5.5868,
        "destination_lat": 6.3350,
        "destination_lng": 5.6037,
        "distance_km": 125.0,
        "duration_mins": 120,
        "risk": 3,
    },
    {
        "origin_park": "Ikare Park",
        "destination": "Akure",
        "origin_lat": 7.4951,
        "origin_lng": 5.7480,
        "destination_lat": 7.2571,
        "destination_lng": 5.2058,
        "distance_km": 82.0,
        "duration_mins": 90,
        "risk": 3,
    },
    {
        "origin_park": "South Gate Akure",
        "destination": "Abuja",
        "origin_lat": 7.2571,
        "origin_lng": 5.1950,
        "destination_lat": 9.0765,
        "destination_lng": 7.3986,
        "distance_km": 520.0,
        "duration_mins": 480,
        "risk": 5,
    },
    {
        "origin_park": "Ondo Garage Akure",
        "destination": "Okitipupa",
        "origin_lat": 7.2571,
        "origin_lng": 5.2058,
        "destination_lat": 6.4719,
        "destination_lng": 4.7874,
        "distance_km": 105.0,
        "duration_mins": 110,
        "risk": 4,
    },
]

SIZES = ["envelope", "small", "medium", "large", "extra_large"]
WEIGHTS = ["very_light", "light", "medium", "heavy", "very_heavy"]
VEHICLES = ["small_car", "big_bus"]

def random_date(start_date, end_date):
    """
    Generate a random datetime between two dates.
    """
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

def _price_logic(route, size, weight, vehicle, day, is_festive, fuel):
    """
    Realistic 2025/2026 Nigerian waybill pricing.
    Based on current fuel costs and informal market rates.
    """
    dist = route["distance_km"]
    weight_val = {
        "very_light": 1.0,
        "light":      3.5,
        "medium":     10.0,
        "heavy":      22.0,
        "very_heavy": 40.0,
    }[weight]

    if vehicle == "small_car":
        base     = 2000
        per_km   = random.uniform(30, 42)
        wt_rate  = random.uniform(250, 400)
    else:
        base     = 1500
        per_km   = random.uniform(22, 32)
        wt_rate  = random.uniform(180, 280)

    size_mult = {
        "envelope":    0.65,
        "small":       0.85,
        "medium":      1.00,
        "large":       1.45,
        "extra_large": 2.00,
    }[size]

    distance_cost = dist * per_km
    weight_cost   = max(0, weight_val - 5) * wt_rate

    price = (base + distance_cost + weight_cost) * size_mult

    price *= fuel / 700

    price *= 1 + ((route["risk"] - 1) * random.uniform(0.06, 0.12))

    if is_festive:
        price *= random.uniform(1.25, 1.50)
    elif day in (5, 6):
        price *= random.uniform(1.10, 1.25)

    price *= random.uniform(0.88, 1.12)

    # Floor: no waybill cheaper than ₦1,500
    price = max(price, 1500)

    # Round to nearest ₦50
    return round(price / 50) * 50


def generate_dummy_dataset(n_records: int = 300) -> pd.DataFrame:
    records = []

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)

    for _ in range(n_records):
        route = random.choice(ROUTES)

        random_dt = random_date(start_date, end_date)

        size = random.choices(SIZES, weights=[10, 30, 35, 20, 5])[0]
        weight = random.choices(WEIGHTS, weights=[10, 30, 35, 20, 5])[0]
        vehicle = random.choices(VEHICLES, weights=[65, 35])[0]

        # Use actual weekday from generated date
        day = random_dt.weekday()

        is_festive = random.random() < 0.08
        fuel = random.choice([680, 700, 720, 750, 800, 850])

        price = _price_logic(route, size, weight, vehicle, day, is_festive, fuel)

        records.append({
            "date": random_dt.date(),  # or random_dt.isoformat()

            "origin_park": route["origin_park"],
            "destination": route["destination"],
            "distance_km": route["distance_km"],
            "estimated_duration_mins": route["duration_mins"],
            "route_risk": route["risk"],
            "package_size": size,
            "package_weight": weight,
            "vehicle_type": vehicle,
            "day_of_week": day,
            "is_festive_period": is_festive,
            "fuel_price_per_litre": fuel,
            "price": price,
        })

    return pd.DataFrame(records)


if __name__ == "__main__":
    df = generate_dummy_dataset(300)
    df.to_csv(DATA_DIR / "dummy_waybill_data.csv", index=False)
    print(f"Generated {len(df)} records")
    print(f"\nSample:\n{df.head(10).to_string()}")
    print(f"\nPrice stats:\n{df['price'].describe()}")
    print(f"\nRoutes:\n{df.groupby(['origin_park', 'destination'])['price'].agg(['count', 'mean', 'min', 'max'])}")