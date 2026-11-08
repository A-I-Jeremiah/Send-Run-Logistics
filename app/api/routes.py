from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import UserRole
from app.schemas.route import RouteCreate, RouteResponse, AvailableDestinations
from app.services.route_service import (
    create_route,
    list_routes,
    update_route_risk,
    get_origins,
    get_destinations_for_origin,
)
from app.api.deps import require_role

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("/origins", response_model=list[str])
async def list_origins(db: AsyncSession = Depends(get_db)):
    """
    Returns all unique origin parks.
    """
    return await get_origins(db)


@router.get("/destinations", response_model=list[RouteResponse])
async def list_destinations(
    origin: str = Query(..., description="Origin park name"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all destinations available from a given origin.
    """
    return await get_destinations_for_origin(origin, db)


@router.get("", response_model=list[RouteResponse])
async def get_all_routes(db: AsyncSession = Depends(get_db)):
    """All routes — used by admin."""
    return await list_routes(db)


@router.post("", response_model=RouteResponse)
async def add_route(
    data: RouteCreate,
    user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await create_route(data, db)


@router.patch("/{route_id}/risk")
async def set_route_risk(
    route_id: UUID,
    risk_level: int = Query(ge=1, le=5),
    user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await update_route_risk(route_id, risk_level, db)