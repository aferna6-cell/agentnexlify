"""Tenant-scoped website / chatbot connect API.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI.
Never add 'from __future__ import annotations' to this file.
"""

import io
import logging
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import website_connect as connect_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/website-connect", tags=["website-connect"])

_PLUGIN_DIR = (
    Path(__file__).resolve().parents[2] / "wordpress-plugin" / "agentnexlify"
)


class ConnectWebsiteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    website_url: str = Field(..., max_length=500)
    platform: str | None = Field(None, max_length=32)

    @field_validator("website_url")
    @classmethod
    def url_required(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Website URL is required")
        return v.strip()

    @field_validator("platform")
    @classmethod
    def platform_allowed(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip().lower()
        if v not in connect_svc.PLATFORMS:
            raise ValueError("Unsupported platform")
        return v


def _reject_raw_secrets(payload: dict) -> None:
    try:
        connect_svc.reject_credential_fields(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def get_website_connection(claims: dict = Depends(_get_current_tenant)):
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    row = connect_svc.get_connection(db, tenant_id)
    return {"connection": row, "status": row["status"] if row else "not_started"}


@router.post("")
async def connect_website(
    request: Request,
    claims: dict = Depends(_get_current_tenant),
):
    raw = await request.json()
    if not isinstance(raw, dict):
        raise HTTPException(status_code=422, detail="Expected a JSON object")
    _reject_raw_secrets(raw)
    try:
        body = ConnectWebsiteRequest.model_validate(raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    try:
        return connect_svc.upsert_connection(
            db,
            tenant_id,
            body.website_url,
            platform=body.platform,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/verify")
def verify_website_connection(claims: dict = Depends(_get_current_tenant)):
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    try:
        return connect_svc.verify_connection(db, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/wordpress-plugin")
def download_wordpress_plugin(claims: dict = Depends(_get_current_tenant)):
    """Authenticated zip of the public WordPress plugin. No tenant secrets."""
    if not _PLUGIN_DIR.is_dir():
        raise HTTPException(status_code=404, detail="WordPress plugin is not packaged")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(_PLUGIN_DIR.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(f"agentnexlify/{path.relative_to(_PLUGIN_DIR)}")
                info.date_time = (2026, 1, 1, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, path.read_bytes())
    buf.seek(0)
    logger.info(
        "website_connect wordpress plugin downloaded tenant=%s",
        claims.get("tenant_id"),
    )
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=agentnexlify.zip",
        },
    )
