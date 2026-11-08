import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.order import OrderStatus, VehicleType


class OrderCreate(BaseModel):
    package_description: str = Field(min_length=3, max_length=500)
    package_size: str = Field(pattern="^(envelope|small|medium|large|extra_large)$")
    package_weight: str = Field(pattern="^(very_light|light|medium|heavy|very_heavy)$")
    origin_park: str
    destination: str
    vehicle_type: VehicleType
    recipient_name: str
    recipient_phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    day_of_week: int = Field(ge=0, le=6)
    is_festive_period: bool = False
    fuel_price_per_litre: float = Field(gt=0)


class OrderResponse(BaseModel):
    id: uuid.UUID
    waybill_number: str
    package_description: str
    package_size: str
    package_weight: str
    origin_park: str
    destination: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    distance_km: float
    estimated_duration_mins: int
    route_risk: int
    day_of_week: int
    is_festive_period: bool
    fuel_price_per_litre: float
    price: float
    vehicle_type: VehicleType
    recipient_name: str
    recipient_phone: str
    status: OrderStatus
    sender_id: uuid.UUID
    sender_name: str | None = None
    driver_id: uuid.UUID | None
    driver_name: str | None = None
    created_at: datetime
    accepted_at: datetime | None
    picked_up_at: datetime | None
    delivered_at: datetime | None

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
    page: int
    per_page: int