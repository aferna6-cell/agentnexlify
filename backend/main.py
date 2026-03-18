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
from backend.routers import action_items, analytics, appointments, auth, automations, bids, billing, business_page, calls, chat_flows, client_portal, clients, content, conversation_inbox, crawl, csat, custom_fields, email_templates, gbp, integrations, invoices, jobs, leads, local_seo, marketing_campaigns, menu, notifications, onboarding, orders, phone, pipeline, reviews, sequences, sms, snippets, social_media, stripe_webhooks, support, tag_definitions, team, twilio_webhooks, webhooks, widget

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


async def _automation_loop():
    """Background loop that processes pending automation steps every 60 seconds.

    With multiple Uvicorn workers, each worker runs its own loop. We use a
    random jitter (0-30s) to spread execution across workers and rely on
    idempotent operations (dedup checks in each function) to prevent duplicates.
    """
    import random
    await asyncio.sleep(random.uniform(0, 30))  # Stagger workers
    from backend.services.automation_engine import check_new_reviews, check_no_response_leads, process_pending_steps, send_appointment_reminders, send_csat_surveys, send_invoice_payment_reminders, send_monthly_reports, send_pending_review_requests, send_onboarding_emails, send_portal_links, send_weekly_intelligence_briefs
    while True:
        try:
            processed = await process_pending_steps()
            if processed:
                logger.info("Automation loop: processed %d steps", processed)
        except Exception:
            logger.exception("Automation loop: process_pending_steps failed")

        try:
            triggered = await check_no_response_leads()
            if triggered:
                logger.info("Automation loop: triggered %d no-response sequences", triggered)
        except Exception:
            logger.exception("Automation loop: check_no_response_leads failed")

        try:
            reminders = await send_appointment_reminders()
            if reminders:
                logger.info("Automation loop: sent %d appointment reminders", reminders)
        except Exception:
            logger.exception("Automation loop: send_appointment_reminders failed")

        try:
            review_reqs = await send_pending_review_requests()
            if review_reqs:
                logger.info("Automation loop: sent %d review requests", review_reqs)
        except Exception:
            logger.exception("Automation loop: send_pending_review_requests failed")

        try:
            onboarding = await send_onboarding_emails()
            if onboarding:
                logger.info("Automation loop: sent %d onboarding emails", onboarding)
        except Exception:
            logger.exception("Automation loop: send_onboarding_emails failed")

        try:
            portal = await send_portal_links()
            if portal:
                logger.info("Automation loop: sent %d portal links", portal)
        except Exception:
            logger.exception("Automation loop: send_portal_links failed")

        try:
            reports = await send_monthly_reports()
            if reports:
                logger.info("Automation loop: sent %d monthly reports", reports)
        except Exception:
            logger.exception("Automation loop: send_monthly_reports failed")

        try:
            review_alerts = await check_new_reviews()
            if review_alerts:
                logger.info("Automation loop: sent %d review alert notifications", review_alerts)
        except Exception:
            logger.exception("Automation loop: check_new_reviews failed")

        try:
            csat_sent = await send_csat_surveys()
            if csat_sent:
                logger.info("Automation loop: sent %d CSAT surveys", csat_sent)
        except Exception:
            logger.exception("Automation loop: send_csat_surveys failed")

        try:
            inv_reminders = await send_invoice_payment_reminders()
            if inv_reminders:
                logger.info("Automation loop: sent %d invoice payment reminders", inv_reminders)
        except Exception:
            logger.exception("Automation loop: send_invoice_payment_reminders failed")

        try:
            briefs = await send_weekly_intelligence_briefs()
            if briefs:
                logger.info("Automation loop: sent %d weekly intelligence briefs", briefs)
        except Exception:
            logger.exception("Automation loop: send_weekly_intelligence_briefs failed")

        await asyncio.sleep(60)


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
# application level in widget.py:_check_origin().
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
app.include_router(widget.router)
app.include_router(notifications.router)
app.include_router(business_page.router)
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
