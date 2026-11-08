from app.core.ws_manager import tracking_manager
from app.schemas.tracking import GPSUpdate
from fastapi import HTTPException


async def update_driver_location(data: GPSUpdate, driver_id: str) -> dict:
    location = {
        "driver_id": driver_id,
        "lat": data.latitude,
        "lng": data.longitude,
        "accuracy": data.accuracy,
        "updated_at": data.timestamp,
    }
    await tracking_manager.broadcast(data.order_id, location)
    return {"status": "ok"}


async def get_live_location(order_id: str) -> dict:
    location = tracking_manager.latest_positions.get(order_id)
    if not location:
        raise HTTPException(
            status_code=404,
            detail="No active tracking for this order"
        )
    return location


async def clear_tracking(order_id: str) -> dict:
    tracking_manager.clear(order_id)
    return {"status": "cleared"}