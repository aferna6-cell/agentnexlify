"""Google OAuth handler bodies extracted from auth.py.

Three service functions:
- `google_auth_url(mode, plan)` — build Google authorization URL.
- `google_auth_callback(code, state, error)` — exchange code, identify or
  redirect to signup setup screen.
- `google_register(request, req)` — finalize signup after Google identifies
  the user.

All three use `from backend.routers import auth as _auth` lazy lookup so test
patches on `backend.routers.auth.httpx`, `backend.routers.auth.settings`,
`backend.routers.auth.send_email`, `backend.routers.auth.secrets`, and
`backend.routers.auth.get_service_supabase` continue to intercept.
"""

import logging
from urllib.parse import urlencode

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from backend.models.schemas import GoogleRegisterRequest, RegisterResponse

logger = logging.getLogger(__name__)

_GOOGLE_OAUTH_SCOPE = "openid email profile"


async def google_auth_url(*, mode: str, plan: str | None) -> dict:
    from backend.routers import auth as _auth

    if not _auth.settings.google_client_id or not _auth.settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": _auth.settings.google_client_id,
            "redirect_uri": _auth._google_auth_callback_url(),
            "response_type": "code",
            "scope": _GOOGLE_OAUTH_SCOPE,
            "state": _auth._encode_google_state(mode, plan),
            "prompt": "select_account",
        }
    )
    return {"auth_url": auth_url}


async def google_auth_callback(
    *, code: str | None, state: str, error: str | None
) -> RedirectResponse:
    from backend.routers import auth as _auth

    oauth_state = _auth._decode_google_state(state)
    mode = oauth_state["mode"]
    plan = oauth_state["plan"]

    if error:
        target = "/login" if mode == "login" else "/signup"
        return RedirectResponse(
            url=_auth._frontend_redirect(
                target, {"google_error": error, "plan": plan}
            )
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing Google authorization code")
    if not _auth.settings.google_client_id or not _auth.settings.google_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    try:
        async with _auth.httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": _auth.settings.google_client_id,
                    "client_secret": _auth.settings.google_client_secret,
                    "redirect_uri": _auth._google_auth_callback_url(),
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

    db = _auth.get_service_supabase()
    existing = (
        db.table("tenants")
        .select("id, business_name, plan, business_type")
        .eq("owner_email", email)
        .limit(1)
        .execute()
    )
    if existing.data:
        tenant = existing.data[0]
        tenant_id = str(tenant["id"])
        token = _auth._create_token(
            tenant_id=tenant_id,
            email=email,
            plan=tenant.get("plan") or "free",
            business_name=tenant.get("business_name") or "",
            business_type=tenant.get("business_type"),
            name=owner_name,
        )
        return RedirectResponse(
            url=_auth._frontend_redirect(
                "/auth/callback",
                {"token": token, "tenant_id": tenant_id},
                use_fragment=True,
            )
        )

    setup_token = _auth._encode_google_setup_token(
        email=email, owner_name=owner_name, plan=plan
    )
    return RedirectResponse(
        url=_auth._frontend_redirect(
            "/signup",
            {
                "google_setup": setup_token,
                "email": email,
                "name": owner_name,
                "plan": plan,
            },
        )
    )


async def google_register(
    *, request: Request, req: GoogleRegisterRequest
) -> RegisterResponse:
    from backend.routers import auth as _auth

    setup = _auth._decode_google_setup_token(req.setup_token)
    email = setup["email"].lower().strip()
    if _auth.is_disposable_email(email):
        raise HTTPException(
            status_code=400, detail="Disposable email addresses are not allowed."
        )
    _auth.check_registration_velocity(request, email)
    generated_password = _auth.secrets.token_urlsafe(32)

    tenant_id, api_key = _auth._provision_tenant_account(
        business_name=req.business_name,
        owner_name=setup["owner_name"],
        email=setup["email"],
        password_hash=_auth._hash_password(generated_password),
        industry=req.industry,
        city=req.city,
        phone=req.phone,
        website_url=req.website_url,
    )

    token = _auth._create_token(
        tenant_id=tenant_id,
        email=setup["email"],
        plan="free",
        business_name=req.business_name,
        business_type=req.industry,
        name=setup["owner_name"],
    )

    await _auth._run_signup_side_effects(
        email=setup["email"],
        owner_name=setup["owner_name"],
        tenant_id=tenant_id,
        business_name=req.business_name,
        industry=req.industry,
        city=req.city,
        website_url=req.website_url,
    )

    _auth._record_signup_attempt(
        _auth._get_client_ip_for_fraud(request), email, tenant_id
    )
    return RegisterResponse(tenant_id=tenant_id, api_key=api_key, token=token)
