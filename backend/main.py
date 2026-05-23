"""AgentNexLiFy — FastAPI application entry point."""

import asyncio

from backend.services.task_utils import safe_create_task
import logging
import os
import socket
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pythonjsonlogger.json import JsonFormatter
from slowapi.errors import RateLimitExceeded
from starlette.datastructures import Headers, MutableHeaders

from backend.config import is_production, settings
from backend.limiter import limiter
from backend.routers import (
    action_items,
    analytics,
    appointments,
    auth,
    automations,
    bids,
    billing,
    booking_page,
    business_page,
    calls,
    channels_facebook,
    chat_flows,
    client_portal,
    clients,
    content,
    content_repurpose,
    conversation_inbox,
    conversations,
    crawl,
    csat,
    custom_fields,
    documents,
    email_sequences,
    email_templates,
    faq,
    forms,
    gbp,
    integrations,
    invoices,
    jobs,
    leads,
    local_seo,
    managed_agent_runs,
    marketing_analytics,
    marketing_campaigns,
    menu,
    notifications,
    onboarding,
    orders,
    phone,
    pipeline,
    pipeline_automations,
    resend_webhooks,
    revenue,
    reviews,
    scoring_config,
    sequences,
    smart_lists,
    sms,
    snippets,
    social_media,
    stripe_webhooks,
    support,
    tag_definitions,
    team,
    twilio_webhooks,
    waitlist,
    webhook_deliveries,
    webhooks,
    widget_chat,
    widget_config,
    widget_lead,
    wizard_analytics,
    ab_tests,
    automation_rules,
    admin_analytics,
    admin_promotions,
    zapier,
)

# --- JSON logging ---
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.root.handlers = [_handler]
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy httpx request logs — Railway misparses them as errors
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# --- Sentry (optional) ---
if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

_startup_time: float = 0.0
_LOCK_OWNER = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}"
_VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"
_cors_warning_logged = False


def _app_uptime_seconds() -> float:
    return round(time.time() - _startup_time, 1) if _startup_time else 0.0


def _app_version() -> str:
    for env_name in ("APP_VERSION", "RELEASE_VERSION", "SERVICE_VERSION"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value[:80]
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip() or "unknown"
    except Exception:
        return "unknown"


def _build_sha() -> str:
    for env_name in (
        "APP_COMMIT_SHA",
        "RAILWAY_GIT_COMMIT_SHA",
        "VERCEL_GIT_COMMIT_SHA",
        "GITHUB_SHA",
        "GIT_SHA",
        "COMMIT_SHA",
        "SOURCE_VERSION",
    ):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value[:40]
    return "unknown"


def _split_origins(raw_value: str) -> list[str]:
    origins = [
        origin.strip() for origin in (raw_value or "").split(",") if origin.strip()
    ]
    return origins or ["*"]


def _cors_origins() -> list[str]:
    global _cors_warning_logged
    raw_value = settings.cors_allowed_origins or settings.widget_allowed_origins or "*"
    origins = _split_origins(raw_value)
    if is_production() and origins == ["*"] and not _cors_warning_logged:
        logger.warning(
            "CORS allow_origins is '*'. Set CORS_ALLOWED_ORIGINS or "
            "WIDGET_ALLOWED_ORIGINS to make production origins explicit."
        )
        _cors_warning_logged = True
    return origins


def _readiness_snapshot() -> dict:
    effective_jwt_secret = settings.jwt_secret_key or settings.api_secret_key
    effective_admin_secret = settings.admin_api_secret_key or settings.api_secret_key
    required_checks = {
        "api_secret_configured": bool(settings.api_secret_key),
        "jwt_secret_configured": bool(effective_jwt_secret),
        "admin_api_secret_configured": bool(effective_admin_secret),
    }
    if is_production():
        required_checks.update(
            {
                "supabase_url_configured": bool(settings.supabase_url),
                "supabase_key_configured": bool(settings.supabase_key),
                "supabase_service_key_configured": bool(settings.supabase_service_key),
            }
        )

    optional_checks = {
        "anthropic_configured": bool(settings.anthropic_api_key),
        "resend_configured": bool(settings.resend_api_key),
        "sentry_configured": bool(settings.sentry_dsn),
        "widget_allowed_origins_explicit": _cors_origins() != ["*"],
    }
    return {
        "required": required_checks,
        "optional": optional_checks,
        "ready": all(required_checks.values()),
    }


def _coerce_rpc_bool(data) -> bool:
    if isinstance(data, bool):
        return data
    if isinstance(data, str):
        return data.strip().lower() == "true"
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, bool):
            return first
        if isinstance(first, dict):
            value = next(iter(first.values()), False)
            return _coerce_rpc_bool(value)
    return bool(data)


async def _safe_run(name: str, fn, timeout: float = 30.0):
    """Run an automation function with a timeout. Logs results and exceptions."""
    try:
        result = await asyncio.wait_for(fn(), timeout=timeout)
        if result:
            logger.info("Automation loop: %s returned %s", name, result)
    except asyncio.TimeoutError:
        logger.warning("Automation loop: %s timed out after %.0fs", name, timeout)
    except Exception:
        logger.exception("Automation loop: %s failed", name)


def _try_acquire_automation_lock(lock_name: str, ttl_seconds: int = 90) -> bool:
    """Acquire a short DB-backed lock so only one worker runs scheduler work."""
    try:
        from backend.models.database import get_service_supabase

        result = (
            get_service_supabase()
            .rpc(
                "try_acquire_automation_lock",
                {
                    "p_name": lock_name,
                    "p_owner": _LOCK_OWNER,
                    "p_ttl_seconds": ttl_seconds,
                },
            )
            .execute()
        )
        return _coerce_rpc_bool(result.data)
    except Exception:
        if is_production():
            logger.exception("Automation lock unavailable in production")
            return False
        logger.warning("Automation lock unavailable; using dev fallback", exc_info=True)
        return True


def _release_automation_lock(lock_name: str) -> None:
    try:
        from backend.models.database import get_service_supabase

        get_service_supabase().rpc(
            "release_automation_lock",
            {"p_name": lock_name, "p_owner": _LOCK_OWNER},
        ).execute()
    except Exception:
        logger.warning("Failed to release automation lock %s", lock_name, exc_info=True)


async def _automation_loop():
    """Background loop that runs automation tasks on a tiered schedule.

    With multiple Uvicorn workers, each worker runs its own loop. A DB-backed
    short lease ensures only one worker performs scheduler work per tick.

    Tiers:
      - Every 60s  (every tick): core sequences, no-response leads, reminders
      - Every 5min (tick % 5):   notifications, review requests, onboarding, CSAT,
                                  scheduled post publishing, scheduled campaign sending
      - Every 30min (tick % 30): heavy/infrequent tasks (monthly reports, briefs,
                                  recurring invoices)
    """
    import random

    await asyncio.sleep(random.uniform(0, 30))  # Stagger workers
    from backend.services.daily_briefing import send_daily_briefings
    from backend.services.noshow_recovery import process_noshow_recovery
    from backend.services.automation_engine import (
        check_new_reviews,
        check_no_response_leads,
        process_pending_steps,
        send_appointment_reminders,
        send_csat_surveys,
        send_invoice_payment_reminders,
        send_monthly_reports,
        process_recurring_invoices,
        send_pending_review_requests,
        send_rebook_suggestions,
        send_onboarding_emails,
        send_portal_links,
        send_weekly_intelligence_briefs,
        send_weekly_digest,
        send_birthday_greetings,
        send_aftercare_instructions,
        schedule_automation_check,
    )

    tick = 0
    while True:
        tick += 1
        lock_name = "automation_loop_tick"
        if not _try_acquire_automation_lock(lock_name):
            await asyncio.sleep(60)
            continue

        try:
            # Every 60s: core automation tasks run in parallel
            core_tasks = [
                _safe_run("process_pending_steps", process_pending_steps),
                _safe_run("check_no_response_leads", check_no_response_leads),
                _safe_run("send_appointment_reminders", send_appointment_reminders),
            ]

            # Every 5 min: notifications, reminders, scheduled content, campaign recovery
            if tick % 5 == 0:
                core_tasks.extend(
                    [
                        _safe_run(
                            "send_pending_review_requests", send_pending_review_requests
                        ),
                        _safe_run("send_rebook_suggestions", send_rebook_suggestions),
                        _safe_run("send_onboarding_emails", send_onboarding_emails),
                        _safe_run("send_portal_links", send_portal_links),
                        _safe_run("send_csat_surveys", send_csat_surveys),
                        _safe_run("check_new_reviews", check_new_reviews),
                        _safe_run(
                            "send_invoice_payment_reminders",
                            send_invoice_payment_reminders,
                        ),
                        _safe_run(
                            "send_aftercare_instructions", send_aftercare_instructions
                        ),
                        _safe_run("process_scheduled_posts", _process_scheduled_posts),
                        _safe_run(
                            "process_scheduled_campaigns", _process_scheduled_campaigns
                        ),
                        _safe_run(
                            "recover_stalled_campaigns", _recover_stalled_campaigns
                        ),
                        _safe_run(
                            "run_sequence_processor",
                            email_sequences.run_sequence_processor,
                        ),
                        _safe_run(
                            "schedule_automation_check", schedule_automation_check
                        ),
                        _safe_run("process_noshow_recovery", process_noshow_recovery),
                    ]
                )

            # Every 30 min: heavy/infrequent tasks
            if tick % 30 == 0:
                core_tasks.extend(
                    [
                        _safe_run("send_monthly_reports", send_monthly_reports),
                        _safe_run(
                            "process_recurring_invoices", process_recurring_invoices
                        ),
                        _safe_run(
                            "send_weekly_intelligence_briefs",
                            send_weekly_intelligence_briefs,
                        ),
                        _safe_run("send_weekly_digest", send_weekly_digest),
                        _safe_run("send_birthday_greetings", send_birthday_greetings),
                        _safe_run("send_daily_briefings", send_daily_briefings),
                    ]
                )

            await asyncio.gather(*core_tasks)
        finally:
            _release_automation_lock(lock_name)
        await asyncio.sleep(60)


async def _recover_stalled_campaigns():
    """Mark marketing campaigns stuck in 'sending' for >30 minutes as 'failed'."""
    from datetime import datetime, timedelta, timezone
    from backend.models.database import get_service_supabase

    db = get_service_supabase()
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    try:
        stale_started = (
            db.table("marketing_campaigns")
            .select("id, name, tenant_id")
            .eq("status", "sending")
            .lt("sending_started_at", stale_cutoff)
            .limit(50)
            .execute()
        )
        stale_missing_start = []
        try:
            stale_missing_start = (
                db.table("marketing_campaigns")
                .select("id, name, tenant_id")
                .eq("status", "sending")
                .is_("sending_started_at", "null")
                .lt("created_at", stale_cutoff)
                .limit(50)
                .execute()
            ).data or []
        except Exception:
            # Some environments may not have created_at on this table yet.
            stale_missing_start = []

        stalled_rows = (stale_started.data or []) + stale_missing_start
        if not stalled_rows:
            return 0
        stalled_ids = list({row["id"] for row in stalled_rows if row.get("id")})
        db.table("marketing_campaigns").update({"status": "failed"}).in_(
            "id", stalled_ids
        ).execute()
        for cid in stalled_ids:
            logger.warning("Marked stalled campaign %s as failed", cid)
        return len(stalled_ids)
    except Exception:
        logger.exception("_recover_stalled_campaigns failed")
        return 0


async def _process_scheduled_posts():
    """Auto-publish social media posts whose scheduled_for has passed.

    Posts with status='scheduled' and scheduled_for <= now() are updated to
    status='published' with published_at set. When platform OAuth is connected
    in the future, this is where the actual API publish call will go.
    """
    from datetime import datetime, timezone
    from backend.models.database import get_service_supabase

    db = get_service_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        due_posts = (
            db.table("social_posts")
            .select("id, tenant_id, platform, content")
            .eq("status", "scheduled")
            .lte("scheduled_for", now_iso)
            .limit(100)
            .execute()
        )
        if not due_posts.data:
            return 0

        published = 0
        for post in due_posts.data:
            try:
                db.table("social_posts").update(
                    {
                        "status": "published",
                        "published_at": now_iso,
                    }
                ).eq("id", post["id"]).execute()
                published += 1
                logger.info(
                    "Auto-published scheduled social post %s (%s) for tenant %s",
                    post["id"],
                    post["platform"],
                    post["tenant_id"],
                )
            except Exception:
                logger.exception("Failed to auto-publish social post %s", post["id"])

        return published
    except Exception:
        logger.exception("_process_scheduled_posts failed")
        return 0


async def _process_scheduled_campaigns():
    """Auto-send marketing campaigns whose scheduled_for has passed.

    Campaigns with status='scheduled' and scheduled_for <= now() are picked up,
    their target leads queried, and the send dispatched as a background task —
    identical to the manual send flow.
    """
    from datetime import datetime, timezone
    from backend.models.database import get_service_supabase
    from backend.routers.marketing_campaigns import (
        _query_target_leads,
        _send_campaign_background,
    )

    db = get_service_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        due_campaigns = (
            db.table("marketing_campaigns")
            .select("*")
            .eq("status", "scheduled")
            .lte("scheduled_for", now_iso)
            .limit(20)
            .execute()
        )
        if not due_campaigns.data:
            return 0

        dispatched = 0
        for campaign in due_campaigns.data:
            campaign_id = campaign["id"]
            tenant_id = campaign["tenant_id"]
            target_filter = campaign.get("target_filter") or {}

            leads = _query_target_leads(db, tenant_id, target_filter)
            if not leads:
                # No matching leads — mark as sent with zero recipients
                db.table("marketing_campaigns").update(
                    {
                        "status": "sent",
                        "sent_at": now_iso,
                        "total_recipients": 0,
                        "total_sent": 0,
                    }
                ).eq("id", campaign_id).execute()
                logger.info(
                    "Scheduled campaign %s had no matching leads — marked as sent",
                    campaign_id,
                )
                continue

            # Mark as sending and dispatch background task
            db.table("marketing_campaigns").update(
                {
                    "status": "sending",
                    "sending_started_at": now_iso,
                }
            ).eq("id", campaign_id).execute()

            safe_create_task(
                _send_campaign_background(campaign_id, tenant_id, leads, campaign),
                name=f"campaign_{campaign_id}",
            )
            dispatched += 1
            logger.info(
                "Auto-dispatched scheduled campaign %s for tenant %s (%d leads)",
                campaign_id,
                tenant_id,
                len(leads),
            )

        return dispatched
    except Exception:
        logger.exception("_process_scheduled_campaigns failed")
        return 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _startup_time
    _startup_time = time.time()
    logger.info("AgentNexLiFy starting up")
    if not os.environ.get("API_SECRET_KEY"):
        logger.warning(
            "API_SECRET_KEY is not set; dev fallback is enabled outside production only."
        )
    if not os.environ.get("TESTING"):
        task = asyncio.create_task(_automation_loop())
    yield
    if not os.environ.get("TESTING"):
        task.cancel()
    logger.info("AgentNexLiFy shutting down")


app = FastAPI(
    title="AgentNexLiFy API",
    description="AI-powered business automation platform. Chat widget captures leads, books appointments, and automates follow-ups for small businesses. Multi-tenant SaaS with 438+ endpoints.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS ---
# allow_origins=["*"] is REQUIRED and must stay hard-coded here, because the
# embeddable widget runs on arbitrary third-party tenant domains that we do
# not know ahead of time. Dashboard routes are protected by JWT auth in the
# Authorization header, which browsers do not send cross-origin automatically,
# and allow_credentials=False prevents cookie-based CSRF.
#
# History: a previous revision wired this to `_cors_origins()`, which reads
# WIDGET_ALLOWED_ORIGINS / CORS_ALLOWED_ORIGINS from the environment. In
# production Railway had that env var set to the dashboard domains only
# ("https://app.agentnexlify.com,https://agentnexlify.com"), which caused
# every widget OPTIONS preflight from tenant customer sites to return 400
# ("invalid origin"). Widget POSTs then failed with "I'm having trouble
# connecting" in the browser. Do not re-introduce the env-driven path here —
# `_cors_origins()` is kept only for the readiness-snapshot indicator
# (`widget_allowed_origins_explicit`) so ops can still see whether an env
# override is configured.
_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Security headers ---
# Routes that may be embedded in iframes on third-party sites.
_EMBEDDABLE_PREFIXES = ("/api/v1/widget", "/api/v1/forms/public", "/api/v1/book")


def _apply_security_headers(headers: MutableHeaders, path: str) -> None:
    is_embeddable = any(path.startswith(p) for p in _EMBEDDABLE_PREFIXES)

    headers["X-Content-Type-Options"] = "nosniff"
    headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    headers["Content-Security-Policy"] = (
        (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'"
        )
        if not is_embeddable
        else (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors *"
        )
    )

    if is_embeddable:
        headers["X-Frame-Options"] = "ALLOWALL"
    else:
        headers["X-Frame-Options"] = "DENY"
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


# --- Rate limiting ---
app.state.limiter = limiter


def _rate_limit_handler_with_cors(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
        headers=_CORS_HEADERS,
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler_with_cors)


# --- Validation error handler (logs actual field errors for debugging) ---
from fastapi.exceptions import RequestValidationError


async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(
        "Validation error on %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    # Do not log raw widget bodies; they can contain PII and contact details.
    if request.url.path.startswith("/api/v1/widget"):
        logger.error("Widget validation failed; request body redacted")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
        headers=_CORS_HEADERS,
    )


app.add_exception_handler(RequestValidationError, _validation_exception_handler)


class RequestContextMiddleware:
    """ASGI middleware for request IDs, security headers, and access logs.

    This avoids BaseHTTPMiddleware's call_next/receive edge cases on error
    responses, which can stall ASGI test transports.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        headers = Headers(scope=scope)
        auth_header = headers.get("authorization", "")
        tenant_id: str | None = None
        if auth_header.startswith("Bearer "):
            try:
                from jose import jwt

                payload = jwt.get_unverified_claims(auth_header[7:])
                tenant_id = payload.get("tenant_id")
            except Exception as exc:
                logger.debug("JWT decode for logging failed: %s", exc)

        method = scope["method"]
        path = scope["path"]
        start = time.time()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = MutableHeaders(scope=message)
                response_headers["X-Request-ID"] = request_id
                _apply_security_headers(response_headers, path)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.time() - start) * 1000
            log_data = {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 1),
                "request_id": request_id,
                "tenant_id": tenant_id,
            }
            if status_code >= 500:
                logger.error("request completed", extra=log_data)
            else:
                logger.info("request completed", extra=log_data)


app.add_middleware(RequestContextMiddleware)


# --- Routers ---
app.include_router(analytics.router)
app.include_router(appointments.router)
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(faq.router)
app.include_router(automations.router)
app.include_router(billing.router)
app.include_router(clients.router)
app.include_router(email_templates.router)
app.include_router(email_sequences.router)
app.include_router(leads.router)
app.include_router(stripe_webhooks.router)
app.include_router(resend_webhooks.router)
app.include_router(sequences.router)
app.include_router(sequences.leads_router)
app.include_router(support.router)
app.include_router(integrations.router)
# More specific /api/v1/webhooks routes must register before the generic
# CRUD router so they do not get shadowed by tenant/webhook path params.
app.include_router(webhook_deliveries.router)
app.include_router(webhooks.router)
app.include_router(sms.router)
app.include_router(team.router)
app.include_router(twilio_webhooks.router)
app.include_router(widget_chat.router)
app.include_router(widget_config.router)
app.include_router(widget_lead.router)
app.include_router(notifications.router)
app.include_router(business_page.router)
app.include_router(booking_page.router)
app.include_router(reviews.router)
app.include_router(content.router)
app.include_router(crawl.router)
app.include_router(menu.router)
app.include_router(orders.router)
app.include_router(jobs.router)
app.include_router(tag_definitions.router)
app.include_router(action_items.router)
app.include_router(conversation_inbox.router)
app.include_router(snippets.router)
app.include_router(chat_flows.router)
app.include_router(client_portal.router)
app.include_router(bids.router)
app.include_router(calls.router)
app.include_router(local_seo.router)
app.include_router(managed_agent_runs.router)
app.include_router(onboarding.router)
app.include_router(phone.router)
app.include_router(gbp.router)
app.include_router(csat.router)
app.include_router(custom_fields.router)
app.include_router(social_media.router)
app.include_router(marketing_campaigns.router)
app.include_router(marketing_analytics.router)
app.include_router(ab_tests.router)
app.include_router(automation_rules.router)
app.include_router(admin_analytics.router)
app.include_router(admin_promotions.router)
app.include_router(invoices.router)
app.include_router(documents.router)
app.include_router(pipeline.router)
app.include_router(revenue.router)
app.include_router(smart_lists.router)
app.include_router(forms.router)
app.include_router(channels_facebook.router)
app.include_router(pipeline_automations.router)
app.include_router(scoring_config.router)
app.include_router(waitlist.router)
app.include_router(wizard_analytics.router)
app.include_router(content_repurpose.router)
app.include_router(zapier.router)


# --- Static files (widget) ---
app.mount("/widget", StaticFiles(directory="widget"), name="widget")


# --- Health check ---
@app.api_route("/healthz", methods=["GET", "HEAD"])
@app.api_route("/api/healthz", methods=["GET", "HEAD"])
@app.api_route("/api/v1/healthz", methods=["GET", "HEAD"])
async def healthz():
    return {
        "status": "ok",
        "service": "agentnexlify",
        "uptime_seconds": _app_uptime_seconds(),
    }


@app.api_route("/readyz", methods=["GET", "HEAD"])
@app.api_route("/api/readyz", methods=["GET", "HEAD"])
@app.api_route("/api/v1/readyz", methods=["GET", "HEAD"])
async def readyz():
    snapshot = _readiness_snapshot()
    return JSONResponse(
        status_code=200 if snapshot["ready"] else 503,
        content={
            "status": "ready" if snapshot["ready"] else "not_ready",
            "service": "agentnexlify",
            "uptime_seconds": _app_uptime_seconds(),
            "checks": snapshot,
        },
    )


@app.api_route("/version", methods=["GET", "HEAD"])
@app.api_route("/api/version", methods=["GET", "HEAD"])
@app.api_route("/api/v1/version", methods=["GET", "HEAD"])
async def version():
    return {
        "service": "agentnexlify",
        "version": _app_version(),
        "commit": _build_sha(),
    }


@app.api_route("/health", methods=["GET", "HEAD"])
@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health():
    uptime = _app_uptime_seconds()

    # Supabase connectivity check
    supabase_status = "disconnected"
    try:
        from backend.models.database import get_service_supabase

        db = get_service_supabase()
        db.table("tenants").select("id").limit(1).execute()
        supabase_status = "connected"
    except Exception:
        logger.warning("Health check: supabase unreachable", exc_info=True)

    overall = "ok" if supabase_status == "connected" else "degraded"
    return {
        "status": overall,
        "service": "agentnexlify",
        "uptime_seconds": uptime,
        "checks": {
            "supabase": supabase_status,
        },
    }


# --- Global error handler ---
@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    from fastapi import HTTPException as _HTTPException

    # Let FastAPI handle HTTPExceptions natively (4xx, etc.)
    if isinstance(exc, _HTTPException):
        # Ensure CORS headers on HTTP error responses for widget endpoints
        if request.url.path.startswith("/api/v1/widget"):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=_CORS_HEADERS,
            )
        raise exc

    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
        headers=_CORS_HEADERS,
    )
