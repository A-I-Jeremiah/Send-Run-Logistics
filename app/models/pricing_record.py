import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PricingRecord(Base):
    """Stores every pricing prediction for model retraining and admin analytics."""
    __tablename__ = "pricing_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    volume_cm3: Mapped[float] = mapped_column(Float)
    distance_km: Mapped[float] = mapped_column(Float)
    vehicle_type: Mapped[str] = mapped_column(String(20))
    route_risk: Mapped[int] = mapped_column(Integer)
    day_of_week: Mapped[int] = mapped_column(Integer)
    is_festive_period: Mapped[bool] = mapped_column(Boolean)
    fuel_price_per_litre: Mapped[float] = mapped_column(Float)
    predicted_price: Mapped[float] = mapped_column(Float)
    actual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_used: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())