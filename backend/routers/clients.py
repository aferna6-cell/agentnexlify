"""CRM client management endpoints."""


import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.models.database import get_supabase
from backend.models.schemas import (
    ActivityItem,
    ClientListItem,
    ClientProfile,
    ClientUpdateRequest,
    CrmDashboardWidgets,
    NoteCreateRequest,
    NoteResponse,
    StageChangeRequest,
)
from backend.routers.auth import _get_current_tenant
from backend.services.activity import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


def _check_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# ------------------------------------------------------------------
# Client List
# ------------------------------------------------------------------


@router.get("/{tenant_id}")
async def get_clients(
    tenant_id: str,
    search: str | None = Query(None),
    stage: str | None = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    claims: dict = Depends(_get_current_tenant),
):
    """Client list with search, stage filter, and sorting."""
    _check_tenant(claims, tenant_id)

    db = get_supabase()
    query = db.table("leads").select("*").eq("tenant_id", tenant_id)

    if stage:
        query = query.eq("lead_stage", stage)

    if search:
        query = query.or_(
            f"name.ilike.%{search}%,email.ilike.%{search}%,phone.ilike.%{search}%"
        )

    desc = order.lower() == "desc"
    query = query.order(sort, desc=desc)

    result = query.execute()
    leads = result.data or []

    # Enrich with last activity timestamp
    lead_ids = [l["id"] for l in leads]
    last_activities: dict[str, str] = {}
    if lead_ids:
        try:
            # Fetch the most recent activity per lead
            act_result = (
                db.table("activity_log")
                .select("lead_id, created_at")
                .eq("tenant_id", tenant_id)
                .in_("lead_id", lead_ids)
                .order("created_at", desc=True)
                .execute()
            )
            for row in act_result.data or []:
                lid = row["lead_id"]
                if lid not in last_activities:
                    last_activities[lid] = row["created_at"]
        except Exception:
            logger.warning("Failed to fetch last activities", exc_info=True)

    clients = []
    for l in leads:
        clients.append(
            ClientListItem(
                id=l["id"],
                name=l.get("name"),
                email=l.get("email"),
                phone=l.get("phone"),
                lead_score=l.get("lead_score", 0),
                lead_stage=l.get("lead_stage", "new"),
                source=l.get("source", "widget"),
                created_at=l["created_at"],
                last_activity=last_activities.get(l["id"]),
            ).model_dump()
        )

    return {"clients": clients}


# ------------------------------------------------------------------
# Dashboard Widgets (must be BEFORE /{lead_id} to avoid path conflict)
# ------------------------------------------------------------------


@router.get("/{tenant_id}/dashboard-widgets", response_model=CrmDashboardWidgets)
async def get_dashboard_widgets(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """CRM dashboard widgets: recent activity, needs attention, weekly stats."""
    _check_tenant(claims, tenant_id)

    db = get_supabase()

    # Recent activity (last 20)
    recent = []
    try:
        act_result = (
            db.table("activity_log")
            .select("*")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        recent = [
            ActivityItem(
                id=r["id"],
                activity_type=r["activity_type"],
                description=r["description"],
                metadata=r.get("metadata", {}),
                lead_id=r.get("lead_id"),
                created_at=r["created_at"],
            ).model_dump()
            for r in (act_result.data or [])
        ]
    except Exception:
        logger.warning("Failed to fetch recent activity", exc_info=True)

    # Needs attention: new leads with no activity in 24h
    needs_attention = []
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        new_leads = (
            db.table("leads")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("lead_stage", "new")
            .lt("created_at", cutoff)
            .order("created_at")
            .limit(10)
            .execute()
        )
        needs_attention = [
            ClientListItem(
                id=l["id"],
                name=l.get("name"),
                email=l.get("email"),
                phone=l.get("phone"),
                lead_score=l.get("lead_score", 0),
                lead_stage=l.get("lead_stage", "new"),
                source=l.get("source", "widget"),
                created_at=l["created_at"],
            ).model_dump()
            for l in (new_leads.data or [])
        ]
    except Exception:
        logger.warning("Failed to fetch needs-attention leads", exc_info=True)

    # Weekly stats
    stats: dict[str, int] = {"new_leads": 0, "notes_added": 0, "stage_changes": 0, "messages": 0}
    try:
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        week_acts = (
            db.table("activity_log")
            .select("activity_type")
            .eq("tenant_id", tenant_id)
            .gte("created_at", week_ago)
            .execute()
        )
        for a in week_acts.data or []:
            t = a["activity_type"]
            if t == "lead_created":
                stats["new_leads"] += 1
            elif t == "note_added":
                stats["notes_added"] += 1
            elif t == "stage_change":
                stats["stage_changes"] += 1
            elif t == "message":
                stats["messages"] += 1
    except Exception:
        logger.warning("Failed to compute weekly stats", exc_info=True)

    return CrmDashboardWidgets(
        recent_activity=recent,
        needs_attention=needs_attention,
        weekly_stats=stats,
    )


# ------------------------------------------------------------------
# Client Profile
# ------------------------------------------------------------------


@router.get("/{tenant_id}/{lead_id}")
async def get_client_profile(
    tenant_id: str,
    lead_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Full client profile: lead + notes + conversations + recent activity."""
    _check_tenant(claims, tenant_id)

    db = get_supabase()

    # Lead
    lead_result = (
        db.table("leads")
        .select("*")
        .eq("id", lead_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not lead_result.data:
        raise HTTPException(status_code=404, detail="Client not found")

    lead = lead_result.data[0]

    # Notes
    notes = []
    try:
        notes_result = (
            db.table("client_notes")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("created_at", desc=True)
            .execute()
        )
        notes = [
            NoteResponse(
                id=n["id"],
                lead_id=n["lead_id"],
                content=n["content"],
                created_at=n["created_at"],
            ).model_dump()
            for n in (notes_result.data or [])
        ]
    except Exception:
        logger.warning("Failed to fetch notes for lead %s", lead_id, exc_info=True)

    # Conversations
    convos = []
    try:
        conv_result = (
            db.table("conversations")
            .select("id, session_id, started_at, last_message_at, messages")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("started_at", desc=True)
            .execute()
        )
        for c in conv_result.data or []:
            msgs = c.get("messages") or []
            convos.append({
                "id": c["id"],
                "session_id": c.get("session_id"),
                "started_at": c.get("started_at"),
                "last_message_at": c.get("last_message_at"),
                "message_count": len(msgs),
            })
    except Exception:
        logger.warning("Failed to fetch conversations for lead %s", lead_id, exc_info=True)

    # Also check by conversation_id if lead has one
    if not convos and lead.get("conversation_id"):
        try:
            conv_result = (
                db.table("conversations")
                .select("id, session_id, started_at, last_message_at, messages")
                .eq("id", lead["conversation_id"])
                .limit(1)
                .execute()
            )
            for c in conv_result.data or []:
                msgs = c.get("messages") or []
                convos.append({
                    "id": c["id"],
                    "session_id": c.get("session_id"),
                    "started_at": c.get("started_at"),
                    "last_message_at": c.get("last_message_at"),
                    "message_count": len(msgs),
                })
        except Exception:
            pass

    # Recent activity
    activity = []
    try:
        act_result = (
            db.table("activity_log")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("lead_id", lead_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        activity = [
            ActivityItem(
                id=a["id"],
                activity_type=a["activity_type"],
                description=a["description"],
                metadata=a.get("metadata", {}),
                lead_id=a.get("lead_id"),
                created_at=a["created_at"],
            ).model_dump()
            for a in (act_result.data or [])
        ]
    except Exception:
        logger.warning("Failed to fetch activity for lead %s", lead_id, exc_info=True)

    return ClientProfile(
        id=lead["id"],
        name=lead.get("name"),
        email=lead.get("email"),
        phone=lead.get("phone"),
        lead_score=lead.get("lead_score", 0),
        lead_stage=lead.get("lead_stage", "new"),
        source=lead.get("source", "widget"),
        service_interest=lead.get("service_interest"),
        timeline=lead.get("timeline"),
        budget=lead.get("budget"),
        notes_text=lead.get("notes"),
        created_at=lead["created_at"],
        client_notes=notes,
        conversations=convos,
        recent_activity=activity,
    ).model_dump()


# ------------------------------------------------------------------
# Timeline
# ------------------------------------------------------------------


@router.get("/{tenant_id}/{lead_id}/timeline")
async def get_client_timeline(
    tenant_id: str,
    lead_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    claims: dict = Depends(_get_current_tenant),
):
    """Paginated activity timeline for a client."""
    _check_tenant(claims, tenant_id)

    db = get_supabase()

    # Verify lead exists
    lead_check = (
        db.table("leads")
        .select("id")
        .eq("id", lead_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not lead_check.data:
        raise HTTPException(status_code=404, detail="Client not found")

    result = (
        db.table("activity_log")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("lead_id", lead_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    items = [
        ActivityItem(
            id=a["id"],
            activity_type=a["activity_type"],
            description=a["description"],
            metadata=a.get("metadata", {}),
            lead_id=a.get("lead_id"),
            created_at=a["created_at"],
        ).model_dump()
        for a in (result.data or [])
    ]

    return {"timeline": items, "offset": offset, "limit": limit, "has_more": len(items) == limit}


# ------------------------------------------------------------------
# Notes
# ------------------------------------------------------------------


@router.post("/{tenant_id}/{lead_id}/notes", response_model=NoteResponse)
async def add_client_note(
    tenant_id: str,
    lead_id: str,
    req: NoteCreateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Add a note to a client."""
    _check_tenant(claims, tenant_id)

    db = get_supabase()

    # Verify lead exists
    lead_check = (
        db.table("leads")
        .select("id, name")
        .eq("id", lead_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not lead_check.data:
        raise HTTPException(status_code=404, detail="Client not found")

    result = (
        db.table("client_notes")
        .insert({
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "content": req.content,
        })
        .execute()
    )
    note = result.data[0]

    lead_name = lead_check.data[0].get("name") or "Unknown"
    log_activity(
        tenant_id=tenant_id,
        activity_type="note_added",
        description=f"Note added for {lead_name}",
        lead_id=lead_id,
        metadata={"note_id": note["id"], "preview": req.content[:100]},
    )

    return NoteResponse(
        id=note["id"],
        lead_id=note["lead_id"],
        content=note["content"],
        created_at=note["created_at"],
    )


# ------------------------------------------------------------------
# Update Client
# ------------------------------------------------------------------


@router.put("/{tenant_id}/{lead_id}")
async def update_client(
    tenant_id: str,
    lead_id: str,
    req: ClientUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Update client contact fields."""
    _check_tenant(claims, tenant_id)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_supabase()
    result = (
        db.table("leads")
        .update(updates)
        .eq("id", lead_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Client not found")

    lead = result.data[0]
    lead_name = lead.get("name") or "Unknown"
    log_activity(
        tenant_id=tenant_id,
        activity_type="lead_updated",
        description=f"Updated {lead_name}: {', '.join(updates.keys())}",
        lead_id=lead_id,
        metadata={"updated_fields": list(updates.keys())},
    )

    return lead


# ------------------------------------------------------------------
# Stage Change
# ------------------------------------------------------------------


@router.put("/{tenant_id}/{lead_id}/stage")
async def change_client_stage(
    tenant_id: str,
    lead_id: str,
    req: StageChangeRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Quick stage change with activity logging."""
    _check_tenant(claims, tenant_id)

    db = get_supabase()

    # Get current stage
    current = (
        db.table("leads")
        .select("id, name, lead_stage")
        .eq("id", lead_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not current.data:
        raise HTTPException(status_code=404, detail="Client not found")

    old_stage = current.data[0].get("lead_stage", "new")
    lead_name = current.data[0].get("name") or "Unknown"

    if old_stage == req.stage:
        return {"id": lead_id, "lead_stage": req.stage, "changed": False}

    db.table("leads").update({"lead_stage": req.stage}).eq("id", lead_id).execute()

    log_activity(
        tenant_id=tenant_id,
        activity_type="stage_change",
        description=f"{lead_name}: {old_stage} -> {req.stage}",
        lead_id=lead_id,
        metadata={"old_stage": old_stage, "new_stage": req.stage},
    )

    return {"id": lead_id, "lead_stage": req.stage, "changed": True}
