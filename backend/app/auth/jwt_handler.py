"""JWT authentication and RBAC dependency injection."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ── Password utils ────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Token utils ───────────────────────────────────────────────────────
def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


# ── Current user dependency ───────────────────────────────────────────
async def get_current_user(token: str | None = Depends(oauth2_scheme)) -> dict:
    """
    Extract user from JWT token.
    For demo purposes, returns a default admin user if no token provided.
    """
    if not token:
        # Demo mode: return default admin user
        return {
            "employee_id": "demo-employee-001",
            "tenant_id": "demo-tenant-001",
            "role": "system_admin",
            "name": "Demo Admin",
        }
    try:
        payload = decode_token(token)
        return {
            "employee_id": payload.get("sub"),
            "tenant_id": payload.get("tenant_id"),
            "role": payload.get("role", "employee"),
            "name": payload.get("name", "User"),
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_manager(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] not in ("manager", "hr_admin", "finance_admin", "system_admin"):
        raise HTTPException(status_code=403, detail="Manager role required")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "system_admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


async def get_tenant_id(user: dict = Depends(get_current_user)) -> str:
    return user.get("tenant_id") or "demo-tenant-001"
