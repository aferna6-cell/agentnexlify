"""Widget config endpoints: GET config, online-status toggle, file upload,
AI feedback, email tracking pixel, and unsubscribe.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
It breaks FastAPI's parameter introspection — Pydantic body models and
BackgroundTasks get treated as query params, causing 422 errors.
"""

import hmac
import logging
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.models.schemas import OnlineStatusRequest, WidgetConfigResponse
from backend.services.email_sender import _make_unsub_sig
from backend.routers.widget_chat_helpers import (
    _check_origin,
    _get_tenant,
    _get_widget_config,
)
from backend.services.branding_helpers import _filter_branding_for_plan
from backend.dependencies import _get_current_tenant as _auth_get_tenant

from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/widget", tags=["widget"])

# ---------------------------------------------------------------------------
# File upload config
# ---------------------------------------------------------------------------

_MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
_ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,200}$")


def _content_matches_type(content_type: str, data: bytes) -> bool:
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/gif":
        return data.startswith((b"GIF87a", b"GIF89a"))
    if content_type == "image/webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if content_type == "application/pdf":
        return data.startswith(b"%PDF-")
    if content_type == "application/msword":
        return data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return data.startswith(b"PK\x03\x04")
    return False

# ---------------------------------------------------------------------------
# Email tracking pixel
# ---------------------------------------------------------------------------

# 1x1 transparent GIF
_TRACKING_PIXEL = bytes([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00,
    0x80, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x21,
    0xF9, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0x2C, 0x00, 0x00,
    0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
    0x01, 0x00, 0x3B,
])


# ---------------------------------------------------------------------------
# JWT helper (dashboard-only endpoints)
# ---------------------------------------------------------------------------


def _get_jwt_claims(authorization: str = Header(...)) -> dict:
    """Extract and verify JWT claims. Returns claims dict."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    from jose import JWTError, jwt as jose_jwt
    jwt_secret = getattr(settings, "jwt_secret_key", "")
    if not (isinstance(jwt_secret, str) and jwt_secret):
        api_secret = getattr(settings, "api_secret_key", "")
        jwt_secret = api_secret if isinstance(api_secret, str) else ""
    try:
        return jose_jwt.decode(
            authorization.removeprefix("Bearer ").strip(),
            jwt_secret,
            algorithms=["HS256"],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ---------------------------------------------------------------------------
# AI Feedback model (defined here since it's only used in config/feedback endpoints)
# ---------------------------------------------------------------------------


class AIFeedbackRequest(BaseModel):
    api_key: str = Field(..., max_length=100)
    session_id: str = Field(..., max_length=200)
    message_index: int = Field(..., ge=0)
    rating: str = Field(..., max_length=20)  # "thumbs_up" or "thumbs_down"
    correction: str | None = Field(None, max_length=2000)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/config/{api_key}", response_model=WidgetConfigResponse)
@limiter.limit("120/minute")
async def get_config(request: Request, api_key: str):
    """Return widget configuration for the embedded chat widget."""
    widget = _get_widget_config(api_key)
    tenant = _get_tenant(widget["tenant_id"])

    # Force watermark for free plan (treat NULL plan as free)
    tenant_plan = tenant.get("plan") or "free"
    if tenant_plan == "free":
        show_watermark = True
    else:
        show_watermark = widget.get("show_watermark", True)

    # Branding: filter by plan
    plan = tenant_plan
    raw_branding = widget.get("branding") or {}
    branding = _filter_branding_for_plan(raw_branding, plan)
    # Free/growth: enforce powered-by defaults
    if plan in ("free", "growth") and not branding.get("powered_by_text"):
        branding.pop("powered_by_text", None)
        branding.pop("powered_by_url", None)

    # Load menu items for restaurant tenants
    menu_items = None
    if (tenant.get("business_type") or "").lower() == "restaurant":
        try:
            db = get_service_supabase()
            menu_result = (
                db.table("menu_items")
                .select("name, description, price, category, available")
                .eq("tenant_id", tenant["id"])
                .eq("available", True)
                .order("category")
                .order("sort_order")
                .execute()
            )
            if menu_result.data:
                menu_items = menu_result.data
        except Exception:
            logger.warning("menu_items config load failed for tenant %s", tenant["id"])

    return WidgetConfigResponse(
        bot_name=widget.get("bot_name", "AI Assistant"),
        primary_color=widget.get("primary_color", "#00BFFF"),
        greeting_message=widget.get("greeting_message"),
        position=widget.get("position", "bottom-right"),
        show_watermark=show_watermark,
        allowed_domains=widget.get("allowed_domains"),
        tenant_id=widget.get("tenant_id"),
        booking_enabled=widget.get("booking_enabled", False),
        branding=branding if branding else None,
        agent_name=tenant.get("business_name"),
        is_online=widget.get("is_online", True),
        offline_message=widget.get("offline_message"),
        menu_items=menu_items,
        business_type=tenant.get("business_type"),
        teaser_message=widget.get("teaser_message"),
        teaser_delay_seconds=widget.get("teaser_delay_seconds") or 3,
        teaser_enabled=widget.get("teaser_enabled", True),
        plan=tenant_plan,
        pre_chat_form=widget.get("pre_chat_form"),
    )


@router.put("/config/{tenant_id}/online-status")
async def toggle_online_status(
    tenant_id: str,
    body: OnlineStatusRequest,
    claims: dict = Depends(_get_jwt_claims),
):
    """Toggle widget online/offline status. Dashboard-only (JWT required)."""
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        db = get_service_supabase()
        result = (
            db.table("widget_configs")
            .update({"is_online": body.is_online})
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Widget config not found")
        logger.info(
            "toggle_online_status: tenant=%s is_online=%s",
            tenant_id, body.is_online,
        )
        return {"is_online": body.is_online}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "toggle_online_status FAILED: tenant=%s error=%s",
            tenant_id, e, exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to update online status")


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    api_key_form: str | None = Form(None, alias="api_key"),
    session_id_form: str | None = Form(None, alias="session_id"),
    api_key_query: str | None = Query(None, alias="api_key"),
    session_id_query: str | None = Query(None, alias="session_id"),
):
    """Upload a file from the chat widget. Returns a public URL.

    Files are stored in Supabase Storage under chat-attachments/{tenant_id}/{session_id}/.
    Max 5 MB. Allowed: images, PDF, Word docs.
    """
    api_key = api_key_form or api_key_query
    session_id = session_id_form or session_id_query
    if not api_key:
        raise HTTPException(status_code=422, detail="api_key is required")
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id is required")

    # Validate API key
    db = get_service_supabase()
    wc = (
        db.table("widget_configs")
        .select("tenant_id, allowed_domains")
        .eq("api_key", api_key)
        .limit(1)
        .execute()
    )
    if not wc.data:
        raise HTTPException(status_code=404, detail="Widget not found")
    widget = wc.data[0]
    _check_origin(request, widget.get("allowed_domains"), require_origin=True)
    tenant_id = widget["tenant_id"]

    if not _SESSION_ID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="Invalid session id")

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {content_type}")

    # Read file with size check
    data = await file.read(_MAX_UPLOAD_SIZE + 1)
    if len(data) > _MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")
    if not _content_matches_type(content_type, data):
        raise HTTPException(status_code=400, detail="File content does not match declared type")

    # Generate unique path
    ext = _CONTENT_TYPE_EXTENSIONS[content_type]
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"
    path = f"{tenant_id}/{session_id}/{unique_name}"

    try:
        db.storage.from_("chat-attachments").upload(
            path,
            data,
            file_options={"content-type": content_type},
        )
    except Exception:
        logger.exception("File upload failed for tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Upload failed")

    # Build public URL
    public_url = f"{settings.supabase_url}/storage/v1/object/public/chat-attachments/{path}"

    return {"url": public_url, "filename": file.filename, "content_type": content_type}


@router.get("/unsubscribe", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def unsubscribe_lead(
    request: Request,
    lid: str = Query(..., description="Lead ID", max_length=50),
    sig: str = Query(..., description="Signature", max_length=200),
    tid: str = Query("", description="Tenant ID", max_length=50),
):
    """Public endpoint clicked from email unsubscribe links."""
    db = get_service_supabase()
    result = (
        db.table("leads")
        .select("id, client_id, unsubscribed")
        .eq("id", lid)
        .limit(1)
        .execute()
    )
    if not result.data:
        return HTMLResponse(
            "<html><body><h2>Lead not found.</h2></body></html>",
            status_code=404,
        )

    lead = result.data[0]
    lead_tenant_id = str(lead.get("client_id") or "")

    expected_bound = _make_unsub_sig(lid, lead_tenant_id) if lead_tenant_id else ""
    tid_matches = (not tid) or (tid == lead_tenant_id)
    valid_bound = (
        bool(expected_bound)
        and tid_matches
        and hmac.compare_digest(sig, expected_bound)
    )

    allow_legacy = getattr(settings, "allow_legacy_unsubscribe_signatures", False)
    if isinstance(allow_legacy, str):
        allow_legacy = allow_legacy.strip().lower() in {"1", "true", "yes", "on"}
    elif not isinstance(allow_legacy, bool):
        allow_legacy = False

    valid_legacy = (
        allow_legacy
        and not tid
        and hmac.compare_digest(sig, _make_unsub_sig(lid, ""))
    )

    if not (valid_bound or valid_legacy):
        return HTMLResponse(
            "<html><body><h2>Invalid unsubscribe link.</h2></body></html>",
            status_code=400,
        )

    if not lead.get("unsubscribed"):
        db.table("leads").update({
            "unsubscribed": True,
            "unsubscribed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", lid).execute()

    return HTMLResponse(
        "<html><body style='font-family:Arial,sans-serif;text-align:center;padding:60px;'>"
        "<h2>You've been unsubscribed.</h2>"
        "<p>You will no longer receive automated messages from this business.</p>"
        "</body></html>"
    )


@router.get("/track/open")
@limiter.limit("300/minute")
async def track_email_open(
    request: Request,
    tid: str = Query(..., description="Tenant ID", max_length=50),
    lid: str = Query("", description="Lead ID", max_length=50),
    eid: str = Query("", description="Execution ID", max_length=50),
):
    """Log an email open event and return a 1x1 tracking pixel."""
    try:
        db = get_service_supabase()
        db.table("email_events").insert({
            "tenant_id": tid,
            "lead_id": lid or None,
            "event_type": "open",
            "execution_id": eid or None,
        }).execute()
    except Exception:
        logger.debug("Email open tracking insert failed", exc_info=True)
    from starlette.responses import Response
    return Response(content=_TRACKING_PIXEL, media_type="image/gif")


@router.post("/feedback")
@limiter.limit("30/minute")
async def submit_ai_feedback(request: Request, req: AIFeedbackRequest):
    """Submit thumbs up/down feedback on an AI response from the widget."""
    if req.rating not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(status_code=400, detail="Rating must be thumbs_up or thumbs_down")

    widget = _get_widget_config(req.api_key)
    tenant_id = widget["tenant_id"]

    db = get_service_supabase()
    db.table("ai_feedback").insert({
        "tenant_id": tenant_id,
        "session_id": req.session_id,
        "message_index": req.message_index,
        "rating": req.rating,
        "correction": req.correction if req.correction and req.correction.strip() else None,
    }).execute()

    return {"status": "ok"}


@router.get("/feedback/{tenant_id}")
async def get_ai_feedback(
    tenant_id: str,
    claims: dict = Depends(_auth_get_tenant),
):
    """Get AI feedback for a tenant (dashboard use)."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    result = (
        db.table("ai_feedback")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"feedback": result.data or []}


@router.delete("/feedback/{tenant_id}/{feedback_id}")
async def delete_ai_feedback(
    tenant_id: str,
    feedback_id: str,
    claims: dict = Depends(_auth_get_tenant),
):
    """Delete a feedback entry."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db = get_service_supabase()
    db.table("ai_feedback").delete().eq("id", feedback_id).eq("tenant_id", tenant_id).execute()
    return {"status": "deleted"}


# ── QR Code Generation ──────────────────────────────────────


@router.get("/{tenant_id}/qr")
async def generate_qr_code(
    tenant_id: str,
    url: str = Query(..., min_length=5, max_length=2000, description="URL to encode in the QR code"),
    size: int = Query(300, ge=100, le=1000, description="QR code image size in pixels"),
    claims: dict = Depends(_auth_get_tenant),
):
    """Generate a QR code PNG for a given URL (widget link, review link, etc.)."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    import io
    import qrcode
    from fastapi.responses import StreamingResponse

    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Resize to requested size
    img = img.resize((size, size))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png", headers={
        "Content-Disposition": f"inline; filename=qr-code-{size}.png",
        "Cache-Control": "public, max-age=3600",
    })
