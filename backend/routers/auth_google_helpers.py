"""Google OAuth helpers extracted from auth.py.

Pure-logic helpers: URL building, state token encode/decode, signup
setup token encode/decode, paid-plan normalization. No FastAPI route
decorators and no database access — safe to extract without touching
router registration order or test patch surfaces.
"""

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import HTTPException
from jose import JWTError, jwt

from backend.services.auth_service import _jwt_secret
from backend.services.stripe_service import PLAN_PRICES


_JWT_ALGORITHM = "HS256"
_GOOGLE_STATE_EXPIRY_MINUTES = 10
_GOOGLE_SETUP_EXPIRY_HOURS = 1


def _normalize_paid_plan(plan: str | None) -> str | None:
    if not plan:
        return None
    normalized = plan.lower().strip()
    return normalized if normalized in PLAN_PRICES else None


def _frontend_redirect(
    path: str, params: dict[str, str | None], *, use_fragment: bool = False
) -> str:
    # Dynamic lookup so test patches at backend.routers.auth.settings reach us.
    from backend.routers import auth as _auth

    base = _auth.settings.frontend_url.rstrip("/")
    query = urlencode({k: v for k, v in params.items() if v not in (None, "")})
    if not query:
        return f"{base}{path}"
    separator = "#" if use_fragment else "?"
    return f"{base}{path}{separator}{query}"


def _google_auth_callback_url() -> str:
    from backend.routers import auth as _auth

    base = (_auth.settings.api_url or "").rstrip("/")
    if not base:
        raise HTTPException(
            status_code=503, detail="API URL is not configured for Google OAuth"
        )
    return f"{base}/api/v1/auth/google/callback"


def _encode_google_state(mode: str, plan: str | None = None) -> str:
    payload = {
        "type": "google_oauth_state",
        "mode": mode,
        "plan": _normalize_paid_plan(plan),
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=_GOOGLE_STATE_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def _decode_google_state(state: str) -> dict:
    try:
        payload = jwt.decode(state, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid or expired Google OAuth state"
        ) from exc

    if payload.get("type") != "google_oauth_state":
        raise HTTPException(status_code=400, detail="Invalid Google OAuth state")

    mode = (payload.get("mode") or "").strip().lower()
    if mode not in {"login", "signup"}:
        raise HTTPException(status_code=400, detail="Invalid Google OAuth mode")

    return {
        "mode": mode,
        "plan": _normalize_paid_plan(payload.get("plan")),
    }


def _encode_google_setup_token(
    email: str, owner_name: str, plan: str | None = None
) -> str:
    payload = {
        "type": "google_setup",
        "email": email.lower().strip(),
        "owner_name": owner_name.strip(),
        "plan": _normalize_paid_plan(plan),
        "exp": datetime.now(timezone.utc) + timedelta(hours=_GOOGLE_SETUP_EXPIRY_HOURS),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def _decode_google_setup_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid or expired Google signup token"
        ) from exc

    if payload.get("type") != "google_setup":
        raise HTTPException(status_code=400, detail="Invalid Google signup token")

    email = (payload.get("email") or "").lower().strip()
    owner_name = (payload.get("owner_name") or "").strip()
    if not email or not owner_name:
        raise HTTPException(status_code=400, detail="Incomplete Google signup token")

    return {
        "email": email,
        "owner_name": owner_name,
        "plan": _normalize_paid_plan(payload.get("plan")),
    }
