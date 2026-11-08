import random
import string
from app.core.redis import redis_client
from app.config import get_settings

settings = get_settings()

OTP_PREFIX = "otp:"


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


async def store_otp(email: str, otp: str) -> None:
    key = f"{OTP_PREFIX}{email}"
    await redis_client.setex(key, settings.OTP_EXPIRY_SECONDS, otp)


async def verify_otp(email: str, otp: str) -> bool:
    key = f"{OTP_PREFIX}{email}"
    stored = await redis_client.get(key)
    if stored and stored == otp:
        await redis_client.delete(key)
        return True
    return False


async def invalidate_otp(email: str) -> None:
    await redis_client.delete(f"{OTP_PREFIX}{email}")