"""Password reset endpoints under /api/v1/auth (forgot-password, reset-password).

Extracted from backend/routers/auth.py (audit 2026-06-10 H1 god-file split,
slice 2). Same URLs and contracts, with one deliberate fix: the reset path
now enforces the SAME password policy as registration (10+ chars with
upper/lower/digit — backend/models/schemas.py) instead of a bare 8-char
minimum, so a reset can no longer weaken an account below signup standards.

Critical rules: no `from __future__ import annotations`; never log tokens
or passwords; never reveal whether an email exists.
"""

import hashlib
import html
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase as _get_service_supabase
from backend.services.email_sender import send_email, mask_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_service_supabase():
    """Module-level indirection so tests can patch auth_password_reset.get_service_supabase."""
    return _get_service_supabase()


def _password_problem(pw: str) -> str | None:
    """Mirror the registration policy (schemas.RegisterRequest.validate_password)."""
    if len(pw) < 10:
        return "Password must be at least 10 characters"
    if not any(c.isupper() for c in pw):
        return "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in pw):
        return "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in pw):
        return "Password must contain at least one number"
    return None


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request):
    """Send password reset email."""
    body = await request.json()
    email = (body.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    db = get_service_supabase()
    # Check tenants table for the email
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
            "DB error during forgot-password lookup for %s", mask_email(email), exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    if not result.data:
        # Don't reveal whether email exists
        return {"message": "If that email exists, a reset link has been sent."}

    tenant = result.data[0]
    tenant_id = str(tenant["id"])

    # Generate reset token (expires in 1 hour)
    reset_token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # Store hashed token in tenant record (compare hashes on redemption)
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

    # Send reset email
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
    try:
        await send_email(
            to=email,
            subject="Reset your AgentNexLiFy password",
            body_html=(
                f"<p>Hi {html.escape(tenant.get('owner_name') or 'there')},</p>"
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
        logger.warning("Failed to send reset email to %s", mask_email(email), exc_info=True)

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request):
    """Reset password using token."""
    body = await request.json()
    token = (body.get("token") or "").strip()
    new_password = body.get("password", "")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and password required")
    problem = _password_problem(new_password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)

    db = get_service_supabase()
    # Hash the incoming token to match stored hash
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

    # Update password and clear token
    from backend.routers.auth import _hash_password

    hashed = _hash_password(new_password)
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
