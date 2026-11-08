from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users import auth_backend, fastapi_users
from app.schemas.user import DriverCreate, UserRead, SenderCreate, SenderRead, DriverRead, UserUpdate
from app.schemas.otp import OTPRequest, OTPVerify
from app.services.otp_service import request_otp, verify_driver_otp
from app.database import get_db

router = APIRouter()

# fastapi-users routes
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_register_router(DriverRead, DriverCreate),
    prefix="/auth/driver",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_register_router(SenderRead, SenderCreate),
    prefix="/auth/sender",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


# OTP endpoints
@router.post("/auth/otp/request", tags=["auth"])
async def request_driver_otp(
    data: OTPRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await request_otp(data.email, db, background_tasks)


@router.post("/auth/otp/verify", tags=["auth"])
async def verify_driver_otp_endpoint(
    data: OTPVerify,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await verify_driver_otp(data.email, data.otp, db, background_tasks)