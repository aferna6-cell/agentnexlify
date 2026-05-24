"""Client login auth helpers: bcrypt password hashing + JWT token issue/decode."""

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Header, HTTPException
from jose import JWTError, jwt

from backend.services.client_portal.urls import _jwt_secret

_JWT_ALGORITHM = "HS256"
_CLIENT_JWT_EXPIRE_DAYS = 30

__all__ = [
    "_JWT_ALGORITHM",
    "_CLIENT_JWT_EXPIRE_DAYS",
    "_hash_client_password",
    "_verify_client_password",
    "_create_client_token",
    "_get_current_client",
]


def _hash_client_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_client_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_client_token(tenant_id: str, lead_id: str, email: str) -> str:
    payload = {
        "tenant_id": tenant_id,
        "lead_id": lead_id,
        "email": email,
        "scope": "client",
        "exp": datetime.now(timezone.utc) + timedelta(days=_CLIENT_JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def _get_current_client(authorization: str = Header(...)) -> dict:
    """Decode and validate a client JWT token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if payload.get("scope") != "client":
        raise HTTPException(status_code=403, detail="Not a client token")
    return payload
