"""
Optional web-scraper utilities for external published fare benchmarks.

NOT used by the modelling pipeline.
The training and baseline evaluation sets are built exclusively from
Survey_Logistics_Dataset_200 (1).xlsx via pipeline.build_master_dataset().
"""
# ml/data_collection/scraper.py
import httpx
import pandas as pd


# ─────────────────────────────────────────────
# HARDCODED PUBLISHED PRICES
# Source: giftgram.com.ng, abujamove.com.ng, easymove.com.ng
# These are formal operator prices — upper bound reference
# ─────────────────────────────────────────────
PUBLISHED_PRICES_2026 = [
    # Akure routes
    {"origin": "Akure", "destination": "Lagos",  "price": 8500,  "vehicle_type": "big_bus",  "package_size": "medium", "package_weight": "medium"},
    {"origin": "Akure", "destination": "Lagos",  "price": 6000,  "vehicle_type": "small_car","package_size": "medium", "package_weight": "medium"},
    {"origin": "Akure", "destination": "Ibadan", "price": 5000,  "vehicle_type": "big_bus",  "package_size": "medium", "package_weight": "medium"},
    {"origin": "Akure", "destination": "Ibadan", "price": 3500,  "vehicle_type": "small_car","package_size": "medium", "package_weight": "medium"},
    {"origin": "Akure", "destination": "Benin",  "price": 5500,  "vehicle_type": "big_bus",  "package_size": "medium", "package_weight": "medium"},
    {"origin": "Akure", "destination": "Benin",  "price": 4000,  "vehicle_type": "small_car","package_size": "medium", "package_weight": "medium"},
    {"origin": "Akure", "destination": "Abuja",  "price": 18000, "vehicle_type": "big_bus",  "package_size": "medium", "package_weight": "medium"},
    {"origin": "Akure", "destination": "Ondo",   "price": 1500,  "vehicle_type": "small_car","package_size": "small",  "package_weight": "light"},
    {"origin": "Akure", "destination": "Owo",    "price": 2000,  "vehicle_type": "small_car","package_size": "small",  "package_weight": "light"},
    {"origin": "Akure", "destination": "Ore",    "price": 3500,  "vehicle_type": "small_car","package_size": "medium", "package_weight": "medium"},
    {"origin": "Akure", "destination": "Ikare",  "price": 2500,  "vehicle_type": "small_car","package_size": "small",  "package_weight": "light"},
    {"origin": "Akure", "destination": "Okitipupa", "price": 4000, "vehicle_type": "small_car","package_size": "medium", "package_weight": "medium"},
    # Ondo routes
    {"origin": "Ondo",  "destination": "Lagos",  "price": 7000,  "vehicle_type": "small_car","package_size": "medium", "package_weight": "medium"},
    {"origin": "Ondo",  "destination": "Ore",    "price": 1800,  "vehicle_type": "small_car","package_size": "small",  "package_weight": "light"},
    {"origin": "Ondo",  "destination": "Akure",  "price": 1500,  "vehicle_type": "small_car","package_size": "small",  "package_weight": "light"},
    # Owo routes
    {"origin": "Owo",   "destination": "Akure",  "price": 2000,  "vehicle_type": "small_car","package_size": "small",  "package_weight": "light"},
    {"origin": "Owo",   "destination": "Benin",  "price": 4500,  "vehicle_type": "small_car","package_size": "medium", "package_weight": "medium"},
    # Ikare routes
    {"origin": "Ikare", "destination": "Akure",  "price": 2500,  "vehicle_type": "small_car","package_size": "small",  "package_weight": "light"},
]


def get_published_prices() -> pd.DataFrame:
    """
    Returns hardcoded price table as a DataFrame.
    Called by pipeline.py during dataset building.
    """
    df = pd.DataFrame(PUBLISHED_PRICES_2026)
    df["source"] = "published"
    df["day_of_week"] = 2        # mid-week default
    df["is_festive_period"] = False
    df["fuel_price_per_litre"] = 700.0
    # origin_park matches what pipeline.py expects
    df["origin_park"] = df["origin"] + " Park"
    return df


# ─────────────────────────────────────────────
# VYRA API SCRAPER (optional)
# Only use this if you get a RapidAPI key
# and confirm they have Ondo State coverage
# ─────────────────────────────────────────────
class VyraScraper:
    BASE_URL = "https://nigeria-intercity-transport-api.p.rapidapi.com"

    def __init__(self, api_key: str):
        self.headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "nigeria-intercity-transport-api.p.rapidapi.com",
        }

    async def fetch_routes(self, origin: str, destination: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.BASE_URL}/routes",
                headers=self.headers,
                params={"from": origin, "to": destination},
            )
            resp.raise_for_status()
            return resp.json()

    async def collect_ondo_region(self) -> pd.DataFrame:
        ondo_cities = ["Akure", "Ondo", "Owo", "Ikare", "Okitipupa"]
        destinations = ["Lagos", "Ibadan", "Benin", "Abuja", "Ore"]

        records = []
        for origin in ondo_cities:
            for dest in destinations:
                try:
                    routes = await self.fetch_routes(origin, dest)
                    for r in routes:
                        price = r.get("price") or r.get("fare")
                        if not price:
                            continue
                        records.append({
                            "origin": origin,
                            "destination": dest,
                            "price": float(price),
                            "vehicle_type": "big_bus",
                            "package_size": "medium",
                            "package_weight": "medium",
                            "source": "vyra_api",
                            "day_of_week": 2,
                            "is_festive_period": False,
                            "fuel_price_per_litre": 700.0,
                            "origin_park": f"{origin} Park",
                        })
                except Exception as e:
                    print(f"Vyra failed {origin} → {dest}: {e}")

        df = pd.DataFrame(records)
        return df