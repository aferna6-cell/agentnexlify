"""Lead management endpoints."""

import csv
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response

from pydantic import BaseModel

from backend.models.database import get_supabase
from backend.models.schemas import LeadScoreResponse, LeadUpdateRequest, ScoreAllResponse
from backend.routers.auth import _get_current_tenant
from backend.services.activity import log_activity
from backend.services.email_sender import send_email
from backend.services.lead_scoring import score_all_leads, score_lead
from backend.services.webhook_dispatcher import fire_event_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])


@router.get("/{tenant_id}")
async def get_leads(
    tenant_id: str,
    stage: str | None = Query(None),
    search: str | None = Query(None),
    sort: str = Query("lead_score"),
    order: str = Query("desc"),
    claims: dict = Depends(_get_current_tenant),
):
    """Get all leads for a tenant, with optional filtering/sorting."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    _ALLOWED_SORT = {"lead_score", "created_at", "name", "email", "status", "updated_at"}
    if sort not in _ALLOWED_SORT:
        sort = "lead_score"

    db = get_supabase()
    try:
        query = db.table("leads").select("*").eq("client_id", tenant_id)

        if stage:
            query = query.eq("status", stage)

        if search:
            safe_search = search.replace(",", "").replace(".", "").strip()
            if safe_search:
                query = query.or_(
                    f"name.ilike.%{safe_search}%,email.ilike.%{safe_search}%,phone.ilike.%{safe_search}%"
                )

        desc = order.lower() == "desc"
        query = query.order(sort, desc=desc)

        result = query.execute()
        return {"leads": result.data or []}
    except Exception:
        logger.warning("Leads query failed for tenant %s", tenant_id, exc_info=True)
        return {"leads": []}


@router.get("/{tenant_id}/summary")
async def get_lead_summary(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Get a summary of lead counts by stage."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_supabase()
    try:
        result = (
            db.table("leads")
            .select("status, lead_score")
            .eq("client_id", tenant_id)
            .execute()
        )
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
        return {"total": 0, "new": 0, "contacted": 0, "appointment_booked": 0, "closed": 0, "lost": 0}


@router.post("/{tenant_id}/score-all", response_model=ScoreAllResponse)
async def rescore_all(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """Re-score all leads for a tenant."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = score_all_leads(tenant_id)
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

    db = get_supabase()
    result = (
        db.table("leads")
        .update(updates)
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    fire_event_background(tenant_id, "lead.updated", {
        "lead_id": lead_id,
        "updated_fields": list(updates.keys()),
        **updates,
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

    db = get_supabase()
    result = (
        db.table("leads")
        .delete()
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
        .execute()
    )
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

    db = get_supabase()
    lead_result = (
        db.table("leads")
        .select("id, email, name")
        .eq("id", lead_id)
        .eq("client_id", tenant_id)
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
        current = db.table("leads").select("status").eq("id", lead_id).limit(1).execute()
        if current.data and current.data[0].get("status") == "new":
            db.table("leads").update({"status": "contacted"}).eq("id", lead_id).execute()
    except Exception:
        logger.warning("Failed to auto-update lead status after email", exc_info=True)

    return {"success": True, "detail": "Email sent"}


# CSV column name → DB column name mapping
_CSV_FIELD_MAP = {
    "name": "name",
    "email": "email",
    "phone": "phone",
    "stage": "status",
    "status": "status",
    "score": "lead_score",
    "source": "lead_temperature",
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

    db = get_supabase()
    created = 0
    updated = 0
    errors = []

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

        # Validate status
        if lead_data.get("status") and lead_data["status"] not in _VALID_STATUSES:
            lead_data["status"] = "new"

        # Validate lead_score
        if lead_data.get("lead_score"):
            try:
                lead_data["lead_score"] = int(lead_data["lead_score"])
            except ValueError:
                del lead_data["lead_score"]

        # Dedup by email if available
        if lead_data.get("email"):
            try:
                existing = (
                    db.table("leads")
                    .select("id")
                    .eq("client_id", tenant_id)
                    .eq("email", lead_data["email"])
                    .limit(1)
                    .execute()
                )
                if existing.data:
                    updates = {k: v for k, v in lead_data.items() if k != "email"}
                    if updates:
                        db.table("leads").update(updates).eq("id", existing.data[0]["id"]).execute()
                    updated += 1
                    continue
            except Exception as e:
                logger.warning("Import dedup check failed row %d: %s", i, e)

        # Insert new lead
        lead_data["client_id"] = tenant_id
        lead_data.setdefault("status", "new")
        try:
            result = db.table("leads").insert(lead_data).execute()
            if result.data:
                created += 1
                fire_event_background(tenant_id, "lead.created", {
                    "lead_id": result.data[0]["id"],
                    "name": lead_data.get("name"),
                    "email": lead_data.get("email"),
                    "source": "csv_import",
                })
            else:
                errors.append({"row": i, "error": "Insert returned no data"})
        except Exception as e:
            errors.append({"row": i, "error": str(e)[:100]})

    return {
        "created": created,
        "updated": updated,
        "errors": errors[:20],
        "total_errors": len(errors),
    }
