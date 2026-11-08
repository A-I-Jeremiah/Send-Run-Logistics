from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.route import Route
from app.schemas.route import RouteCreate


async def get_origins(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(Route.origin).distinct().order_by(Route.origin)
    )
    return list(result.scalars().all())


async def get_destinations_for_origin(origin: str, db: AsyncSession) -> list[Route]:
    result = await db.execute(
        select(Route)
        .where(Route.origin == origin)
        .order_by(Route.destination)
    )
    return list(result.scalars().all())


async def get_route_by_origin_destination(
    origin: str, destination: str, db: AsyncSession
) -> Route:
    result = await db.execute(
        select(Route).where(
            and_(Route.origin == origin, Route.destination == destination)
        )
    )
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(
            status_code=404,
            detail=f"No route found from {origin} to {destination}. "
                   f"Contact admin to add this route."
        )
    return route


async def create_route(data: RouteCreate, db: AsyncSession) -> Route:
    existing = await db.execute(
        select(Route).where(
            and_(Route.origin == data.origin, Route.destination == data.destination)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Route already exists")

    route = Route(**data.model_dump())
    db.add(route)
    await db.commit()
    await db.refresh(route)
    return route


async def list_routes(db: AsyncSession) -> list[Route]:
    result = await db.execute(select(Route).order_by(Route.origin))
    return list(result.scalars().all())


async def update_route_risk(route_id: UUID, risk_level: int, db: AsyncSession) -> Route:
    result = await db.execute(select(Route).where(Route.id == route_id))
    route = result.scalar_one_or_none()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.risk_level = risk_level
    await db.commit()
    await db.refresh(route)
    return route