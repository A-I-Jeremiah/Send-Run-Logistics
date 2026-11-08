import uuid
import random
import string
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate
from app.services.route_service import get_route_by_origin_destination
from app.services.pricing_service import predict_price_for_order
from app.services.email_service import send_order_notification_email
from app.core.ws_manager import tracking_manager
import asyncio


def _generate_waybill() -> str:
    digits = "".join(random.choices(string.digits, k=8))
    return f"OND-{digits}"

async def create_order(data: OrderCreate, sender: User, db: AsyncSession) -> Order:
    from app.services.route_service import get_route_by_origin_destination

    route = await get_route_by_origin_destination(data.origin_park, data.destination, db)

    pricing = predict_price_for_order(
        package_size=data.package_size,
        package_weight=data.package_weight,
        distance_km=route.distance_km,
        vehicle_type=data.vehicle_type.value,
        route_risk=route.risk_level,
        day_of_week=data.day_of_week,
        is_festive_period=data.is_festive_period,
        fuel_price_per_litre=data.fuel_price_per_litre,
    )

    order = Order(
        waybill_number=_generate_waybill(),
        sender_id=sender.id,
        package_description=data.package_description,
        package_size=data.package_size,
        package_weight=data.package_weight,
        origin_park=data.origin_park,
        destination=data.destination,
        origin_lat=route.origin_lat,
        origin_lng=route.origin_lng,
        destination_lat=route.destination_lat,
        destination_lng=route.destination_lng,
        distance_km=route.distance_km,
        estimated_duration_mins=route.estimated_duration_mins,
        route_risk=route.risk_level,
        day_of_week=data.day_of_week,
        is_festive_period=data.is_festive_period,
        fuel_price_per_litre=data.fuel_price_per_litre,
        price=pricing["predicted_price"],
        confidence_band_low=pricing["confidence_band"]["low"],
        confidence_band_high=pricing["confidence_band"]["high"],
        model_used=pricing["model_used"],
        vehicle_type=data.vehicle_type,
        recipient_name=data.recipient_name,
        recipient_phone=data.recipient_phone,
    )

    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_order_by_id(order_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.sender),
            selectinload(Order.driver),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def get_order_by_waybill(waybill: str, db: AsyncSession) -> Order:
    result = await db.execute(select(Order).where(Order.waybill_number == waybill))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


async def list_sender_orders(
    sender_id: uuid.UUID, db: AsyncSession, page: int = 1, per_page: int = 20
) -> dict:
    offset = (page - 1) * per_page

    count_q = await db.execute(
        select(func.count()).select_from(Order).where(Order.sender_id == sender_id)
    )
    total = count_q.scalar()

    result = await db.execute(
        select(Order)
        .where(Order.sender_id == sender_id)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    orders = list(result.scalars().all())

    return {"orders": orders, "total": total, "page": page, "per_page": per_page}


async def list_all_orders(db: AsyncSession, page: int = 1, per_page: int = 20) -> dict:
    """Admin view — every order regardless of sender/driver."""
    offset = (page - 1) * per_page

    count_q = await db.execute(select(func.count()).select_from(Order))
    total = count_q.scalar()

    result = await db.execute(
        select(Order)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    orders = list(result.scalars().all())

    return {"orders": orders, "total": total, "page": page, "per_page": per_page}


async def list_available_orders(db: AsyncSession, page: int = 1, per_page: int = 20) -> dict:
    """Orders available for drivers to accept."""
    offset = (page - 1) * per_page

    count_q = await db.execute(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.PENDING)
    )
    total = count_q.scalar()

    result = await db.execute(
        select(Order)
        .where(Order.status == OrderStatus.PENDING)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    orders = list(result.scalars().all())

    return {"orders": orders, "total": total, "page": page, "per_page": per_page}


async def list_driver_orders(
    driver_id: uuid.UUID, db: AsyncSession, page: int = 1, per_page: int = 20
) -> dict:
    offset = (page - 1) * per_page

    count_q = await db.execute(
        select(func.count()).select_from(Order).where(Order.driver_id == driver_id)
    )
    total = count_q.scalar()

    result = await db.execute(
        select(Order)
        .where(Order.driver_id == driver_id)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    orders = list(result.scalars().all())

    return {"orders": orders, "total": total, "page": page, "per_page": per_page}


# Valid status transitions
STATUS_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.ACCEPTED, OrderStatus.CANCELLED],
    OrderStatus.ACCEPTED: [OrderStatus.PICKED_UP, OrderStatus.CANCELLED],
    OrderStatus.PICKED_UP: [OrderStatus.IN_TRANSIT],
    OrderStatus.IN_TRANSIT: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}


async def update_order_status(
    order_id: uuid.UUID,
    new_status: OrderStatus,
    user: User,
    db: AsyncSession,
) -> Order:
    order = await get_order_by_id(order_id, db)

    # Validate transition
    allowed = STATUS_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {order.status.value} to {new_status.value}",
        )

    # Role-specific validation
    if new_status == OrderStatus.ACCEPTED:
        if user.role != UserRole.DRIVER:
            raise HTTPException(status_code=403, detail="Only drivers can accept orders")
        if order.driver_id and order.driver_id != user.id:
            raise HTTPException(status_code=409, detail="Order already accepted by another driver")
        order.driver_id = user.id
        order.accepted_at = datetime.now(timezone.utc)

    elif new_status in (OrderStatus.PICKED_UP, OrderStatus.IN_TRANSIT, OrderStatus.DELIVERED):
        if user.role != UserRole.DRIVER or order.driver_id != user.id:
            raise HTTPException(status_code=403, detail="Only the assigned driver can update this order")
        if new_status == OrderStatus.PICKED_UP:
            order.picked_up_at = datetime.now(timezone.utc)
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = datetime.now(timezone.utc)

    elif new_status == OrderStatus.CANCELLED:
        if user.role == UserRole.SENDER and order.sender_id != user.id:
            raise HTTPException(status_code=403, detail="You can only cancel your own orders")
        if user.role == UserRole.DRIVER and order.driver_id != user.id:
            raise HTTPException(status_code=403, detail="You can only cancel orders you accepted")

    order.status = new_status
    await db.commit()

    if new_status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
        await tracking_manager.close_chat(str(order_id))
        tracking_manager.clear(str(order_id))
    await db.refresh(order)

    # Send email notification to sender (fire and forget)
    try:
        sender_result = await db.execute(select(User).where(User.id == order.sender_id))
        sender = sender_result.scalar_one_or_none()
        if sender:
            asyncio.create_task(
                send_order_notification_email(
                    email=sender.email,
                    first_name=sender.first_name,
                    waybill_number=order.waybill_number,
                    status=new_status.value,
                    origin=order.origin_park,
                    destination=order.destination,
                )
            )
    except Exception:
        pass

    return order