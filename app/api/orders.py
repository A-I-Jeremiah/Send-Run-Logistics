import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate, OrderListResponse
from app.services.order_service import (
    create_order,
    get_order_by_id,
    get_order_by_waybill,
    list_sender_orders,
    list_available_orders,
    list_driver_orders,
    list_all_orders,
    update_order_status,
)
from app.api.deps import require_role, require_verified_driver
from app.core.users import current_active_user

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse)
async def create_new_order(
    data: OrderCreate,
    user: User = Depends(require_role(UserRole.SENDER)),
    db: AsyncSession = Depends(get_db),
):
    order = await create_order(data, user, db)
    return order


@router.get("/my", response_model=OrderListResponse)
async def get_my_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role == UserRole.SENDER:
        result = await list_sender_orders(user.id, db, page, per_page)
    elif user.role == UserRole.DRIVER:
        result = await list_driver_orders(user.id, db, page, per_page)
    else:
        # Admin sees everything
        result = await list_all_orders(db, page, per_page)
    return result


@router.get("/available", response_model=OrderListResponse)
async def get_available_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(require_verified_driver()),
    db: AsyncSession = Depends(get_db),
):
    return await list_available_orders(db, page, per_page)


@router.get("/track/{waybill_number}", response_model=OrderResponse)
async def track_order(
    waybill_number: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — anyone with a waybill number can track."""
    return await get_order_by_waybill(waybill_number, db)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    order = await get_order_by_id(order_id, db)

    # Access control: sender, assigned driver, or admin
    if user.role == UserRole.SENDER and order.sender_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not your order")
    if user.role == UserRole.DRIVER and order.driver_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not assigned to you")

    return {
        **order.__dict__,
        "sender_name": f"{order.sender.first_name} {order.sender.last_name}" if order.sender else None,
        "driver_name": f"{order.driver.first_name} {order.driver.last_name}" if order.driver else None,
    }


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def change_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_order_status(order_id, data.status, user, db)