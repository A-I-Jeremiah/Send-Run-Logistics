import uuid
import enum
from datetime import datetime
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String, Enum as SAEnum, DateTime, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.order import VehicleType


class UserRole(str, enum.Enum):
    SENDER = "sender"
    DRIVER = "driver"
    ADMIN = "admin"


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String(75))
    last_name: Mapped[str] = mapped_column(String(75))
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.SENDER)
    address: Mapped[str] = mapped_column(String(200))
    vehicle_type: Mapped[VehicleType] = mapped_column(SAEnum(VehicleType), nullable=True)
    plate_number: Mapped[str] = mapped_column(String(20), nullable=True)
    state_of_operation: Mapped[str] = mapped_column(String(30), nullable=True)
    nin_license: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders_as_sender = relationship("Order", back_populates="sender", foreign_keys="Order.sender_id")
    orders_as_driver = relationship("Order", back_populates="driver", foreign_keys="Order.driver_id")