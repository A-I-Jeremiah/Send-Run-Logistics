from fastapi import HTTPException, BackgroundTasks
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.otp import generate_otp, store_otp, verify_otp
from app.services.email_service import (
    send_otp_email,
    send_driver_welcome_email,
)


async def request_otp(
    email: str,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.DRIVER:
        raise HTTPException(status_code=400, detail="OTP verification is only for driver accounts")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account already verified")

    otp = generate_otp()
    await store_otp(email, otp)

    background_tasks.add_task(send_otp_email, email, otp, user.first_name)

    return {"message": "OTP sent to your email"}


async def verify_driver_otp(
    email: str,
    otp: str,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Account already verified")

    is_valid = await verify_otp(email, otp)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    await db.execute(
        update(User).where(User.id == user.id).values(is_verified=True)
    )
    await db.commit()

    background_tasks.add_task(send_driver_welcome_email, email, user.first_name)

    return {"message": "Driver account verified successfully"}