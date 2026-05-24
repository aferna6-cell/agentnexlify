"""Forgot/reset password handler bodies extracted from auth.py.

Two service functions:
- `forgot_password(email)` — issue reset token + send email.
- `reset_password(token, new_password)` — verify token + update hash.

Both use `from backend.routers import auth as _auth` lazy lookup so test
patches on `backend.routers.auth.secrets`, `backend.routers.auth.send_email`,
`backend.routers.auth.settings`, and `backend.routers.auth.get_service_supabase`
continue to intercept.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def forgot_password(*, email: str) -> dict:
    from backend.routers import auth as _auth

    email = (email or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    db = _auth.get_service_supabase()
    try:
        result = (
            db.table("tenants")
            .select("id, owner_email, owner_name, business_name")
            .eq("owner_email", email)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error(
            "DB error during forgot-password lookup for %s", email, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    if not result.data:
        return {"message": "If that email exists, a reset link has been sent."}

    tenant = result.data[0]
    tenant_id = str(tenant["id"])

    reset_token = _auth.secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    hashed_token = hashlib.sha256(reset_token.encode()).hexdigest()
    try:
        db.table("tenants").update(
            {
                "reset_token": hashed_token,
                "reset_token_expires": expires_at,
            }
        ).eq("id", tenant_id).execute()
    except Exception:
        logger.error(
            "Failed to store reset token for tenant %s", tenant_id, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    reset_url = f"{_auth.settings.frontend_url}/reset-password?token={reset_token}"
    try:
        await _auth.send_email(
            to=email,
            subject="Reset your AgentNexLiFy password",
            body_html=(
                f"<p>Hi {tenant.get('owner_name', 'there')},</p>"
                "<p>Click the link below to reset your password. This link expires in 1 hour.</p>"
                f'<p><a href="{reset_url}" style="background:#3B82F6;color:white;'
                'padding:12px 24px;border-radius:8px;text-decoration:none;display:inline-block;">'
                "Reset Password</a></p>"
                "<p>If you didn't request this, you can safely ignore this email.</p>"
                "<p>- The AgentNexLiFy Team</p>"
            ),
            tenant_id=tenant_id,
        )
    except Exception:
        logger.warning("Failed to send reset email to %s", email, exc_info=True)

    return {"message": "If that email exists, a reset link has been sent."}


def reset_password(*, token: str, new_password: str) -> dict:
    from backend.routers import auth as _auth

    token = (token or "").strip()
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and password required")
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400, detail="Password must be at least 8 characters"
        )

    db = _auth.get_service_supabase()
    hashed_token = hashlib.sha256(token.encode()).hexdigest()
    try:
        result = (
            db.table("tenants")
            .select("id, reset_token_expires")
            .eq("reset_token", hashed_token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error("DB error during reset-password token lookup", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    if not result.data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")

    tenant = result.data[0]
    expires = tenant.get("reset_token_expires")
    if expires:
        exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > exp_dt:
            raise HTTPException(status_code=400, detail="Reset link has expired")

    hashed = _auth._hash_password(new_password)
    try:
        db.table("tenants").update(
            {
                "password_hash": hashed,
                "reset_token": None,
                "reset_token_expires": None,
            }
        ).eq("id", str(tenant["id"])).execute()
    except Exception:
        logger.error(
            "Failed to update password for tenant %s", tenant["id"], exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    logger.info("Password reset completed for tenant %s", tenant["id"])
    return {"message": "Password reset successfully"}
