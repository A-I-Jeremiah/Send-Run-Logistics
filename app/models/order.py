import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, Enum as SAEnum, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class VehicleType(str, enum.Enum):
    SMALL_CAR = "small_car"
    BIG_BUS = "big_bus"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waybill_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    driver_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Package — category based, no tape measure needed
    package_description: Mapped[str] = mapped_column(Text)
    package_size: Mapped[str] = mapped_column(String(20))     # envelope/small/medium/large/extra_large
    package_weight: Mapped[str] = mapped_column(String(20))   # very_light/light/medium/heavy/very_heavy

    # Route
    origin_park: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(100))
    origin_lat: Mapped[float] = mapped_column(Float)
    origin_lng: Mapped[float] = mapped_column(Float)
    destination_lat: Mapped[float] = mapped_column(Float)
    destination_lng: Mapped[float] = mapped_column(Float)
    distance_km: Mapped[float] = mapped_column(Float)
    estimated_duration_mins: Mapped[int]
    route_risk: Mapped[int] = mapped_column(Integer, default=1)

    # Pricing inputs stored so we can retrain the model later with real data
    day_of_week: Mapped[int] = mapped_column(Integer)
    is_festive_period: Mapped[bool] = mapped_column(Boolean, default=False)
    fuel_price_per_litre: Mapped[float] = mapped_column(Float)

    # Pricing outputs
    price: Mapped[float] = mapped_column(Float)
    vehicle_type: Mapped[VehicleType] = mapped_column(SAEnum(VehicleType))

    confidence_band_low: Mapped[float] = mapped_column(Float)
    confidence_band_high: Mapped[float] = mapped_column(Float)
    model_used: Mapped[str] = mapped_column(String(20))

    # Recipient
    recipient_name: Mapped[str] = mapped_column(String(150))
    recipient_phone: Mapped[str] = mapped_column(String(20))

    # Status
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sender = relationship("User", back_populates="orders_as_sender", foreign_keys=[sender_id])
    driver = relationship("User", back_populates="orders_as_driver", foreign_keys=[driver_id])