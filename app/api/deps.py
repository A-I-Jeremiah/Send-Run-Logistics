from fastapi import Depends, HTTPException, status
from app.models.user import User, UserRole
from app.core.users import current_active_user


def require_role(*roles: UserRole):
    """Dependency factory: restrict endpoint to specific roles."""
    async def _check(user: User = Depends(current_active_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of: {[r.value for r in roles]}",
            )
        return user
    return _check


def require_verified_driver():
    """Drivers must have completed OTP verification."""
    async def _check(user: User = Depends(current_active_user)):
        if user.role != UserRole.DRIVER:
            raise HTTPException(status_code=403, detail="Driver role required")
        if not user.is_verified:
            raise HTTPException(status_code=403, detail="Driver account not verified. Complete OTP verification first.")
        return user
    return _check