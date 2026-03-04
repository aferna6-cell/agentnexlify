"""AgentNexLiFy — FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pythonjsonlogger.jsonlogger import JsonFormatter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.limiter import limiter
from backend.routers import appointments, auth, automations, billing, clients, leads, sequences, stripe_webhooks, support, widget

# --- JSON logging ---
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.root.handlers = [_handler]
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

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
    """Background loop that processes pending automation steps every 60 seconds."""
    from backend.services.automation_engine import check_no_response_leads, process_pending_steps
    while True:
        try:
            processed = await process_pending_steps()
            if processed:
                logger.info("Automation loop: processed %d steps", processed)
            # Also check for no-response leads
            triggered = await check_no_response_leads()
            if triggered:
                logger.info("Automation loop: triggered %d no-response sequences", triggered)
        except Exception:
            logger.exception("Automation loop error")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _startup_time
    _startup_time = time.time()
    logger.info("AgentNexLiFy starting up")
    task = asyncio.create_task(_automation_loop())
    yield
    task.cancel()
    logger.info("AgentNexLiFy shutting down")


app = FastAPI(
    title="AgentNexLiFy",
    description="AI-powered lead capture and qualification chatbot for real estate agents",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS ---
# Widget is embedded on customer websites (arbitrary origins), so we must
# allow all origins.  Per-widget domain restrictions are enforced at the
# application level in widget.py:_check_origin().
#
# Note: allow_credentials cannot be True when allow_origins is ["*"], so
# we disable it.  The widget uses API-key auth, not cookies.
_cors_origins: list[str] = ["*"]
if settings.widget_allowed_origins and settings.widget_allowed_origins != "*":
    _cors_origins = [o.strip() for o in settings.widget_allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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
        except Exception:
            pass

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
app.include_router(appointments.router)
app.include_router(auth.router)
app.include_router(automations.router)
app.include_router(billing.router)
app.include_router(clients.router)
app.include_router(leads.router)
app.include_router(stripe_webhooks.router)
app.include_router(sequences.router)
app.include_router(sequences.leads_router)
app.include_router(support.router)
app.include_router(widget.router)


# --- Static files (widget) ---
app.mount("/widget", StaticFiles(directory="widget"), name="widget")


# --- Health check ---
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

    return {
        "status": "ok",
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
        raise exc

    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )
