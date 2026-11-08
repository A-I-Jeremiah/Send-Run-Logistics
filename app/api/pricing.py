from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.pricing import PricingRequest, PricingResponse, QuickQuoteRequest
from app.services.pricing_service import predict_price_for_order
from app.services.route_service import get_route_by_origin_destination
from app.core.users import current_active_user

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/predict", response_model=PricingResponse)
async def predict_price(req: PricingRequest, user=Depends(current_active_user)):
    result = predict_price_for_order(
        package_size=req.package_size,
        package_weight=req.package_weight,
        distance_km=req.distance_km,
        vehicle_type=req.vehicle_type,
        route_risk=req.route_risk,
        day_of_week=req.day_of_week,
        is_festive_period=req.is_festive_period,
        fuel_price_per_litre=req.fuel_price_per_litre,
    )
    return PricingResponse(
        price=result["predicted_price"],
        model_used=result["model_used"],
    )


@router.post("/quick-quote")
async def quick_quote(
    req: QuickQuoteRequest,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    route = await get_route_by_origin_destination(req.origin_park, req.destination, db)
    now = datetime.now()

    result = predict_price_for_order(
        package_size=req.package_size,
        package_weight=req.package_weight,
        distance_km=route.distance_km,
        vehicle_type=req.vehicle_type,
        route_risk=route.risk_level,
        day_of_week=now.weekday(),
        is_festive_period=False,
        fuel_price_per_litre=700.0,
    )

    return {
        "origin": req.origin_park,
        "destination": req.destination,
        "distance_km": route.distance_km,
        "estimated_duration_mins": route.estimated_duration_mins,
        "price": result["predicted_price"],
    }
