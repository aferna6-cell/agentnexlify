"""Onboarding workflow orchestration.

DB-touching multi-step routines for the ``/complete`` and ``/status`` endpoints.
Routers stay thin; orchestration logic + phase decomposition lives here.

Test compatibility: ``_generate_ai_content`` is kept in the router module so the
existing ``monkeypatch.setattr("backend.routers.onboarding._generate_ai_content",
...)`` patch path survives. The router passes its module-level binding here via
the ``ai_content_fn`` kwarg, and Python resolves the monkeypatched attribute
dynamically at call time.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from fastapi import HTTPException

from backend.services.business_profiles import get_widget_defaults

logger = logging.getLogger(__name__)


AiContentFn = Callable[..., Awaitable[dict[str, Any] | None]]


@dataclass
class OnboardingCompleteResult:
    """Aggregated state from the complete-onboarding flow."""

    tenant: dict[str, Any] = field(default_factory=dict)
    configured: dict[str, bool] = field(
        default_factory=lambda: {
            "business_info": False,
            "hours": False,
            "website_crawl": False,
            "faqs": False,
            "ai_content": False,
            "industry_pack": False,
        }
    )
    ai_content_generated: bool = False
    crawl_started: bool = False
    faqs_created: int = 0
    industry_pack_applied: bool = False
    industry_pack_key: str | None = None


@dataclass
class OnboardingStatusResult:
    """Computed onboarding progress for the GET /status endpoint."""

    has_business_info: bool = False
    has_hours: bool = False
    has_website: bool = False
    has_faqs: bool = False
    has_widget_customized: bool = False
    onboarding_completed: bool = False
    completion_percentage: int = 0


# ---------------------------------------------------------------------------
# Phase helpers — each one is independently testable and easy to scan.
# ---------------------------------------------------------------------------


def _load_tenant(db, tenant_id: str) -> dict[str, Any]:
    tenant_result = (
        db.table("tenants")
        .select("id, business_name, business_page_enabled")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_result.data[0]


def _update_tenant_record(db, tenant_id: str, req, result: OnboardingCompleteResult) -> None:
    tenant_update: dict[str, Any] = {
        "business_name": req.business_name,
        "business_type": req.business_type,
        "city": req.city,
        "autopilot_enabled": True,
        "onboarding_completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if req.phone:
        tenant_update["notification_phone"] = req.phone
    if req.website_url:
        tenant_update["website_url"] = req.website_url
    if req.services:
        tenant_update["business_services"] = req.services

    try:
        db.table("tenants").update(tenant_update).eq("id", tenant_id).execute()
        result.configured["business_info"] = True
    except Exception:
        logger.exception("Failed to update tenant %s during onboarding", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to update business info")


def _update_widget_config(db, tenant_id: str, req) -> None:
    widget_defaults = get_widget_defaults(req.business_type, req.business_name)
    existing_widget: dict[str, Any] = {}
    try:
        existing_widget_result = (
            db.table("widget_configs")
            .select("bot_name, primary_color, greeting_message, position")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if existing_widget_result.data:
            existing_widget = existing_widget_result.data[0] or {}
    except Exception:
        logger.warning(
            "Failed to read existing widget config during onboarding for %s",
            tenant_id,
            exc_info=True,
        )

    widget_updates: dict[str, Any] = {
        "bot_name": req.widget_bot_name or existing_widget.get("bot_name") or widget_defaults["bot_name"],
        "primary_color": req.widget_primary_color or existing_widget.get("primary_color") or widget_defaults["primary_color"],
        "greeting_message": req.widget_greeting_message or existing_widget.get("greeting_message") or widget_defaults["greeting_message"],
        "position": req.widget_position or existing_widget.get("position") or widget_defaults["position"],
    }
    try:
        db.table("widget_configs").update(widget_updates).eq("tenant_id", tenant_id).execute()
    except Exception:
        logger.error(
            "Failed to update widget_configs during onboarding for %s",
            tenant_id,
            exc_info=True,
        )


def _apply_industry_pack(db, tenant_id: str, req, result: OnboardingCompleteResult) -> None:
    try:
        from backend.services.industry_packs import load_pack
        from backend.services.industry_packs.seed import apply_pack_to_tenant

        pack = load_pack(req.business_type)
        result.industry_pack_key = pack.key
        pack_result = apply_pack_to_tenant(db, tenant_id, pack, dry_run=False)
        result.industry_pack_applied = True
        result.configured["industry_pack"] = True
        if pack_result.errors:
            logger.warning(
                "Industry pack seeded with warnings for tenant=%s pack=%s errors=%s",
                tenant_id,
                pack.key,
                pack_result.errors,
            )
    except Exception:
        logger.warning(
            "Failed to apply industry pack during onboarding for tenant %s",
            tenant_id,
            exc_info=True,
        )


def _seed_business_hours(db, tenant_id: str, req, result: OnboardingCompleteResult) -> None:
    if not req.hours:
        return
    try:
        existing_hours = (
            db.table("business_hours")
            .select("id")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        hours_data: dict[str, Any] = {
            "tenant_id": tenant_id,
            "hours": dict(req.hours),
            "timezone": req.hours.get("timezone", "America/New_York"),
        }
        if "timezone" in hours_data["hours"]:
            tz = hours_data["hours"].pop("timezone")
            hours_data["timezone"] = tz

        if existing_hours.data:
            db.table("business_hours").update(hours_data).eq("id", existing_hours.data[0]["id"]).execute()
        else:
            db.table("business_hours").insert(hours_data).execute()
        result.configured["hours"] = True
    except Exception:
        logger.exception("Failed to create business_hours for tenant %s", tenant_id)


async def _trigger_website_crawl(tenant_id: str, req, result: OnboardingCompleteResult) -> None:
    if not req.website_url:
        return
    try:
        from backend.services.website_crawler import start_crawl

        await start_crawl(tenant_id, req.website_url)
        result.crawl_started = True
        result.configured["website_crawl"] = True
    except Exception:
        logger.exception("Failed to start website crawl for tenant %s", tenant_id)


def _seed_service_faqs(db, tenant_id: str, req, result: OnboardingCompleteResult) -> None:
    if not req.services:
        return
    services_str = ", ".join(req.services)
    faq_entries: list[dict[str, Any]] = [
        {
            "tenant_id": tenant_id,
            "question": "What services do you offer?",
            "answer": f"We offer the following services: {services_str}.",
            "category": "services",
            "is_active": True,
        },
        {
            "tenant_id": tenant_id,
            "question": "Where are you located?",
            "answer": f"We are located in {req.city}. Feel free to contact us for our exact address.",
            "category": "general",
            "is_active": True,
        },
    ]
    if req.phone:
        faq_entries.append({
            "tenant_id": tenant_id,
            "question": "How can I contact you?",
            "answer": f"You can reach us at {req.phone} or through this chat widget.",
            "category": "general",
            "is_active": True,
        })

    inserted_any = False
    for entry in faq_entries:
        try:
            db.table("faq_entries").insert(entry).execute()
            result.faqs_created += 1
            inserted_any = True
        except Exception:
            logger.exception("Failed to create FAQ entry for tenant %s", tenant_id)

    if inserted_any:
        result.configured["faqs"] = True


def _seed_wizard_faqs(db, tenant_id: str, req, result: OnboardingCompleteResult) -> None:
    if not req.faqs:
        return
    try:
        faq_rows = [
            {
                "tenant_id": tenant_id,
                "question": faq.question,
                "answer": faq.answer,
                "category": "wizard",
                "is_active": True,
            }
            for faq in req.faqs
        ]
        db.table("faq_entries").insert(faq_rows).execute()
        result.configured["faqs"] = True
    except Exception:
        logger.error("Failed to insert wizard FAQs for tenant %s", tenant_id, exc_info=True)


async def _apply_ai_content(
    db,
    tenant_id: str,
    req,
    result: OnboardingCompleteResult,
    ai_content_fn: AiContentFn,
) -> None:
    try:
        ai_content = await ai_content_fn(
            business_name=req.business_name,
            business_type=req.business_type,
            city=req.city,
            services=req.services,
        )
    except Exception:
        logger.exception("AI content generation failed for tenant %s", tenant_id)
        return

    if not ai_content:
        return

    for faq in ai_content.get("faqs", []):
        try:
            db.table("faq_entries").insert({
                "tenant_id": tenant_id,
                "question": faq["question"],
                "answer": faq["answer"],
                "category": "ai_generated",
                "is_active": True,
            }).execute()
            result.faqs_created += 1
        except Exception:
            logger.exception("Failed to insert AI-generated FAQ for tenant %s", tenant_id)

    if result.tenant.get("business_page_enabled") and ai_content.get("about_section"):
        try:
            db.table("tenants").update(
                {"business_description": ai_content["about_section"]}
            ).eq("id", tenant_id).execute()
        except Exception:
            logger.exception("Failed to update business page for tenant %s", tenant_id)

    result.ai_content_generated = True
    result.configured["ai_content"] = True


def _seed_welcome_sequence(db, tenant_id: str, req) -> None:
    try:
        existing_seqs = (
            db.table("email_sequences")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if existing_seqs.data:
            return
        biz = req.business_name or "our team"
        seq_result = db.table("email_sequences").insert({
            "tenant_id": tenant_id,
            "name": "Welcome Series",
            "trigger_type": "lead_captured",
            "is_active": True,
        }).execute()
        if not seq_result.data:
            return
        seq_id = seq_result.data[0]["id"]
        welcome_steps = [
            {
                "sequence_id": seq_id,
                "step_order": 1,
                "delay_days": 0,
                "delay_hours": 0,
                "subject": f"Thanks for reaching out to {biz}!",
                "body": (
                    f"<p>Hi {{{{name}}}},</p>"
                    f"<p>Thanks for getting in touch with {biz}! We received your message and "
                    f"wanted to make sure you know we're here to help.</p>"
                    f"<p>If you have any questions, just reply to this email or chat with us on our website.</p>"
                    f"<p>Best,<br/>{biz}</p>"
                ),
                "email_type": "html",
                "is_active": True,
            },
            {
                "sequence_id": seq_id,
                "step_order": 2,
                "delay_days": 2,
                "delay_hours": 0,
                "subject": f"Here's what {biz} can do for you",
                "body": (
                    f"<p>Hi {{{{name}}}},</p>"
                    f"<p>We wanted to share a bit more about what we offer and how we can help.</p>"
                    f"<p>Whether you're looking for a quick question answered or ready to get started, "
                    f"we're just a message away.</p>"
                    f"<p>Visit our website to learn more or book a time that works for you.</p>"
                    f"<p>Best,<br/>{biz}</p>"
                ),
                "email_type": "html",
                "is_active": True,
            },
            {
                "sequence_id": seq_id,
                "step_order": 3,
                "delay_days": 5,
                "delay_hours": 0,
                "subject": f"Ready to get started with {biz}?",
                "body": (
                    f"<p>Hi {{{{name}}}},</p>"
                    f"<p>Just checking in! If you're ready to move forward or have any questions, "
                    f"we'd love to hear from you.</p>"
                    f"<p>You can reply to this email, give us a call, or book an appointment "
                    f"directly through our website.</p>"
                    f"<p>Looking forward to working with you!</p>"
                    f"<p>Best,<br/>{biz}</p>"
                ),
                "email_type": "html",
                "is_active": True,
            },
        ]
        db.table("email_sequence_steps").insert(welcome_steps).execute()
        logger.info("Auto-created Welcome Series with 3 steps for tenant %s", tenant_id)
    except Exception:
        logger.warning(
            "Failed to auto-create welcome email sequence for tenant %s",
            tenant_id,
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Public orchestrators
# ---------------------------------------------------------------------------


async def run_onboarding_complete(
    db,
    tenant_id: str,
    req,
    *,
    ai_content_fn: AiContentFn,
) -> OnboardingCompleteResult:
    """Run all 9 onboarding phases. Raises HTTPException on missing tenant.

    The ``ai_content_fn`` is injected so the caller (router) can pass its
    module-level ``_generate_ai_content`` binding — that keeps the existing
    ``monkeypatch.setattr("backend.routers.onboarding._generate_ai_content",
    ...)`` test patch path intact.
    """
    result = OnboardingCompleteResult()
    result.tenant = _load_tenant(db, tenant_id)
    _update_tenant_record(db, tenant_id, req, result)
    _update_widget_config(db, tenant_id, req)
    _apply_industry_pack(db, tenant_id, req, result)
    _seed_business_hours(db, tenant_id, req, result)
    await _trigger_website_crawl(tenant_id, req, result)
    _seed_service_faqs(db, tenant_id, req, result)
    _seed_wizard_faqs(db, tenant_id, req, result)
    await _apply_ai_content(db, tenant_id, req, result, ai_content_fn)
    _seed_welcome_sequence(db, tenant_id, req)
    return result


def compute_onboarding_status(db, tenant_id: str) -> OnboardingStatusResult:
    """Compute onboarding progress. Raises HTTPException on missing tenant."""
    tenant_result = (
        db.table("tenants")
        .select(
            "id, business_name, business_type, city, phone, website_url, "
            "autopilot_enabled, onboarding_completed_at"
        )
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = tenant_result.data[0]
    result = OnboardingStatusResult()

    result.has_business_info = bool(
        tenant.get("business_name")
        and tenant.get("business_type")
        and tenant.get("city")
    )

    try:
        hours_result = (
            db.table("business_hours")
            .select("id")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        result.has_hours = bool(hours_result.data)
    except Exception:
        logger.warning("Failed to check business_hours for tenant %s", tenant_id)

    try:
        website_result = (
            db.table("website_content")
            .select("id, crawl_status")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        result.has_website = bool(
            website_result.data
            and website_result.data[0].get("crawl_status") == "completed"
        )
    except Exception:
        logger.warning("Failed to check website_content for tenant %s", tenant_id)

    try:
        faq_result = (
            db.table("faq_entries")
            .select("id")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        result.has_faqs = bool(faq_result.data)
    except Exception:
        logger.warning("Failed to check faq_entries for tenant %s", tenant_id)

    try:
        widget_result = (
            db.table("widget_configs")
            .select("bot_name, primary_color, greeting_message")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if widget_result.data:
            wc = widget_result.data[0]
            result.has_widget_customized = bool(
                wc.get("bot_name")
                and wc["bot_name"] != "AI Assistant"
                or wc.get("primary_color")
                and wc["primary_color"] != "#00BFFF"
            )
    except Exception:
        logger.warning("Failed to check widget_configs for tenant %s", tenant_id)

    result.onboarding_completed = bool(tenant.get("onboarding_completed_at"))

    checks = [
        result.has_business_info,
        result.has_hours,
        result.has_website,
        result.has_faqs,
        result.has_widget_customized,
    ]
    completed_count = sum(1 for c in checks if c)
    result.completion_percentage = int((completed_count / len(checks)) * 100)

    return result
