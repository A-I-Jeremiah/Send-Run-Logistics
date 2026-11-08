from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.models.order import Order, OrderStatus
from app.models.user import User, UserRole
from app.models.pricing_record import PricingRecord


async def get_dashboard_stats(db: AsyncSession) -> dict:
    # Order counts by status
    total = await db.execute(select(func.count()).select_from(Order))
    pending = await db.execute(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.PENDING)
    )
    in_transit = await db.execute(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.IN_TRANSIT)
    )
    delivered = await db.execute(
        select(func.count()).select_from(Order).where(Order.status == OrderStatus.DELIVERED)
    )

    # User counts
    senders = await db.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.SENDER)
    )
    drivers = await db.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.DRIVER)
    )
    verified_drivers = await db.execute(
        select(func.count()).select_from(User).where(
            and_(User.role == UserRole.DRIVER, User.is_verified == True)
        )
    )

    # Revenue
    avg_price = await db.execute(select(func.avg(Order.price)))
    total_revenue = await db.execute(select(func.sum(Order.price)))


    return {
        "total_orders": total.scalar() or 0,
        "pending_orders": pending.scalar() or 0,
        "in_transit_orders": in_transit.scalar() or 0,
        "delivered_orders": delivered.scalar() or 0,
        "total_senders": senders.scalar() or 0,
        "total_drivers": drivers.scalar() or 0,
        "verified_drivers": verified_drivers.scalar() or 0,
        "average_predicted_price": round(float(avg_price.scalar() or 0), 2),
        "total_revenue_predicted": round(float(total_revenue.scalar() or 0), 2),
        "model_accuracy": None
    }


async def get_order_volume(db: AsyncSession, days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Order.created_at).label("date"),
            func.count().label("count"),
        )
        .where(Order.created_at >= since)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )

    return [{"date": str(row.date), "count": row.count} for row in result.all()]


async def get_route_activity(db: AsyncSession, limit: int = 10) -> list[dict]:
    result = await db.execute(
        select(
            Order.origin_park,
            Order.destination,
            func.count().label("order_count"),
            func.avg(Order.price).label("avg_price"),
        )
        .group_by(Order.origin_park, Order.destination)
        .order_by(func.count().desc())
        .limit(limit)
    )

    return [
        {
            "origin": row.origin_park,
            "destination": row.destination,
            "order_count": row.order_count,
            "avg_price": round(float(row.avg_price), 2),
        }
        for row in result.all()
    ]