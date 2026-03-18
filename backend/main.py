"""AgentNexLiFy — FastAPI application entry point."""


import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pythonjsonlogger.jsonlogger import JsonFormatter
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.limiter import limiter
from backend.routers import action_items, analytics, appointments, auth, automations, bids, billing, booking_page, business_page, calls, channels_facebook, chat_flows, client_portal, clients, content, conversation_inbox, crawl, csat, custom_fields, email_templates, forms, gbp, integrations, invoices, jobs, leads, local_seo, marketing_campaigns, menu, notifications, onboarding, orders, phone, pipeline, reviews, sequences, smart_lists, sms, snippets, social_media, stripe_webhooks, support, tag_definitions, team, twilio_webhooks, webhooks, widget_chat, widget_config, widget_lead

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


async def _automation_loop():
    """Background loop that runs automation tasks on a tiered schedule.

    With multiple Uvicorn workers, each worker runs its own loop. We use a
    random jitter (0-30s) to spread execution across workers and rely on
    idempotent operations (dedup checks in each function) to prevent duplicates.

    Tiers:
      - Every 60s  (every tick): core sequences, no-response leads, reminders
      - Every 5min (tick % 5):   notifications, review requests, onboarding, CSAT
      - Every 30min (tick % 30): heavy/infrequent tasks (monthly reports, briefs)
    """
    import random
    await asyncio.sleep(random.uniform(0, 30))  # Stagger workers
    from backend.services.automation_engine import (
        check_new_reviews,
        check_no_response_leads,
        process_pending_steps,
        send_appointment_reminders,
        send_csat_surveys,
        send_invoice_payment_reminders,
        send_monthly_reports,
        send_pending_review_requests,
        send_onboarding_emails,
        send_portal_links,
        send_weekly_intelligence_briefs,
    )

    tick = 0
    while True:
        tick += 1

        # Every 60s: core automation tasks run in parallel
        core_tasks = [
            _safe_run("process_pending_steps", process_pending_steps),
            _safe_run("check_no_response_leads", check_no_response_leads),
            _safe_run("send_appointment_reminders", send_appointment_reminders),
        ]

        # Every 5 min: notification/reminder functions
        if tick % 5 == 0:
            core_tasks.extend([
                _safe_run("send_pending_review_requests", send_pending_review_requests),
                _safe_run("send_onboarding_emails", send_onboarding_emails),
                _safe_run("send_portal_links", send_portal_links),
                _safe_run("send_csat_surveys", send_csat_surveys),
                _safe_run("check_new_reviews", check_new_reviews),
                _safe_run("send_invoice_payment_reminders", send_invoice_payment_reminders),
            ])

        # Every 30 min: heavy/infrequent tasks
        if tick % 30 == 0:
            core_tasks.extend([
                _safe_run("send_monthly_reports", send_monthly_reports),
                _safe_run("send_weekly_intelligence_briefs", send_weekly_intelligence_briefs),
            ])

        # Stalled campaign recovery: find campaigns stuck in 'sending' for >30 min
        if tick % 5 == 0:
            core_tasks.append(_safe_run("recover_stalled_campaigns", _recover_stalled_campaigns))

        await asyncio.gather(*core_tasks)
        await asyncio.sleep(60)


async def _recover_stalled_campaigns():
    """Mark marketing campaigns stuck in 'sending' for >30 minutes as 'failed'."""
    from datetime import datetime, timedelta, timezone
    from backend.models.database import get_supabase

    db = get_supabase()
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    try:
        stalled = (
            db.table("marketing_campaigns")
            .select("id, name, tenant_id")
            .eq("status", "sending")
            .lt("updated_at", stale_cutoff)
            .limit(50)
            .execute()
        )
        if not stalled.data:
            return 0
        stalled_ids = [r["id"] for r in stalled.data]
        for campaign_id in stalled_ids:
            db.table("marketing_campaigns").update({"status": "failed"}).eq("id", campaign_id).execute()
            logger.warning("Marked stalled campaign %s as failed", campaign_id)
        return len(stalled_ids)
    except Exception:
        logger.exception("_recover_stalled_campaigns failed")
        return 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _startup_time
    _startup_time = time.time()
    logger.info("AgentNexLiFy starting up")
    if not os.environ.get("TESTING"):
        task = asyncio.create_task(_automation_loop())
    yield
    if not os.environ.get("TESTING"):
        task.cancel()
    logger.info("AgentNexLiFy shutting down")


app = FastAPI(
    title="AgentNexLiFy",
    description="AI-powered lead capture and qualification chatbot for real estate agents",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS ---
# Widget is embedded on customer websites (arbitrary origins), so we MUST
# allow all origins.  Per-widget domain restrictions are enforced at the
# application level in widget_helpers.py:_check_origin().
#
# Note: allow_credentials cannot be True when allow_origins is ["*"], so
# we disable it.  The widget uses API-key auth, not cookies.
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
    # Try to log the raw body for widget endpoints
    if request.url.path.startswith("/api/v1/widget"):
        try:
            body = await request.body()
            logger.error("Request body was: %s", body[:2000])
        except Exception as e:
            logger.warning("Could not read request body for debugging: %s", e)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
        headers=_CORS_HEADERS,
    )


app.add_exception_handler(RequestValidationError, _validation_exception_handler)


# --- Request logging middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Extract tenant_id from JWT if present (decode-only, no auth enforcement)
    tenant_id: str | None = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from jose import jwt

            payload = jwt.get_unverified_claims(auth_header[7:])
            tenant_id = payload.get("tenant_id")
        except Exception as e:
            logger.debug("JWT decode for logging failed: %s", e)

    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    response.headers["X-Request-ID"] = request_id

    log_data = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration_ms, 1),
        "request_id": request_id,
        "tenant_id": tenant_id,
    }

    if response.status_code >= 500:
        logger.error("request completed", extra=log_data)
    else:
        logger.info("request completed", extra=log_data)

    return response


# --- Routers ---
app.include_router(analytics.router)
app.include_router(appointments.router)
app.include_router(auth.router)
app.include_router(automations.router)
app.include_router(billing.router)
app.include_router(clients.router)
app.include_router(email_templates.router)
app.include_router(leads.router)
app.include_router(stripe_webhooks.router)
app.include_router(sequences.router)
app.include_router(sequences.leads_router)
app.include_router(support.router)
app.include_router(integrations.router)
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
app.include_router(onboarding.router)
app.include_router(phone.router)
app.include_router(gbp.router)
app.include_router(csat.router)
app.include_router(custom_fields.router)
app.include_router(social_media.router)
app.include_router(marketing_campaigns.router)
app.include_router(invoices.router)
app.include_router(pipeline.router)
app.include_router(smart_lists.router)
app.include_router(forms.router)
app.include_router(channels_facebook.router)


# --- Static files (widget) ---
app.mount("/widget", StaticFiles(directory="widget"), name="widget")


# --- Health check ---
@app.get("/health")
@app.get("/api/health")
async def health():
    uptime = round(time.time() - _startup_time, 1) if _startup_time else 0.0

    # Supabase connectivity check
    supabase_status = "disconnected"
    try:
        from backend.models.database import get_supabase

        db = get_supabase()
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
            "anthropic_api_key": bool(settings.anthropic_api_key),
            "stripe_configured": bool(settings.stripe_secret_key),
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
