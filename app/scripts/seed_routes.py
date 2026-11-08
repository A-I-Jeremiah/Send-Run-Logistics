# scripts/seed_routes.py
"""
Seeds the routes table with Ondo State routes.
Run once: python -m scripts.seed_routes
"""
import asyncio
from app.database import async_session
from app.models.route import Route
from app.scripts.dummy_data import ROUTES


async def seed():
    async with async_session() as db:
        for r in ROUTES:
            route = Route(
                origin=r["origin_park"],
                destination=r["destination"],

                origin_lat=r["origin_lat"],
                origin_lng=r["origin_lng"],
                destination_lat=r["destination_lat"],
                destination_lng=r["destination_lng"],

                distance_km=r["distance_km"],
                estimated_duration_mins=r["duration_mins"],
                risk_level=r["risk"],
            )
            db.add(route)
        await db.commit()
        print(f"Seeded {len(ROUTES)} routes")


if __name__ == "__main__":
    asyncio.run(seed())