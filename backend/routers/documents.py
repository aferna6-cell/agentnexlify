"""Documents & E-Signatures — create, send, and sign documents digitally."""

import html as html_mod
import logging
import re
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.dependencies import verify_tenant
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant, require_role
from backend.services.email_sender import send_email
from backend.services.twilio_service import send_sms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DocumentCreate(BaseModel):
    title: str = Field(..., max_length=500)
    template_html: str = Field(..., max_length=100000)
    lead_id: str | None = None
    signer_name: str | None = Field(None, max_length=200)
    signer_email: str | None = Field(None, max_length=320)
    signer_phone: str | None = Field(None, max_length=30)
    expires_days: int | None = Field(None, ge=1, le=365)
    notes: str | None = Field(None, max_length=5000)


class DocumentFromTemplate(BaseModel):
    template_id: str
    title: str = Field(..., max_length=500)
    lead_id: str | None = None
    signer_name: str | None = Field(None, max_length=200)
    signer_email: str | None = Field(None, max_length=320)
    signer_phone: str | None = Field(None, max_length=30)
    variables: dict[str, str] = Field(default_factory=dict)
    expires_days: int | None = Field(None, ge=1, le=365)


class SendDocumentRequest(BaseModel):
    method: str = Field(..., pattern="^(email|sms|both)$")


class SignDocumentRequest(BaseModel):
    signature_data: str = Field(..., max_length=500000)
    signer_name: str = Field(..., max_length=200)


class TemplateCreate(BaseModel):
    name: str = Field(..., max_length=200)
    category: str | None = Field(None, max_length=100)
    template_html: str = Field(..., max_length=100000)
    variables: list[str] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    category: str | None = Field(None, max_length=100)
    template_html: str | None = Field(None, max_length=100000)
    variables: list[str] | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Document CRUD
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}")
async def list_documents(
    tenant_id: str,
    status: str | None = Query(None),
    lead_id: str | None = Query(None),
    claims: dict = Depends(_get_current_tenant),
):
    """List documents for a tenant."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()
    q = db.table("documents").select("*").eq("tenant_id", tenant_id).order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    if lead_id:
        q = q.eq("lead_id", lead_id)
    result = q.limit(200).execute()
    return {"documents": result.data or []}


@router.post("/{tenant_id}")
async def create_document(
    tenant_id: str,
    req: DocumentCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a new document from raw HTML."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()

    data = {
        "tenant_id": tenant_id,
        "title": req.title,
        "template_html": req.template_html,
        "rendered_html": req.template_html,
        "status": "draft",
    }
    if req.lead_id:
        data["lead_id"] = req.lead_id
    if req.signer_name:
        data["signer_name"] = req.signer_name
    if req.signer_email:
        data["signer_email"] = req.signer_email
    if req.signer_phone:
        data["signer_phone"] = req.signer_phone
    if req.notes:
        data["notes"] = req.notes
    if req.expires_days:
        data["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=req.expires_days)).isoformat()

    try:
        result = db.table("documents").insert(data).execute()
    except Exception:
        logger.exception("Failed to create document for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create document")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create document")
    return result.data[0]


@router.post("/{tenant_id}/from-template")
async def create_from_template(
    tenant_id: str,
    req: DocumentFromTemplate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a document from a saved template, substituting variables."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()

    # Load template
    tmpl = db.table("document_templates").select("*").eq("id", req.template_id).eq("tenant_id", tenant_id).limit(1).execute()
    if not tmpl.data:
        raise HTTPException(status_code=404, detail="Template not found")

    template_html = tmpl.data[0]["template_html"]

    # Substitute variables: {{variable_name}} → value
    rendered = template_html
    for key, value in req.variables.items():
        safe_val = html_mod.escape(str(value))
        rendered = rendered.replace(f"{{{{{key}}}}}", safe_val)

    data = {
        "tenant_id": tenant_id,
        "title": req.title,
        "template_html": template_html,
        "rendered_html": rendered,
        "status": "draft",
    }
    if req.lead_id:
        data["lead_id"] = req.lead_id
    if req.signer_name:
        data["signer_name"] = req.signer_name
    if req.signer_email:
        data["signer_email"] = req.signer_email
    if req.signer_phone:
        data["signer_phone"] = req.signer_phone
    if req.expires_days:
        data["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=req.expires_days)).isoformat()

    try:
        result = db.table("documents").insert(data).execute()
    except Exception:
        logger.exception("Failed to create document from template for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to create document")

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create document")
    return result.data[0]


@router.get("/{tenant_id}/{document_id}")
async def get_document(
    tenant_id: str,
    document_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single document with details."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()
    result = db.table("documents").select("*").eq("id", document_id).eq("tenant_id", tenant_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = result.data[0]

    # Attach lead info if linked
    if doc.get("lead_id"):
        try:
            lead = db.table("leads").select("name, email, phone").eq("id", doc["lead_id"]).eq("client_id", tenant_id).limit(1).execute()
            doc["lead"] = lead.data[0] if lead.data else None
        except Exception:
            doc["lead"] = None

    return doc


@router.delete("/{tenant_id}/{document_id}")
async def delete_document(
    tenant_id: str,
    document_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Delete a draft document."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()

    # Only allow deleting draft documents
    doc = db.table("documents").select("status").eq("id", document_id).eq("tenant_id", tenant_id).limit(1).execute()
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.data[0]["status"] != "draft":
        raise HTTPException(status_code=400, detail="Can only delete draft documents")

    db.table("documents").delete().eq("id", document_id).eq("tenant_id", tenant_id).execute()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Send & Sign
# ---------------------------------------------------------------------------

@router.post("/{tenant_id}/{document_id}/send")
async def send_document(
    tenant_id: str,
    document_id: str,
    req: SendDocumentRequest,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Send a document for signature via email and/or SMS."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()

    doc = db.table("documents").select("*").eq("id", document_id).eq("tenant_id", tenant_id).limit(1).execute()
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = doc.data[0]

    if doc["status"] not in ("draft", "sent"):
        raise HTTPException(status_code=400, detail=f"Cannot send a {doc['status']} document")

    if not doc.get("signer_email") and not doc.get("signer_phone"):
        raise HTTPException(status_code=400, detail="Document has no signer email or phone")

    # Build signing URL
    signing_url = f"https://app.agentnexlify.com/sign/{doc['signing_token']}"

    # Load tenant info
    tenant = db.table("tenants").select("business_name").eq("id", tenant_id).limit(1).execute()
    business_name = tenant.data[0]["business_name"] if tenant.data else "Business"
    safe_biz = html_mod.escape(business_name)
    safe_title = html_mod.escape(doc["title"])
    safe_signer = html_mod.escape(doc.get("signer_name") or "there")

    sent_via = []

    # Email
    if req.method in ("email", "both") and doc.get("signer_email"):
        subject = f"Document for your signature: {doc['title']}"
        body = (
            f"<h2>Hi {safe_signer},</h2>"
            f"<p><strong>{safe_biz}</strong> has sent you a document to review and sign:</p>"
            f"<p style='font-size:16px;font-weight:600;'>{safe_title}</p>"
            f'<p style="text-align:center;margin:24px 0;">'
            f'<a href="{signing_url}" style="background:#4f46e5;color:#fff;padding:14px 28px;'
            f'border-radius:8px;text-decoration:none;font-weight:600;font-size:16px;">Review & Sign</a></p>'
            f"<p style='color:#666;font-size:13px;'>This link is unique to you. Do not share it.</p>"
        )
        try:
            result = await send_email(to=doc["signer_email"], subject=subject, body_html=body, tenant_id=tenant_id)
            if result.get("success"):
                sent_via.append("email")
        except Exception:
            logger.exception("Failed to send document email for doc %s", document_id)

    # SMS
    if req.method in ("sms", "both") and doc.get("signer_phone"):
        sms_body = (
            f"{business_name} sent you a document to sign: \"{doc['title']}\". "
            f"Review and sign here: {signing_url}"
        )
        try:
            ok = await send_sms(to=doc["signer_phone"], body=sms_body)
            if ok:
                sent_via.append("sms")
        except Exception:
            logger.exception("Failed to send document SMS for doc %s", document_id)

    if not sent_via:
        raise HTTPException(status_code=500, detail="Failed to send document")

    # Update status
    db.table("documents").update({
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_via": ", ".join(sent_via),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", document_id).execute()

    return {"sent_via": sent_via, "signing_url": signing_url}


@router.get("/public/sign/{token}")
@limiter.limit("30/minute")
async def get_document_for_signing(request: Request, token: str):
    """Public endpoint: load a document for signing by token."""
    db = get_supabase()
    result = db.table("documents").select(
        "id, title, rendered_html, status, signer_name, expires_at, tenant_id"
    ).eq("signing_token", token).limit(1).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = result.data[0]

    if doc["status"] == "signed":
        return {"status": "already_signed", "title": doc["title"], "signer_name": doc["signer_name"]}
    if doc["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="This document has been cancelled")
    if doc["status"] == "expired":
        raise HTTPException(status_code=400, detail="This document has expired")

    # Check expiry
    if doc.get("expires_at"):
        expires = datetime.fromisoformat(doc["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires:
            db.table("documents").update({"status": "expired"}).eq("id", doc["id"]).execute()
            raise HTTPException(status_code=400, detail="This document has expired")

    # Mark as viewed
    if doc["status"] == "sent":
        db.table("documents").update({
            "status": "viewed",
            "viewed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", doc["id"]).execute()

    # Load business name
    tenant = db.table("tenants").select("business_name").eq("id", doc["tenant_id"]).limit(1).execute()
    business_name = tenant.data[0]["business_name"] if tenant.data else ""

    return {
        "title": doc["title"],
        "html": doc["rendered_html"],
        "signer_name": doc.get("signer_name") or "",
        "business_name": business_name,
        "status": "ready",
    }


@router.post("/public/sign/{token}")
@limiter.limit("10/minute")
async def sign_document(request: Request, token: str, req: SignDocumentRequest):
    """Public endpoint: submit a signature."""
    db = get_supabase()
    result = db.table("documents").select("id, status, tenant_id, title, signer_email, lead_id").eq("signing_token", token).limit(1).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = result.data[0]

    if doc["status"] == "signed":
        raise HTTPException(status_code=400, detail="Document already signed")
    if doc["status"] in ("cancelled", "expired"):
        raise HTTPException(status_code=400, detail=f"Document is {doc['status']}")

    # Record signature
    client_ip = request.client.host if request.client else "unknown"
    db.table("documents").update({
        "status": "signed",
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "signature_data": req.signature_data,
        "signature_ip": client_ip,
        "signer_name": req.signer_name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", doc["id"]).execute()

    # Log activity
    try:
        db.table("activity_log").insert({
            "tenant_id": doc["tenant_id"],
            "lead_id": doc.get("lead_id"),
            "activity_type": "document_signed",
            "description": f"Document \"{doc['title']}\" signed by {req.signer_name}",
        }).execute()
    except Exception:
        logger.warning("Failed to log document signing activity", exc_info=True)

    return {"status": "signed", "signed_at": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# Templates CRUD
# ---------------------------------------------------------------------------

@router.get("/{tenant_id}/templates")
async def list_templates(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """List document templates."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()
    result = (
        db.table("document_templates")
        .select("id, name, category, variables, is_active, created_at")
        .eq("tenant_id", tenant_id)
        .eq("is_active", True)
        .order("name")
        .execute()
    )
    return result.data or []


@router.post("/{tenant_id}/templates")
async def create_template(
    tenant_id: str,
    req: TemplateCreate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Create a reusable document template."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()

    # Auto-detect variables in template: {{variable_name}}
    detected = re.findall(r"\{\{(\w+)\}\}", req.template_html)
    variables = list(set(req.variables + detected))

    result = db.table("document_templates").insert({
        "tenant_id": tenant_id,
        "name": req.name,
        "category": req.category,
        "template_html": req.template_html,
        "variables": variables,
    }).execute()

    return result.data[0] if result.data else {}


@router.put("/{tenant_id}/templates/{template_id}")
async def update_template(
    tenant_id: str,
    template_id: str,
    req: TemplateUpdate,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Update a document template."""
    verify_tenant(claims, tenant_id)
    updates = {k: v for k, v in req.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Re-detect variables if template changed
    if "template_html" in updates:
        detected = re.findall(r"\{\{(\w+)\}\}", updates["template_html"])
        updates["variables"] = list(set(updates.get("variables", []) + detected))

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    db = get_supabase()
    result = db.table("document_templates").update(updates).eq("id", template_id).eq("tenant_id", tenant_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")
    return result.data[0]


@router.delete("/{tenant_id}/templates/{template_id}")
async def delete_template(
    tenant_id: str,
    template_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Soft-delete a document template."""
    verify_tenant(claims, tenant_id)
    db = get_supabase()
    result = (
        db.table("document_templates")
        .update({"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", template_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"deleted": True}
