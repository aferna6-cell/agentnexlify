"""Google OAuth endpoints under /api/v1/auth (google/url, google/callback,
google-register) plus their signed-state helpers.

Extracted from backend/routers/auth.py (audit 2026-06-10 H1 god-file split,
slice 3 — final slice). Same URLs and contracts; account provisioning and
signup side effects stay in auth.py and are imported (one-way: auth never
imports this module, so no cycle).

Critical rules: no `from __future__ import annotations`; never log tokens.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase as _get_service_supabase
from backend.models.schemas import GoogleRegisterRequest, RegisterResponse
from backend.services.auth_service import _jwt_secret
from backend.services.fraud_guard import (
    check_registration_velocity,
    is_disposable_email,
    _record_signup_attempt,
)
from backend.services.stripe_service import PLAN_PRICES
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_JWT_ALGORITHM = "HS256"
_GOOGLE_STATE_EXPIRY_MINUTES = 10
_GOOGLE_SETUP_EXPIRY_HOURS = 1
_GOOGLE_OAUTH_SCOPE = "openid email profile"


def get_service_supabase():
    """Module-level indirection so tests can patch auth_google.get_service_supabase."""
    return _get_service_supabase()


def _normalize_paid_plan(plan: str | None) -> str | None:
    if not plan:
        return None
    normalized = plan.lower().strip()
    return normalized if normalized in PLAN_PRICES else None


def _frontend_redirect(
    path: str, params: dict[str, str | None], *, use_fragment: bool = False
) -> str:
    base = settings.frontend_url.rstrip("/")
    query = urlencode({k: v for k, v in params.items() if v not in (None, "")})
    if not query:
        return f"{base}{path}"
    separator = "#" if use_fragment else "?"
    return f"{base}{path}{separator}{query}"


def _google_auth_callback_url() -> str:
    base = (settings.api_url or "").rstrip("/")
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


@router.get("/google/url")
async def google_auth_url(
    mode: str = Query("signup", pattern="^(login|signup)$"),
    plan: str | None = Query(None),
):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": _google_auth_callback_url(),
            "response_type": "code",
            "scope": _GOOGLE_OAUTH_SCOPE,
            "state": _encode_google_state(mode, plan),
            "prompt": "select_account",
        }
    )
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_auth_callback(
    code: str | None = Query(None, description="Authorization code returned by Google"),
    state: str = Query(..., description="Signed OAuth state token"),
    error: str | None = Query(None, description="OAuth error returned by Google"),
):
    oauth_state = _decode_google_state(state)
    mode = oauth_state["mode"]
    plan = oauth_state["plan"]

    if error:
        target = "/login" if mode == "login" else "/signup"
        return RedirectResponse(
            url=_frontend_redirect(target, {"google_error": error, "plan": plan})
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing Google authorization code")
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": _google_auth_callback_url(),
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(
                    status_code=502, detail="Google did not return an access token"
                )

            userinfo_resp = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_resp.raise_for_status()
            profile = userinfo_resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Google OAuth exchange failed")
        raise HTTPException(
            status_code=502, detail="Failed to complete Google sign-in"
        ) from exc

    email = (profile.get("email") or "").lower().strip()
    owner_name = (profile.get("name") or "").strip() or email.split("@")[0]
    if not email:
        raise HTTPException(
            status_code=400, detail="Google account did not provide an email address"
        )
    if profile.get("email_verified") is False:
        raise HTTPException(
            status_code=400, detail="Google account email must be verified"
        )

    db = get_service_supabase()
    existing = (
        db.table("tenants")
        .select("id, business_name, plan, business_type")
        .eq("owner_email", email)
        .limit(1)
        .execute()
    )
    if existing.data:
        from backend.routers.auth import _create_token

        tenant = existing.data[0]
        tenant_id = str(tenant["id"])
        token = _create_token(
            tenant_id=tenant_id,
            email=email,
            plan=tenant.get("plan") or "free",
            business_name=tenant.get("business_name") or "",
            business_type=tenant.get("business_type"),
            name=owner_name,
        )
        return RedirectResponse(
            url=_frontend_redirect(
                "/auth/callback",
                {"token": token, "tenant_id": tenant_id},
                use_fragment=True,
            )
        )

    setup_token = _encode_google_setup_token(
        email=email, owner_name=owner_name, plan=plan
    )
    return RedirectResponse(
        url=_frontend_redirect(
            "/signup",
            {
                "google_setup": setup_token,
                "email": email,
                "name": owner_name,
                "plan": plan,
            },
        )
    )


@router.post("/google-register", response_model=RegisterResponse)
@limiter.limit("5/minute")
async def google_register(request: Request, req: GoogleRegisterRequest):
    from backend.routers.auth import (
        _create_token,
        _get_client_ip_for_fraud,
        _hash_password,
        _provision_tenant_account,
        _run_signup_side_effects,
    )

    setup = _decode_google_setup_token(req.setup_token)
    email = setup["email"].lower().strip()
    if is_disposable_email(email):
        raise HTTPException(
            status_code=400, detail="Disposable email addresses are not allowed."
        )
    check_registration_velocity(request, email)
    generated_password = secrets.token_urlsafe(32)

    tenant_id, api_key = _provision_tenant_account(
        business_name=req.business_name,
        owner_name=setup["owner_name"],
        email=setup["email"],
        password_hash=_hash_password(generated_password),
        industry=req.industry,
        city=req.city,
        phone=req.phone,
        website_url=req.website_url,
    )

    token = _create_token(
        tenant_id=tenant_id,
        email=setup["email"],
        plan="free",
        business_name=req.business_name,
        business_type=req.industry,
        name=setup["owner_name"],
    )

    await _run_signup_side_effects(
        email=setup["email"],
        owner_name=setup["owner_name"],
        tenant_id=tenant_id,
        business_name=req.business_name,
        industry=req.industry,
        city=req.city,
        website_url=req.website_url,
    )

    _record_signup_attempt(_get_client_ip_for_fraud(request), email, tenant_id)
    return RegisterResponse(tenant_id=tenant_id, api_key=api_key, token=token)
