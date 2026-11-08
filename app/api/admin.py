from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import UserRole
from app.schemas.admin import DashboardStats
from app.services.admin_service import get_dashboard_stats, get_order_volume, get_route_activity
from app.api.deps import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await get_dashboard_stats(db)


@router.get("/order-volume")
async def order_volume(
    days: int = Query(30, ge=1, le=365),
    user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await get_order_volume(db, days)


@router.get("/route-activity")
async def route_activity(
    limit: int = Query(10, ge=1, le=50),
    user=Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await get_route_activity(db, limit)