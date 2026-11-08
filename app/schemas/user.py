import uuid
from fastapi_users import schemas
from pydantic import Field, model_validator
from app.models.user import UserRole
from app.models.order import VehicleType
from app.data.states import NIGERIA_STATES


class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: str
    last_name: str
    phone: str
    role: UserRole
    address: str

class SenderRead(UserRead):
    pass

class DriverRead(UserRead):
    is_verified: bool
    vehicle_type: VehicleType
    plate_number: str
    state_of_operation: str
    nin_license: str


class UserCreate(schemas.BaseUserCreate):
    first_name: str
    last_name: str
    phone: str = Field(pattern=r"^\+?[0-9]{10,15}$")
    address: str


class SenderCreate(UserCreate):
    role: UserRole = UserRole.SENDER


class DriverCreate(UserCreate):
    role: UserRole = UserRole.DRIVER
    vehicle_type: VehicleType
    plate_number: str
    state_of_operation: str
    nin_license: str

    @model_validator(mode="after")
    def validate_driver_states(self):
        if self.state_of_operation and self.state_of_operation not in NIGERIA_STATES:
            raise ValueError("Invalid state_of_operation")

        return self


class UserUpdate(schemas.BaseUserUpdate):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None

    address: str | None = None
    vehicle_type: str | None = None
    plate_number: str | None = None
    state_of_operation: str | None = None
    nin_license: str | None = None