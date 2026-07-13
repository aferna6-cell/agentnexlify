"""JWT auth utilities shared between routers and services.

Extracted here so that service-layer modules can use ``get_current_tenant``
as a FastAPI dependency without importing from a router (service→router
layer violation).
"""

from fastapi import Header, HTTPException
from jose import JWTError, jwt

from backend.config import settings

_JWT_ALGORITHM = "HS256"


def _jwt_secret() -> str:
    jwt_secret = getattr(settings, "jwt_secret_key", "")
    if isinstance(jwt_secret, str) and jwt_secret:
        return jwt_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


async def get_current_tenant(authorization: str = Header(...)) -> dict:
    """FastAPI dependency: extract tenant claims from Bearer token.

    Purpose-scoped tokens (e.g. the long-lived ``kb_sync`` token minted for
    the folder-sync CLI, or OAuth state JWTs) are NOT dashboard sessions —
    reject them here so a leaked scoped token can't reach general endpoints.
    Endpoints that accept a scoped token use their own dependency
    (backend/routers/tenant_kb.py::_get_kb_claims)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    claims = _decode_token(authorization.removeprefix("Bearer ").strip())
    if claims.get("purpose"):
        raise HTTPException(status_code=401, detail="Token not valid for this endpoint")
    return claims
