"""Lead management endpoints."""

import asyncio
import csv
import io
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
    lead_result = (
        tenant_select(db, "leads", tenant_id, "id, email, name")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    if not lead_result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = lead_result.data[0]
    if not lead.get("email"):
        raise HTTPException(status_code=400, detail="Lead has no email address")

    import html as html_mod
    safe_message = html_mod.escape(req.message).replace("\n", "<br>")

    # Get business name for email context
    tenant_result = (
        db.table("tenants")
        .select("business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    business_name = tenant_result.data[0]["business_name"] if tenant_result.data else "Our Team"

    body_html = (
        f"<p>{safe_message}</p>"
        f"<p style='margin-top:16px;color:#666;font-size:0.9em;'>— {html_mod.escape(business_name)}</p>"
    )

    result = await send_email(
        to=lead["email"],
        subject=req.subject,
        body_html=body_html,
        tenant_id=tenant_id,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("detail", "Failed to send email"))

    # Log activity
    log_activity(
        tenant_id=tenant_id,
        activity_type="email_sent",
        description=f"Follow-up email sent to {lead.get('name', lead['email'])}: {req.subject}",
        lead_id=lead_id,
    )

    # Auto-update lead status from "new" to "contacted"
    try:
        current = tenant_select(db, "leads", tenant_id, "status").eq("id", lead_id).limit(1).execute()
        if current.data and current.data[0].get("status") == "new":
            tenant_update(db, "leads", tenant_id, {"status": "contacted"}).eq("id", lead_id).execute()
    except Exception:
        logger.warning("Failed to auto-update lead status after email", exc_info=True)

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
    lead_result = (
        tenant_select(db, "leads", tenant_id, "id, phone, name")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    if not lead_result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = lead_result.data[0]
    if not lead.get("phone"):
        raise HTTPException(status_code=400, detail="Lead has no phone number")

    from backend.services.twilio_service import send_sms
    success = await send_sms(to=lead["phone"], body=req.message, tenant_id=tenant_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send SMS")

    log_activity(
        tenant_id=tenant_id,
        activity_type="sms_sent",
        description=f"Follow-up SMS sent to {lead.get('name', lead['phone'])}",
        lead_id=lead_id,
    )

    # Auto-update lead status from "new" to "contacted"
    try:
        current = tenant_select(db, "leads", tenant_id, "status").eq("id", lead_id).limit(1).execute()
        if current.data and current.data[0].get("status") == "new":
            tenant_update(db, "leads", tenant_id, {"status": "contacted"}).eq("id", lead_id).execute()
    except Exception:
        logger.warning("Failed to auto-update lead status after SMS", exc_info=True)

    return {"success": True, "detail": "SMS sent"}


@router.get("/{tenant_id}/duplicates")
async def find_duplicate_leads(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Find potential duplicate leads by email or phone."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    result = tenant_select(
        db,
        "leads",
        tenant_id,
        "id, name, email, phone, status, lead_score, created_at",
    ).execute()
    leads = result.data or []

    # Group by email and phone
    email_groups: dict[str, list] = {}
    phone_groups: dict[str, list] = {}
    for lead in leads:
        email = (lead.get("email") or "").strip().lower()
        phone = (lead.get("phone") or "").strip()
        if email:
            email_groups.setdefault(email, []).append(lead)
        if phone:
            phone_groups.setdefault(phone, []).append(lead)

    # Find groups with 2+ leads (true duplicates)
    duplicate_sets = []
    seen_ids = set()
    for key, group in {**email_groups, **phone_groups}.items():
        if len(group) < 2:
            continue
        ids = tuple(sorted(l["id"] for l in group))
        if ids in seen_ids:
            continue
        seen_ids.add(ids)
        duplicate_sets.append({
            "match_field": "email" if "@" in key else "phone",
            "match_value": key,
            "leads": group,
        })

    return {"duplicates": duplicate_sets}


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

    # Fetch both leads
    keep_result = tenant_select(db, "leads", tenant_id).eq("id", req.keep_id).limit(1).execute()
    merge_result = tenant_select(db, "leads", tenant_id).eq("id", req.merge_id).limit(1).execute()

    if not keep_result.data:
        raise HTTPException(status_code=404, detail="Primary lead not found")
    if not merge_result.data:
        raise HTTPException(status_code=404, detail="Merge lead not found")

    keep = keep_result.data[0]
    merge = merge_result.data[0]

    # Fill in missing fields from merge into keep
    fillable = ["name", "email", "phone", "lead_type", "areas_of_interest",
                 "timeline", "budget", "conversation_summary", "next_steps"]
    updates = {}
    for field in fillable:
        if not keep.get(field) and merge.get(field):
            updates[field] = merge[field]

    # Merge tags (union)
    keep_tags = keep.get("tags") or []
    merge_tags = merge.get("tags") or []
    combined_tags = list(dict.fromkeys(keep_tags + merge_tags))  # Preserve order, dedup
    if combined_tags != keep_tags:
        updates["tags"] = combined_tags

    # Keep the higher lead score
    if (merge.get("lead_score") or 0) > (keep.get("lead_score") or 0):
        updates["lead_score"] = merge["lead_score"]

    if updates:
        tenant_update(db, "leads", tenant_id, updates).eq("id", req.keep_id).execute()

    # Reassign appointments from merge to keep
    try:
        tenant_update(db, "appointments", tenant_id, {"lead_id": req.keep_id}).eq("lead_id", req.merge_id).execute()
    except Exception:
        logger.warning("Failed to reassign appointments during merge", exc_info=True)

    # Reassign activity log entries
    try:
        tenant_update(db, "activity_log", tenant_id, {"lead_id": req.keep_id}).eq("lead_id", req.merge_id).execute()
    except Exception:
        logger.warning("Failed to reassign activity_log during merge", exc_info=True)

    # Reassign client notes
    try:
        tenant_update(db, "client_notes", tenant_id, {"lead_id": req.keep_id}).eq("lead_id", req.merge_id).execute()
    except Exception:
        logger.warning("Failed to reassign client_notes during merge", exc_info=True)

    # Delete the merged lead
    tenant_delete(db, "leads", tenant_id).eq("id", req.merge_id).execute()

    log_activity(
        tenant_id=tenant_id,
        activity_type="lead_merged",
        description=f"Merged lead {merge.get('name', merge.get('email', req.merge_id))} into {keep.get('name', keep.get('email', req.keep_id))}",
        lead_id=req.keep_id,
    )

    return {"success": True, "kept_id": req.keep_id, "merged_id": req.merge_id, "fields_updated": list(updates.keys())}


# CSV column name → DB column name mapping
_CSV_FIELD_MAP = {
    "name": "name",
    "email": "email",
    "phone": "phone",
    "stage": "status",
    "status": "status",
    "score": "lead_score",
    "source": "source",
    "temperature": "lead_temperature",
    "service interest": "areas_of_interest",
    "service_interest": "areas_of_interest",
    "areas_of_interest": "areas_of_interest",
    "timeline": "timeline",
    "budget": "budget",
    "notes": "conversation_summary",
    "conversation_summary": "conversation_summary",
    "next_steps": "next_steps",
    "lead_type": "lead_type",
}

_VALID_STATUSES = {"new", "contacted", "appointment_booked", "closed", "lost"}
_MAX_IMPORT_ROWS = 500


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

    query = tenant_select(
        db,
        "leads",
        tenant_id,
        "name, email, phone, status, lead_score, lead_temperature, "
        "areas_of_interest, tags, conversation_summary, deal_value, "
        "source, created_at, updated_at",
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

    query = query.order("created_at", desc=True).limit(5000)
    result = query.execute()
    leads_data = result.data or []

    # Build CSV
    output = io.StringIO()
    fields = [
        "name", "email", "phone", "status", "lead_score", "lead_temperature",
        "areas_of_interest", "tags", "conversation_summary", "deal_value",
        "source", "created_at", "updated_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for lead in leads_data:
        # Convert tags array to comma-separated string
        row = {**lead}
        if isinstance(row.get("tags"), list):
            row["tags"] = ", ".join(row["tags"])
        writer.writerow(row)

    csv_content = output.getvalue()
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

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no headers")

    # Map CSV headers to DB columns
    col_map = {}
    for header in reader.fieldnames:
        key = header.strip().lower().replace(" ", "_")
        if key in _CSV_FIELD_MAP:
            col_map[header] = _CSV_FIELD_MAP[key]
        elif key.replace("_", " ") in _CSV_FIELD_MAP:
            col_map[header] = _CSV_FIELD_MAP[key.replace("_", " ")]

    if not col_map:
        raise HTTPException(
            status_code=400,
            detail=f"No recognized columns. Expected: {', '.join(sorted(set(_CSV_FIELD_MAP.values())))}"
        )

    db = get_service_supabase()
    created = 0
    updated = 0
    errors = []

    # Pre-parse all rows and collect emails for batch dedup (avoids N+1 queries)
    parsed_rows = []
    for i, row in enumerate(reader, start=2):
        if i - 1 > _MAX_IMPORT_ROWS:
            errors.append({"row": i, "error": f"Stopped at {_MAX_IMPORT_ROWS} rows"})
            break

        lead_data = {}
        for csv_col, db_col in col_map.items():
            val = (row.get(csv_col) or "").strip()
            if val:
                lead_data[db_col] = val

        if not lead_data.get("email") and not lead_data.get("phone") and not lead_data.get("name"):
            errors.append({"row": i, "error": "No name, email, or phone"})
            continue

        if lead_data.get("status") and lead_data["status"] not in _VALID_STATUSES:
            lead_data["status"] = "new"

        if lead_data.get("lead_score"):
            try:
                lead_data["lead_score"] = int(lead_data["lead_score"])
            except ValueError:
                del lead_data["lead_score"]

        parsed_rows.append((i, lead_data))

    # Batch-fetch existing leads by email (single query instead of N queries)
    all_emails = [ld.get("email") for _, ld in parsed_rows if ld.get("email")]
    existing_by_email = {}
    if all_emails:
        try:
            existing_result = (
                tenant_select(db, "leads", tenant_id, "id, email")
                .in_("email", list(set(all_emails)))
                .execute()
            )
            for lead in (existing_result.data or []):
                if lead.get("email"):
                    existing_by_email[lead["email"].lower()] = lead["id"]
        except Exception as e:
            logger.warning("Import batch dedup query failed: %s", e)

    # Process rows with dedup lookup from cache; collect new leads for batch insert
    new_rows: list[tuple[int, dict]] = []
    for i, lead_data in parsed_rows:
        email = (lead_data.get("email") or "").lower()
        if email and email in existing_by_email:
            updates = {k: v for k, v in lead_data.items() if k != "email"}
            if updates:
                try:
                    tenant_update(db, "leads", tenant_id, updates).eq("id", existing_by_email[email]).execute()
                except Exception as e:
                    errors.append({"row": i, "error": str(e)[:100]})
                    continue
            updated += 1
            continue

        lead_data.setdefault("status", "new")
        new_rows.append((i, lead_data))

    # Insert all new leads in one query (was one insert per row). Fall back to
    # per-row inserts on batch failure so row-level errors stay reportable.
    if new_rows:
        inserted_rows = []
        try:
            result = tenant_insert(db, "leads", tenant_id, [ld for _, ld in new_rows]).execute()
            inserted_rows = list(result.data or [])
            if not inserted_rows:
                raise ValueError("Batch insert returned no data")
        except Exception:
            logger.warning("Import batch insert failed; falling back to per-row inserts", exc_info=True)
            inserted_rows = []
            for i, lead_data in new_rows:
                try:
                    result = tenant_insert(db, "leads", tenant_id, lead_data).execute()
                    if result.data:
                        inserted_rows.extend(result.data)
                    else:
                        errors.append({"row": i, "error": "Insert returned no data"})
                except Exception as e:
                    errors.append({"row": i, "error": str(e)[:100]})

        created += len(inserted_rows)
        for row in inserted_rows:
            fire_event_background(tenant_id, "lead.created", {
                "lead_id": row["id"],
                "name": row.get("name"),
                "email": row.get("email"),
                "source": "csv_import",
            })

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

    # Verify team member exists if assigning
    if req.assigned_to:
        member = (
            tenant_select(db, "team_members", tenant_id, "id, name, email")
            .eq("id", req.assigned_to)
            .limit(1)
            .execute()
        )
        if not member.data:
            raise HTTPException(status_code=404, detail="Team member not found")

    result = (
        tenant_update(db, "leads", tenant_id, {"assigned_to": req.assigned_to})
        .eq("id", lead_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Log the assignment with performing user info
    member_name = member.data[0]["name"] if req.assigned_to and member.data else "nobody"
    performer_id = claims.get("team_member_id") or claims.get("tenant_id")
    performer_name = claims.get("name") or claims.get("email") or "Owner"
    try:
        log_activity(
            tenant_id=tenant_id,
            activity_type="assignment",
            description=f"Lead assigned to {member_name}",
            lead_id=lead_id,
            metadata={
                "assigned_to": req.assigned_to,
                "assigned_to_name": member_name,
                "performed_by": performer_id,
                "performed_by_name": performer_name,
            },
        )
    except Exception:
        logger.warning("Failed to log assignment activity", exc_info=True)

    return result.data[0]


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
    if req.action not in ("approve", "dismiss"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'dismiss'")

    db = get_service_supabase()

    # Fetch the suggestion
    suggestion = (
        tenant_select(db, "activity_log", tenant_id, "id, lead_id, metadata")
        .eq("id", suggestion_id)
        .eq("activity_type", "lead_suggestion")
        .limit(1)
        .execute()
    )
    if not suggestion.data:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    entry = suggestion.data[0]

    if req.action == "approve":
        # Apply the suggested updates to the lead
        suggestions = (entry.get("metadata") or {}).get("suggestions", {})
        if suggestions and entry.get("lead_id"):
            updates = {field: s["new"] for field, s in suggestions.items()}
            tenant_update(db, "leads", tenant_id, updates).eq("id", entry["lead_id"]).execute()
            logger.info("Approved suggestion %s: updated lead %s with %s", suggestion_id, entry["lead_id"], list(updates.keys()))

    # Delete the suggestion (both approve and dismiss)
    tenant_delete(db, "activity_log", tenant_id).eq("id", suggestion_id).execute()

    return {"success": True, "action": req.action}


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

    # Get the lead's conversation
    lead = (
        tenant_select(db, "leads", tenant_id, "conversation_id, name")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    if not lead.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    conv_id = lead.data[0].get("conversation_id")
    if not conv_id:
        raise HTTPException(status_code=400, detail="Lead has no linked conversation")

    # Fetch messages
    conv = (
        tenant_select(db, "conversations", tenant_id, "messages")
        .eq("id", conv_id)
        .limit(1)
        .execute()
    )
    if not conv.data or not conv.data[0].get("messages"):
        raise HTTPException(status_code=400, detail="No conversation messages found")

    messages = conv.data[0]["messages"]
    if len(messages) < 2:
        raise HTTPException(status_code=400, detail="Conversation too short to summarize")

    # Build transcript (last 30 messages)
    transcript = "\n".join(
        f"{'Visitor' if m['role'] == 'user' else 'Agent'}: {m['content']}"
        for m in messages[-30:]
    )

    # Generate AI summary
    try:
        resp = await call_claude_messages(
            operation="leads.generate_summary",
            model="claude-sonnet-4-6",
            max_tokens=150,
            temperature=0,
            timeout=15.0,
            system="Summarize this customer conversation in 1-2 sentences. Focus on: what the customer needs, any decisions made, and next steps. Be concise.",
            messages=[{"role": "user", "content": transcript[:3000]}],
            metadata={"tenant_id": tenant_id, "lead_id": lead_id, "message_count": len(messages)},
        )
        summary = resp.text.strip()
    except Exception:
        logger.exception("Failed to generate AI summary for lead %s", lead_id)
        raise HTTPException(status_code=502, detail="AI summary generation failed")

    # Save the summary
    tenant_update(db, "leads", tenant_id, {"conversation_summary": summary}).eq("id", lead_id).execute()

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

    # Verify lead exists
    lead = (
        tenant_select(db, "leads", tenant_id, "id")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    if not lead.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Fetch activity log entries for this lead
    activity = (
        tenant_select(db, "activity_log", tenant_id, "id, activity_type, description, metadata, created_at")
        .eq("lead_id", lead_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    # Also fetch appointments for this lead
    appointments = (
        tenant_select(db, "appointments", tenant_id, "id, customer_name, start_time, status, created_at")
        .eq("lead_id", lead_id)
        .order("start_time", desc=True)
        .limit(20)
        .execute()
    )

    # Also fetch email events for this lead
    email_events = (
        tenant_select(db, "email_events", tenant_id, "id, event_type, details, created_at")
        .eq("lead_id", lead_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )

    # Merge all into a single timeline
    timeline = []

    for a in (activity.data or []):
        timeline.append({
            "type": a.get("activity_type") or "activity",
            "description": a.get("description") or "",
            "metadata": a.get("metadata"),
            "created_at": a["created_at"],
        })

    for appt in (appointments.data or []):
        status = appt.get("status") or "scheduled"
        timeline.append({
            "type": f"appointment_{status}",
            "description": f"Appointment ({status}): {appt.get('customer_name') or 'Customer'} at {appt.get('start_time', '')}",
            "metadata": {"appointment_id": appt["id"]},
            "created_at": appt["created_at"],
        })

    for ev in (email_events.data or []):
        timeline.append({
            "type": f"email_{ev.get('event_type', 'event')}",
            "description": f"Email {ev.get('event_type', 'event')}",
            "metadata": ev.get("details"),
            "created_at": ev["created_at"],
        })

    # Sort by date descending
    timeline.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    return {"timeline": timeline[:100]}


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
    updated = 0
    errors = []

    for lead_id in req.lead_ids:
        try:
            update_data = {}
            if req.status:
                update_data["status"] = req.status
            if req.assigned_to is not None:
                update_data["assigned_to"] = req.assigned_to if req.assigned_to else None

            if req.tags_add:
                # Fetch existing tags and merge
                existing = tenant_select(db, "leads", tenant_id, "tags").eq("id", lead_id).limit(1).execute()
                if existing.data:
                    current_tags = existing.data[0].get("tags") or []
                    merged = list(set(current_tags + req.tags_add))
                    update_data["tags"] = merged

            if update_data:
                result = (
                    tenant_update(db, "leads", tenant_id, update_data)
                    .eq("id", lead_id)
                    .execute()
                )
                if result.data:
                    updated += 1
                else:
                    errors.append(lead_id)
        except Exception as e:
            logger.warning("Bulk update failed for lead %s: %s", lead_id, str(e))
            errors.append(lead_id)

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
