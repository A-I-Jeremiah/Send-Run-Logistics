import uuid
from typing import AsyncGenerator
from fastapi import Depends, Request, HTTPException, status, BackgroundTasks
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.config import get_settings
from app.core.otp import generate_otp, store_otp
from app.services.email_service import send_otp_email
import asyncio

settings = get_settings()


async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.RESET_PASSWORD_SECRET
    verification_token_secret = settings.VERIFICATION_SECRET

    async def on_after_register(self, user: User, request: Request | None = None):
        """After registration, if user is a driver, send OTP for verification."""
        if user.role == UserRole.DRIVER:
            otp = generate_otp()
            await store_otp(user.email, otp)
            asyncio.create_task(
                send_otp_email(
                    user.email,
                    otp,
                    user.first_name
                )
            )

    async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None):
        # Could send a password reset email here
        pass

    async def on_after_request_verify(self, user: User, token: str, request: Request | None = None):
        pass

    async def update(self, user_update, user, safe=True, request=None):
        if user.role == UserRole.SENDER:
            forbidden_fields = [
                user_update.vehicle_type,
                user_update.plate_number,
                user_update.state_of_operation,
                user_update.nin_license,
            ]

            if any(forbidden_fields):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Senders cannot update driver-specific fields"
                )

        return await super().update(user_update, user, safe, request)


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


# Auth backend
bearer_transport = BearerTransport(tokenUrl="auth/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.JWT_SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)