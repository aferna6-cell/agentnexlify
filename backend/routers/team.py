"""Team management endpoints — invite, list, update, remove members."""

import logging
import secrets

import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from backend.config import settings
from backend.models.database import get_supabase
from backend.models.schemas import (
    AcceptInviteRequest,
    InviteValidationResponse,
    TeamInviteRequest,
    TeamMemberResponse,
)
from backend.routers.auth import _create_token, _get_current_tenant, _hash_password, _verify_password
from backend.services.email_sender import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/team", tags=["team"])


def _require_owner_or_admin(claims: dict) -> dict:
    role = claims.get("role", "owner")
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return claims


def _require_owner(claims: dict) -> dict:
    role = claims.get("role", "owner")
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only owners can perform this action")
    return claims


# ── POST /invite ────────────────────────────────────────────


@router.post("/invite")
async def invite_member(req: TeamInviteRequest, claims: dict = Depends(_get_current_tenant)):
    _require_owner_or_admin(claims)
    tenant_id = claims["tenant_id"]

    try:
        db = get_supabase()

        # Check if already invited
        existing = (
            db.table("team_members")
            .select("id, invite_accepted")
            .eq("tenant_id", tenant_id)
            .eq("email", req.email.lower().strip())
            .limit(1)
            .execute()
        )
        if existing.data:
            raise HTTPException(status_code=409, detail="This email has already been invited")

        invite_token = secrets.token_urlsafe(32)
        row = {
            "tenant_id": tenant_id,
            "email": req.email.lower().strip(),
            "name": req.name,
            "role": req.role,
            "invite_token": invite_token,
            "invite_accepted": False,
            "invited_by": claims.get("user_id"),
        }
        result = db.table("team_members").insert(row).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create invite")

        # Fetch business name for the email
        tenant_result = (
            db.table("tenants")
            .select("business_name")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        business_name = tenant_result.data[0]["business_name"] if tenant_result.data else "Your team"

        # Send invite email
        invite_url = f"https://app.agentnexlify.com/invite/{invite_token}"
        body_html = f"""
        <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto; padding: 24px;">
            <h2 style="color: #00bfff;">You're invited to {business_name}</h2>
            <p>You've been invited to join <strong>{business_name}</strong> on AgentNexLiFy as a <strong>{req.role}</strong>.</p>
            <p style="margin: 24px 0;">
                <a href="{invite_url}"
                   style="display: inline-block; padding: 12px 24px; background: #00bfff; color: #000; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Accept Invitation
                </a>
            </p>
            <p style="color: #888; font-size: 13px;">If you didn't expect this invitation, you can ignore this email.</p>
        </div>
        """
        email_result = await send_email(
            to=req.email.lower().strip(),
            subject=f"You're invited to join {business_name} on AgentNexLiFy",
            body_html=body_html,
            tenant_id=tenant_id,
        )
        logger.info("Invite email result for %s: %s", req.email, email_result)

        member = result.data[0]
        return TeamMemberResponse(
            id=str(member["id"]),
            email=member["email"],
            name=member.get("name"),
            role=member["role"],
            invite_accepted=member["invite_accepted"],
            last_login=member.get("last_login"),
            created_at=member["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("invite_member failed for tenant_id=%s email=%s", tenant_id, req.email)
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /invite/{token} — public, no auth ──────────────────


@router.get("/invite/{token}", response_model=InviteValidationResponse)
async def validate_invite(token: str):
    db = get_supabase()
    result = (
        db.table("team_members")
        .select("email, role, tenant_id, invite_accepted")
        .eq("invite_token", token)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Invalid or expired invite")

    member = result.data[0]
    if member["invite_accepted"]:
        raise HTTPException(status_code=400, detail="Invite already accepted")

    # Fetch business name
    tenant = (
        db.table("tenants")
        .select("business_name")
        .eq("id", member["tenant_id"])
        .limit(1)
        .execute()
    )
    business_name = tenant.data[0]["business_name"] if tenant.data else ""

    return InviteValidationResponse(
        email=member["email"],
        business_name=business_name,
        role=member["role"],
    )


# ── POST /accept-invite — public, no auth ──────────────────


@router.post("/accept-invite")
async def accept_invite(req: AcceptInviteRequest):
    db = get_supabase()
    result = (
        db.table("team_members")
        .select("id, email, role, tenant_id, invite_accepted")
        .eq("invite_token", req.token)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Invalid or expired invite")

    member = result.data[0]
    if member["invite_accepted"]:
        raise HTTPException(status_code=400, detail="Invite already accepted")

    # Set password and mark accepted
    password_hash = _hash_password(req.password)
    db.table("team_members").update({
        "name": req.name,
        "password_hash": password_hash,
        "invite_accepted": True,
        "invite_token": None,  # Invalidate token after use
    }).eq("id", member["id"]).execute()

    # Fetch business name for JWT
    tenant = (
        db.table("tenants")
        .select("business_name, plan")
        .eq("id", member["tenant_id"])
        .limit(1)
        .execute()
    )
    t = tenant.data[0] if tenant.data else {}

    token = _create_token(
        tenant_id=str(member["tenant_id"]),
        email=member["email"],
        plan=t.get("plan", "free"),
        business_name=t.get("business_name", ""),
        user_id=str(member["id"]),
        role=member["role"],
        is_team_member=True,
        name=req.name,
    )

    return {"token": token, "tenant_id": str(member["tenant_id"])}


# ── GET /members/{tenant_id} ───────────────────────────────


@router.get("/members/{tenant_id}", response_model=list[TeamMemberResponse])
async def list_members(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    _require_owner_or_admin(claims)

    try:
        db = get_supabase()
        result = (
            db.table("team_members")
            .select("id, email, name, role, invite_accepted, last_login, created_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=False)
            .execute()
        )

        # Also include the owner from tenants table
        owner_result = (
            db.table("tenants")
            .select("id, owner_email, owner_name, created_at")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )

        members = []
        if owner_result.data:
            o = owner_result.data[0]
            members.append(TeamMemberResponse(
                id=str(o["id"]),
                email=o["owner_email"],
                name=o.get("owner_name"),
                role="owner",
                invite_accepted=True,
                last_login=None,
                created_at=o["created_at"],
            ))

        for row in (result.data or []):
            members.append(TeamMemberResponse(
                id=str(row["id"]),
                email=row["email"],
                name=row.get("name"),
                role=row["role"],
                invite_accepted=row["invite_accepted"],
                last_login=row.get("last_login"),
                created_at=row["created_at"],
            ))

        return members
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_members failed for tenant_id=%s", tenant_id)
        raise HTTPException(status_code=500, detail=str(e))


# ── PUT /members/{tenant_id}/{member_id} ───────────────────


@router.put("/members/{tenant_id}/{member_id}")
async def update_member_role(
    tenant_id: str,
    member_id: str,
    request_body: dict,
    claims: dict = Depends(_get_current_tenant),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    _require_owner(claims)

    new_role = request_body.get("role")
    if new_role not in ("admin", "member", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    db = get_supabase()

    # Check member exists and isn't the tenant owner
    member = (
        db.table("team_members")
        .select("id, role")
        .eq("id", member_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Team member not found")

    db.table("team_members").update({"role": new_role}).eq("id", member_id).execute()
    return {"status": "updated", "role": new_role}


# ── DELETE /members/{tenant_id}/{member_id} ────────────────


@router.delete("/members/{tenant_id}/{member_id}", status_code=204)
async def remove_member(
    tenant_id: str,
    member_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    _require_owner_or_admin(claims)

    db = get_supabase()

    # Verify member exists
    member = (
        db.table("team_members")
        .select("id, role")
        .eq("id", member_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Team member not found")

    # Admin can't remove owners
    caller_role = claims.get("role", "owner")
    if caller_role == "admin" and member.data[0]["role"] == "owner":
        raise HTTPException(status_code=403, detail="Admins cannot remove owners")

    db.table("team_members").delete().eq("id", member_id).eq("tenant_id", tenant_id).execute()


# ── POST /members/{tenant_id}/{member_id}/resend ──────────


@router.post("/members/{tenant_id}/{member_id}/resend")
async def resend_invite(
    tenant_id: str,
    member_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    _require_owner_or_admin(claims)

    db = get_supabase()

    member = (
        db.table("team_members")
        .select("id, email, role, invite_accepted, invite_token")
        .eq("id", member_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not member.data:
        raise HTTPException(status_code=404, detail="Team member not found")

    m = member.data[0]
    if m["invite_accepted"]:
        raise HTTPException(status_code=400, detail="Invite already accepted")

    # Generate a new token
    new_token = secrets.token_urlsafe(32)
    db.table("team_members").update({"invite_token": new_token}).eq("id", member_id).execute()

    # Fetch business name
    tenant = (
        db.table("tenants")
        .select("business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    business_name = tenant.data[0]["business_name"] if tenant.data else "Your team"

    invite_url = f"https://app.agentnexlify.com/invite/{new_token}"
    body_html = f"""
    <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto; padding: 24px;">
        <h2 style="color: #00bfff;">You're invited to {business_name}</h2>
        <p>You've been invited to join <strong>{business_name}</strong> on AgentNexLiFy as a <strong>{m['role']}</strong>.</p>
        <p style="margin: 24px 0;">
            <a href="{invite_url}"
               style="display: inline-block; padding: 12px 24px; background: #00bfff; color: #000; text-decoration: none; border-radius: 6px; font-weight: bold;">
                Accept Invitation
            </a>
        </p>
        <p style="color: #888; font-size: 13px;">If you didn't expect this invitation, you can ignore this email.</p>
    </div>
    """
    email_result = await send_email(
        to=m["email"],
        subject=f"Reminder: You're invited to join {business_name} on AgentNexLiFy",
        body_html=body_html,
        tenant_id=tenant_id,
    )
    logger.info("Resend invite email result for %s: %s", m["email"], email_result)

    return {"status": "resent"}
