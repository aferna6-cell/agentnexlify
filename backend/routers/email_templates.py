"""Email templates API — reusable template library for automation sequences."""

import html
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.models.database import get_supabase
from backend.models.schemas import EmailTemplateCreate, EmailTemplateUpdate
from backend.routers.auth import _get_current_tenant
from backend.services.email_sender import render_template

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/email-templates", tags=["email-templates"])

# Pre-built starter templates (system-level, available to all tenants)
STARTER_TEMPLATES = [
    {
        "id": "starter-welcome",
        "name": "Welcome Email",
        "category": "welcome",
        "subject_template": "Welcome to {{business_name}}!",
        "body_template": (
            "<h2>Hi {{name}},</h2>"
            "<p>Thanks for reaching out to <strong>{{business_name}}</strong>! "
            "We received your inquiry and wanted to personally welcome you.</p>"
            "<p>One of our team members will be in touch shortly to help "
            "with whatever you need.</p>"
            "<p>In the meantime, feel free to reply to this email with any questions.</p>"
            "<p>Best regards,<br>The {{business_name}} Team</p>"
        ),
        "is_shared": True,
    },
    {
        "id": "starter-followup",
        "name": "Friendly Follow-Up",
        "category": "follow_up",
        "subject_template": "Following up — {{business_name}}",
        "body_template": (
            "<h2>Hi {{name}},</h2>"
            "<p>Just wanted to check in and see if you had any questions "
            "about what we discussed.</p>"
            "<p>We're here to help whenever you're ready. "
            "Simply reply to this email or give us a call.</p>"
            "<p>Looking forward to hearing from you!</p>"
            "<p>Best,<br>The {{business_name}} Team</p>"
        ),
        "is_shared": True,
    },
    {
        "id": "starter-reminder",
        "name": "Appointment Reminder",
        "category": "reminder",
        "subject_template": "Reminder: Your upcoming appointment with {{business_name}}",
        "body_template": (
            "<h2>Hi {{name}},</h2>"
            "<p>This is a friendly reminder about your upcoming appointment "
            "with <strong>{{business_name}}</strong>.</p>"
            "<p>If you need to reschedule or have any questions, "
            "just reply to this email and we'll take care of it.</p>"
            "<p>We look forward to seeing you!</p>"
            "<p>Best,<br>The {{business_name}} Team</p>"
        ),
        "is_shared": True,
    },
    {
        "id": "starter-review",
        "name": "Review Request",
        "category": "review",
        "subject_template": "How was your experience, {{name}}?",
        "body_template": (
            "<h2>Hi {{name}},</h2>"
            "<p>Thank you for choosing <strong>{{business_name}}</strong>! "
            "We hope everything went well.</p>"
            "<p>If you have a moment, we'd love to hear about your experience. "
            "Your feedback helps us improve and helps others find us.</p>"
            '<p><a href="{{review_link}}" style="display:inline-block;padding:12px 24px;'
            "background:#4f46e5;color:#fff;text-decoration:none;border-radius:6px;"
            'font-weight:600;">Leave a Review</a></p>'
            "<p>Thank you for your support!</p>"
            "<p>&mdash; The {{business_name}} Team</p>"
        ),
        "is_shared": True,
    },
    {
        "id": "starter-promo",
        "name": "Special Offer",
        "category": "promotion",
        "subject_template": "A special offer just for you, {{name}}!",
        "body_template": (
            "<h2>Hi {{name}},</h2>"
            "<p>As a valued customer of <strong>{{business_name}}</strong>, "
            "we wanted to share something special with you.</p>"
            "<p style=\"padding:16px;background:#f0f9ff;border-left:4px solid #4f46e5;"
            'border-radius:4px;margin:16px 0;">'
            "<strong>Your Exclusive Offer:</strong><br>"
            "Use code <strong>VALUED10</strong> for 10% off your next visit!</p>"
            "<p>This offer is our way of saying thank you. "
            "We appreciate your trust in us.</p>"
            "<p>Best,<br>The {{business_name}} Team</p>"
        ),
        "is_shared": True,
    },
    {
        "id": "starter-reengagement",
        "name": "We Miss You",
        "category": "follow_up",
        "subject_template": "We haven't heard from you, {{name}}",
        "body_template": (
            "<h2>Hi {{name}},</h2>"
            "<p>It's been a while since we last connected, and we "
            "wanted to reach out from <strong>{{business_name}}</strong>.</p>"
            "<p>We're still here and ready to help whenever you need us. "
            "If there's anything we can do, just reply to this email.</p>"
            "<p>We'd love to hear from you again!</p>"
            "<p>Best,<br>The {{business_name}} Team</p>"
        ),
        "is_shared": True,
    },
]

SAMPLE_CONTEXT = {
    "name": "Alex Johnson",
    "email": "alex@example.com",
    "phone": "(555) 123-4567",
    "business_name": "Your Business",
    "review_link": "https://g.page/your-business/review",
}


def _verify_tenant(tenant_id: str, claims: dict) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")


@router.get("/{tenant_id}")
async def list_templates(tenant_id: str, claims: dict = Depends(_get_current_tenant)):
    """List all email templates (starter + tenant custom)."""
    _verify_tenant(tenant_id, claims)
    db = get_supabase()

    custom = (
        db.table("email_templates")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "templates": (custom.data or []),
        "starter_templates": STARTER_TEMPLATES,
    }


@router.post("/{tenant_id}")
async def create_template(
    tenant_id: str,
    req: EmailTemplateCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a custom email template."""
    _verify_tenant(tenant_id, claims)
    db = get_supabase()

    result = db.table("email_templates").insert({
        "tenant_id": tenant_id,
        "name": req.name,
        "category": req.category,
        "subject_template": req.subject_template,
        "body_template": req.body_template,
    }).execute()

    return {"template": result.data[0]}


@router.put("/{tenant_id}/{template_id}")
async def update_template(
    tenant_id: str,
    template_id: str,
    req: EmailTemplateUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a custom email template."""
    _verify_tenant(tenant_id, claims)
    db = get_supabase()

    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if req.name is not None:
        updates["name"] = req.name
    if req.category is not None:
        updates["category"] = req.category
    if req.subject_template is not None:
        updates["subject_template"] = req.subject_template
    if req.body_template is not None:
        updates["body_template"] = req.body_template

    result = (
        db.table("email_templates")
        .update(updates)
        .eq("id", template_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")

    return {"template": result.data[0]}


@router.delete("/{tenant_id}/{template_id}")
async def delete_template(
    tenant_id: str,
    template_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a custom email template."""
    _verify_tenant(tenant_id, claims)
    db = get_supabase()

    result = (
        db.table("email_templates")
        .delete()
        .eq("id", template_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found")

    return {"deleted": True}


@router.post("/{tenant_id}/preview")
async def preview_template(
    tenant_id: str,
    req: EmailTemplateCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Render a template with sample data for preview."""
    _verify_tenant(tenant_id, claims)

    # Use tenant business name if available
    db = get_supabase()
    tenant = db.table("tenants").select("business_name").eq("id", tenant_id).limit(1).execute()
    context = {**SAMPLE_CONTEXT}
    if tenant.data and tenant.data[0].get("business_name"):
        context["business_name"] = tenant.data[0]["business_name"]

    rendered_subject = render_template(req.subject_template, context)
    rendered_body = render_template(req.body_template, context)

    return {
        "subject": rendered_subject,
        "body": rendered_body,
        "context_used": context,
    }
