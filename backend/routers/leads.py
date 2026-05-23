"""Lead management endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from pydantic import BaseModel, Field

from backend.models.database import get_service_supabase as _get_service_supabase
from backend.models.schemas import LeadScoreResponse, LeadUpdateRequest, ScoreAllResponse
from backend.services.llm_runtime import call_claude_messages
from backend.dependencies import _get_current_tenant
from backend.services.activity import log_activity
from backend.services.email_sender import send_email
from backend.limiter import limiter
from backend.services.lead_csv import (  # noqa: F401  re-exported for tests
    CSV_FIELD_MAP as _CSV_FIELD_MAP,
    apply_import_batch as _apply_import_batch,
    build_export_query as _build_export_query,
    fetch_existing_emails as _fetch_existing_emails,
    parse_csv_for_import as _parse_csv_for_import,
    serialize_leads_to_csv as _serialize_leads_to_csv,
)
from backend.services.lead_dedup import (  # noqa: F401  re-exported for tests
    apply_lead_merge as _apply_lead_merge,
    fetch_duplicate_groups as _fetch_duplicate_groups,
)
from backend.services.lead_activity import (  # noqa: F401  re-exported for tests
    fetch_lead_timeline as _fetch_lead_timeline,
    lead_exists as _lead_exists,
)
from backend.services.lead_contact import (  # noqa: F401  re-exported for tests
    auto_promote_new_to_contacted as _auto_promote_new_to_contacted,
    build_followup_email_html as _build_followup_email_html,
    fetch_business_name as _fetch_business_name,
    fetch_lead_with_channel as _fetch_lead_with_channel,
)
from backend.services.lead_ai_summary import (  # noqa: F401  re-exported for tests
    build_lead_transcript as _build_lead_transcript,
    fetch_lead_summary_inputs as _fetch_lead_summary_inputs,
    save_lead_summary as _save_lead_summary,
)
from backend.services.lead_bulk_ops import (  # noqa: F401  re-exported for tests
    apply_bulk_lead_updates as _apply_bulk_lead_updates,
)
from backend.services.lead_assignment import (  # noqa: F401  re-exported for tests
    assign_lead_to_member as _assign_lead_to_member,
)
from backend.services.lead_suggestions import (  # noqa: F401  re-exported for tests
    apply_or_dismiss_suggestion as _apply_or_dismiss_suggestion,
)
from backend.services.lead_scoring import score_all_leads, score_lead
from backend.services.tenant_scope import tenant_delete, tenant_insert, tenant_select, tenant_update
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


def get_supabase():
    """Backward-compatible test seam for modules that still patch leads.get_supabase."""
    return _get_service_supabase()


def get_service_supabase():
    """Preserve existing call sites while allowing get_supabase() patches to intercept."""
    return get_supabase()


@router.get("/{tenant_id}")
async def get_leads(
    tenant_id: str,
    stage: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("lead_score"),
    order: str = Query("desc"),
    assigned_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    claims: dict = Depends(_get_current_tenant),
):
    """Get leads for a tenant with filtering, sorting, and pagination."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    _ALLOWED_SORT = {"lead_score", "created_at", "name", "email", "status", "updated_at"}
    if sort not in _ALLOWED_SORT:
        sort = "lead_score"

    db = get_service_supabase()
    try:
        query = tenant_select(
            db,
            "leads",
            tenant_id,
            "id, client_id, name, email, phone, status, lead_score, lead_temperature, "
            "areas_of_interest, tags, assigned_to, deal_value, created_at, updated_at, "
            "enrichment_source",
            count="exact",
        )

        if stage:
            query = query.eq("status", stage)

        if assigned_to:
            if assigned_to == "unassigned":
                query = query.is_("assigned_to", "null")
            else:
                query = query.eq("assigned_to", assigned_to)

        if search:
            import re
            safe_search = re.sub(r"[^a-zA-Z0-9@_ \-+.]", "", search).strip()[:100]
            if safe_search:
                query = query.or_(
                    f"name.ilike.%{safe_search}%,email.ilike.%{safe_search}%,phone.ilike.%{safe_search}%"
                )

        desc = order.lower() == "desc"
        query = query.order(sort, desc=desc)

        # Pagination
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1)

        result = query.execute()
        total = result.count if result.count is not None else len(result.data or [])
        return {
            "leads": result.data or [],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total else 1,
        }
    except Exception:
        logger.warning("Leads query failed for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=503, detail="Leads query failed — please retry")


@router.get("/{tenant_id}/summary")
async def get_lead_summary(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Get a summary of lead counts by stage."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        result = tenant_select(db, "leads", tenant_id, "status, lead_score").execute()
        leads = result.data or []
        return {
            "total": len(leads),
            "new": sum(1 for l in leads if l.get("status") == "new"),
            "contacted": sum(1 for l in leads if l.get("status") == "contacted"),
            "appointment_booked": sum(1 for l in leads if l.get("status") == "appointment_booked"),
            "closed": sum(1 for l in leads if l.get("status") == "closed"),
            "lost": sum(1 for l in leads if l.get("status") == "lost"),
        }
    except Exception:
        logger.warning("Lead summary query failed for tenant %s", tenant_id, exc_info=True)
        raise HTTPException(status_code=503, detail="Lead summary query failed — please retry")


@router.post("/{tenant_id}/score-all", response_model=ScoreAllResponse)
@limiter.limit("3/minute")
async def rescore_all(request: Request, tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Re-score all leads for a tenant."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, score_all_leads, tenant_id)
    return ScoreAllResponse(**result)


@router.get("/{tenant_id}/{lead_id}/score", response_model=LeadScoreResponse)
async def get_lead_score(
    tenant_id: str, lead_id: str, claims: dict = Depends(_get_current_tenant)
):
    """Get detailed score breakdown for a single lead."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        result = score_lead(lead_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadScoreResponse(**result)


class LeadCreateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = "new"
    lead_temperature: str | None = None
    areas_of_interest: str | None = None
    deal_value: float | None = None
    expected_close_date: str | None = None


@router.post("/{tenant_id}", status_code=201)
async def create_lead(
    tenant_id: str,
    req: LeadCreateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a lead manually (e.g. from pipeline Add Deal)."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not req.name and not req.email and not req.phone:
        raise HTTPException(status_code=400, detail="At least one of name, email, or phone is required")

    db = get_service_supabase()
    lead_data = {
        "client_id": tenant_id,
        "name": req.name,
        "email": req.email,
        "phone": req.phone,
        "status": req.status or "new",
        "lead_temperature": req.lead_temperature,
        "areas_of_interest": req.areas_of_interest,
        "source": "manual",
    }
    if req.deal_value is not None:
        lead_data["deal_value"] = req.deal_value
    if req.expected_close_date:
        lead_data["expected_close_date"] = req.expected_close_date

    # Remove None values
    lead_data = {k: v for k, v in lead_data.items() if v is not None}

    result = tenant_insert(db, "leads", tenant_id, lead_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create lead")

    lead = result.data[0]
    log_activity(tenant_id=tenant_id, lead_id=lead["id"], activity_type="lead_created",
                 description=f"Lead created manually: {req.name or req.email or req.phone}",
                 metadata={"performed_by": claims.get("team_member_id") or claims.get("tenant_id"),
                           "performed_by_name": claims.get("name") or claims.get("email") or "Owner"})
    fire_event_background(tenant_id, "lead.created", {"lead_id": lead["id"], "name": req.name, "source": "manual"})

    return lead


@router.patch("/{tenant_id}/{lead_id}")
async def update_lead(
    tenant_id: str,
    lead_id: str,
    req: LeadUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a lead's fields."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    db = get_service_supabase()
    result = tenant_update(db, "leads", tenant_id, updates).eq("id", lead_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    fire_event_background(tenant_id, "lead.updated", {
        "lead_id": lead_id,
        "updated_fields": list(updates.keys()),
        **updates,
    })

    # Fire status-change event when status is explicitly updated
    if "status" in updates:
        fire_event_background(tenant_id, "lead.status_changed", {
            "lead_id": lead_id,
            "new_status": updates["status"],
            "source": "leads_update",
        })

    return result.data[0]


@router.delete("/{tenant_id}/{lead_id}", status_code=204)
async def delete_lead(
    tenant_id: str,
    lead_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a lead."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    result = tenant_delete(db, "leads", tenant_id).eq("id", lead_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    return Response(status_code=204)


class QuickEmailRequest(BaseModel):
    subject: str
    message: str


@router.post("/{tenant_id}/{lead_id}/email")
async def send_lead_email(
    tenant_id: str,
    lead_id: str,
    req: QuickEmailRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Send a quick follow-up email to a lead."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        lead = _fetch_lead_with_channel(db, tenant_id, lead_id, "email")
    except LookupError as exc:
        if str(exc) == "no_channel":
            raise HTTPException(status_code=400, detail="Lead has no email address")
        raise HTTPException(status_code=404, detail="Lead not found")

    business_name = _fetch_business_name(db, tenant_id)
    body_html = _build_followup_email_html(req.message, business_name)

    result = await send_email(
        to=lead["email"],
        subject=req.subject,
        body_html=body_html,
        tenant_id=tenant_id,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("detail", "Failed to send email"))

    log_activity(
        tenant_id=tenant_id,
        activity_type="email_sent",
        description=f"Follow-up email sent to {lead.get('name', lead['email'])}: {req.subject}",
        lead_id=lead_id,
    )

    _auto_promote_new_to_contacted(db, tenant_id, lead_id)
    return {"success": True, "detail": "Email sent"}


class QuickSmsRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1600)


@router.post("/{tenant_id}/{lead_id}/sms")
async def send_lead_sms(
    tenant_id: str,
    lead_id: str,
    req: QuickSmsRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Send a quick follow-up SMS to a lead."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        lead = _fetch_lead_with_channel(db, tenant_id, lead_id, "phone")
    except LookupError as exc:
        if str(exc) == "no_channel":
            raise HTTPException(status_code=400, detail="Lead has no phone number")
        raise HTTPException(status_code=404, detail="Lead not found")

    from backend.services.twilio_service import send_sms
    success = await send_sms(to=lead["phone"], body=req.message)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send SMS")

    log_activity(
        tenant_id=tenant_id,
        activity_type="sms_sent",
        description=f"Follow-up SMS sent to {lead.get('name', lead['phone'])}",
        lead_id=lead_id,
    )

    _auto_promote_new_to_contacted(db, tenant_id, lead_id)
    return {"success": True, "detail": "SMS sent"}


@router.get("/{tenant_id}/duplicates")
async def find_duplicate_leads(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Find potential duplicate leads by email or phone."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    return {"duplicates": _fetch_duplicate_groups(db, tenant_id)}


class MergeLeadsRequest(BaseModel):
    keep_id: str
    merge_id: str


@router.post("/{tenant_id}/merge")
async def merge_leads(
    tenant_id: str,
    req: MergeLeadsRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Merge two leads into one. Keeps keep_id, deletes merge_id.
    Fills in missing fields from merge_id into keep_id.
    Reassigns appointments and activity_log from merge_id.
    """
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        keep, merge, updates = _apply_lead_merge(
            db, tenant_id, keep_id=req.keep_id, merge_id=req.merge_id
        )
    except LookupError as exc:
        which = "Primary" if str(exc) == "keep" else "Merge"
        raise HTTPException(status_code=404, detail=f"{which} lead not found")

    log_activity(
        tenant_id=tenant_id,
        activity_type="lead_merged",
        description=f"Merged lead {merge.get('name', merge.get('email', req.merge_id))} into {keep.get('name', keep.get('email', req.keep_id))}",
        lead_id=req.keep_id,
    )

    return {"success": True, "kept_id": req.keep_id, "merged_id": req.merge_id, "fields_updated": list(updates.keys())}


@router.get("/{tenant_id}/export-csv")
async def export_leads_csv(
    tenant_id: str,
    stage: str | None = Query(None),
    search: str | None = Query(None),
    assigned_to: str | None = Query(None),
    claims: dict = Depends(_get_current_tenant),
):
    """Export filtered leads as CSV file download."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    query = _build_export_query(
        db, tenant_id, stage=stage, search=search, assigned_to=assigned_to
    )
    result = query.execute()
    csv_content = _serialize_leads_to_csv(result.data or [])
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leads-export-{tenant_id[:8]}.csv"},
    )


@router.post("/{tenant_id}/import")
async def import_leads_csv(
    tenant_id: str,
    file: UploadFile,
    claims: dict = Depends(_get_current_tenant),
):
    """Import leads from a CSV file. Max 500 rows per upload."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    try:
        parsed_rows, errors, col_map = _parse_csv_for_import(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not col_map:
        raise HTTPException(
            status_code=400,
            detail=f"No recognized columns. Expected: {', '.join(sorted(set(_CSV_FIELD_MAP.values())))}"
        )

    db = get_service_supabase()
    all_emails = [ld.get("email") for _, ld in parsed_rows if ld.get("email")]
    existing_by_email = _fetch_existing_emails(db, tenant_id, [e for e in all_emails if e])

    created, updated = _apply_import_batch(
        db,
        tenant_id,
        parsed_rows=parsed_rows,
        existing_by_email=existing_by_email,
        errors=errors,
        fire_event=fire_event_background,
    )

    return {
        "created": created,
        "updated": updated,
        "errors": errors[:20],
        "total_errors": len(errors),
    }


class AssignLeadRequest(BaseModel):
    assigned_to: str | None = None  # team_member UUID or null to unassign


@router.put("/{tenant_id}/{lead_id}/assign")
async def assign_lead(
    tenant_id: str,
    lead_id: str,
    req: AssignLeadRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Assign or unassign a lead to a team member."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    performer_id = claims.get("team_member_id") or claims.get("tenant_id")
    performer_name = claims.get("name") or claims.get("email") or "Owner"
    try:
        return _assign_lead_to_member(
            db,
            tenant_id,
            lead_id,
            assigned_to=req.assigned_to,
            performer_id=performer_id,
            performer_name=performer_name,
        )
    except LookupError as exc:
        if str(exc) == "member":
            raise HTTPException(status_code=404, detail="Team member not found")
        raise HTTPException(status_code=404, detail="Lead not found")


# --- Lead Update Suggestions ---


@router.get("/{tenant_id}/suggestions")
async def list_lead_suggestions(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List pending AI-generated lead update suggestions."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    result = (
        tenant_select(db, "activity_log", tenant_id, "id, lead_id, description, metadata, created_at")
        .eq("activity_type", "lead_suggestion")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return {"suggestions": result.data or []}


class SuggestionAction(BaseModel):
    action: str  # "approve" or "dismiss"


@router.post("/{tenant_id}/suggestions/{suggestion_id}")
async def handle_suggestion(
    tenant_id: str,
    suggestion_id: str,
    req: SuggestionAction,
    claims: dict = Depends(_get_current_tenant),
):
    """Approve or dismiss a lead update suggestion."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        return _apply_or_dismiss_suggestion(db, tenant_id, suggestion_id, req.action)
    except ValueError:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'dismiss'")
    except LookupError:
        raise HTTPException(status_code=404, detail="Suggestion not found")


@router.post("/{tenant_id}/{lead_id}/generate-summary")
async def generate_lead_summary(
    tenant_id: str,
    lead_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate an AI summary of a lead's conversation history."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    try:
        messages = _fetch_lead_summary_inputs(db, tenant_id, lead_id)
    except LookupError as exc:
        code = str(exc)
        if code == "not_found":
            raise HTTPException(status_code=404, detail="Lead not found")
        if code == "no_conversation":
            raise HTTPException(status_code=400, detail="Lead has no linked conversation")
        if code == "too_short":
            raise HTTPException(status_code=400, detail="Conversation too short to summarize")
        raise HTTPException(status_code=400, detail="No conversation messages found")

    transcript = _build_lead_transcript(messages)

    try:
        resp = await call_claude_messages(
            operation="leads.generate_summary",
            model="claude-sonnet-4-6",
            max_tokens=150,
            temperature=0,
            timeout=15.0,
            system="Summarize this customer conversation in 1-2 sentences. Focus on: what the customer needs, any decisions made, and next steps. Be concise.",
            messages=[{"role": "user", "content": transcript}],
            metadata={"tenant_id": tenant_id, "lead_id": lead_id, "message_count": len(messages)},
        )
        summary = resp.text.strip()
    except Exception:
        logger.exception("Failed to generate AI summary for lead %s", lead_id)
        raise HTTPException(status_code=502, detail="AI summary generation failed")

    _save_lead_summary(db, tenant_id, lead_id, summary)
    return {"summary": summary}


# --- Lead Activity Timeline ---


@router.get("/{tenant_id}/{lead_id}/activity")
async def get_lead_activity(
    tenant_id: str,
    lead_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get activity timeline for a specific lead."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    if not _lead_exists(db, tenant_id, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")

    return {"timeline": _fetch_lead_timeline(db, tenant_id, lead_id)}


class BulkUpdateRequest(BaseModel):
    lead_ids: list[str] = Field(..., min_length=1, max_length=100)
    status: str | None = None
    assigned_to: str | None = None
    tags_add: list[str] | None = None  # Tags to add (union with existing)


@router.post("/{tenant_id}/bulk-update")
async def bulk_update_leads(
    tenant_id: str,
    req: BulkUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Update status, assignment, or tags for multiple leads at once."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not req.status and not req.assigned_to and not req.tags_add:
        raise HTTPException(status_code=400, detail="Nothing to update. Provide status, assigned_to, or tags_add.")

    db = get_service_supabase()
    updated, errors = _apply_bulk_lead_updates(
        db,
        tenant_id,
        lead_ids=req.lead_ids,
        status=req.status,
        assigned_to=req.assigned_to,
        tags_add=req.tags_add,
    )
    return {"updated": updated, "failed": len(errors), "failed_ids": errors}


@router.get("/{tenant_id}/debug")
async def debug_lead_capture(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Debug endpoint: visibility into lead capture health for a tenant.

    Returns recent lead counts and sample IDs to help diagnose whether
    widget lead capture is working correctly. Owner-only access.
    """
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if claims.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Owner or admin access required")

    db = get_service_supabase()

    try:
        # Total leads count
        total_result = (
            tenant_select(db, "leads", tenant_id, "id", count="exact")
            .execute()
        )
        total_leads = total_result.count or 0
    except Exception:
        logger.error("debug_lead_capture: total count failed for %s", tenant_id, exc_info=True)
        total_leads = -1

    try:
        # Leads created in the last 7 days
        from datetime import datetime, timedelta, timezone
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent_result = (
            tenant_select(db, "leads", tenant_id, "id", count="exact")
            .gte("created_at", week_ago)
            .execute()
        )
        leads_last_7_days = recent_result.count or 0
    except Exception:
        logger.error("debug_lead_capture: recent count failed for %s", tenant_id, exc_info=True)
        leads_last_7_days = -1

    try:
        # Most recent lead created_at timestamp
        latest_result = (
            tenant_select(db, "leads", tenant_id, "id, created_at, email, phone")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        latest_leads = latest_result.data or []
        last_lead_created_at = latest_leads[0]["created_at"] if latest_leads else None
        sample_lead_ids = [l["id"] for l in latest_leads]
        has_email_leads = any(l.get("email") for l in latest_leads)
    except Exception:
        logger.error("debug_lead_capture: sample query failed for %s", tenant_id, exc_info=True)
        last_lead_created_at = None
        sample_lead_ids = []
        has_email_leads = False

    logger.info(
        "debug_lead_capture: tenant=%s total=%s last_7d=%s last_created=%s",
        tenant_id, total_leads, leads_last_7_days, last_lead_created_at,
    )

    return {
        "total_leads": total_leads,
        "leads_last_7_days": leads_last_7_days,
        "last_lead_created_at": last_lead_created_at,
        "has_email_leads": has_email_leads,
        "sample_lead_ids": sample_lead_ids,
    }
