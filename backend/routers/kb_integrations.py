"""Google Drive KB integration endpoints (specs/drive-kb-onboarding_spec.md).

OAuth connect flow mirrors backend/routers/integrations.py (calendar): the
SPA fetches an auth URL carrying a signed-state JWT, Google redirects back to
a public callback, tokens land vault-encrypted on tenant_integrations. Then:
folder list/pick, status, manual sync-now, sync log, disconnect.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel

from backend.config import settings
from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.drive_kb_sync import (
    DriveNotConfigured,
    EncryptionRequired,
    build_auth_url,
    disconnect,
    drive_oauth_ready,
    exchange_code,
    get_integration,
    list_folders,
    save_tokens,
    set_folder,
    sync_tenant_drive,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kb/integrations/drive", tags=["tenant-kb"])

_JWT_ALGORITHM = "HS256"


def _jwt_secret() -> str:
    return settings.api_secret_key


def _encode_state(tenant_id: str) -> str:
    payload = {
        "tenant_id": tenant_id,
        "purpose": "drive_kb_oauth",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)


def _decode_state(state: str) -> str:
    try:
        payload = jwt.decode(state, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
        if payload.get("purpose") != "drive_kb_oauth" or not payload.get("tenant_id"):
            raise HTTPException(status_code=400, detail="Invalid state")
        return payload["tenant_id"]
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired state") from exc


class FolderChoice(BaseModel):
    folder_id: str
    folder_name: str


@router.get("/auth")
async def drive_auth(claims: dict = Depends(_get_current_tenant)):
    """Return the Google consent URL for the Drive KB connection."""
    tenant_id = claims["tenant_id"]
    try:
        return {"auth_url": build_auth_url(_encode_state(tenant_id))}
    except DriveNotConfigured:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "drive_kb_not_configured",
                "message": "Google Drive sync isn't set up on this platform yet.",
            },
        )
    except EncryptionRequired:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "encryption_key_required",
                "message": "Token encryption isn't provisioned yet. Set INTEGRATIONS_ENC_KEY first.",
            },
        )


@router.get("/callback")
async def drive_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """Public OAuth callback — the browser arrives via Google's redirect."""
    tenant_id = _decode_state(state)
    try:
        tokens = exchange_code(code)
        save_tokens(tenant_id, tokens)
    except EncryptionRequired:
        raise HTTPException(status_code=503, detail="Encryption key not provisioned")
    except Exception:
        logger.exception("Drive OAuth exchange failed for tenant %s", tenant_id)
        raise HTTPException(status_code=400, detail="Failed to complete Drive authorization")

    if settings.frontend_url:
        return RedirectResponse(url=f"{settings.frontend_url}/dashboard/knowledge?drive=connected")
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;text-align:center;padding:4rem'>"
        "<h2>Connected!</h2><p>Google Drive is linked. You can close this window.</p>"
        "</body></html>"
    )


@router.get("/status")
async def drive_status(claims: dict = Depends(_get_current_tenant)):
    """Connection + folder + last-sync state for the dashboard card."""
    tenant_id = claims["tenant_id"]
    integration = get_integration(tenant_id)
    if not integration:
        return {"connected": False, "configured": drive_oauth_ready()}
    config = integration.get("config") or {}
    return {
        "connected": True,
        "configured": drive_oauth_ready(),
        "enabled": bool(integration.get("enabled")),
        "folder_id": config.get("folder_id"),
        "folder_name": config.get("folder_name"),
        "last_synced_at": integration.get("last_synced_at"),
        "last_sync_status": integration.get("last_sync_status"),
    }


@router.get("/folders")
async def drive_folders(claims: dict = Depends(_get_current_tenant)):
    """Folders the tenant can choose as the KB source."""
    tenant_id = claims["tenant_id"]
    try:
        return {"folders": await run_in_threadpool(list_folders, tenant_id)}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        logger.exception("Drive folder listing failed for tenant %s", tenant_id)
        raise HTTPException(status_code=502, detail="Failed to list Drive folders")


@router.post("/folder")
async def drive_set_folder(
    choice: FolderChoice,
    claims: dict = Depends(_get_current_tenant),
):
    """Pick the synced folder, then run the first sync immediately."""
    tenant_id = claims["tenant_id"]
    try:
        set_folder(tenant_id, choice.folder_id, choice.folder_name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    # Threadpool: first sync of a large folder makes per-file httpx fetches
    # (up to 60s timeouts each) — must not sit on the event loop (audit H1).
    summary = await run_in_threadpool(sync_tenant_drive, tenant_id)
    return {"folder_set": True, "sync": summary}


@router.post("/sync-now")
async def drive_sync_now(claims: dict = Depends(_get_current_tenant)):
    """Manual sync trigger (spec: dashboard 'sync now' button)."""
    tenant_id = claims["tenant_id"]
    summary = await run_in_threadpool(sync_tenant_drive, tenant_id)
    if summary.get("error") in ("drive not connected or disabled", "no folder selected"):
        raise HTTPException(status_code=409, detail=summary["error"])
    return {"sync": summary}


@router.get("/sync-log")
async def drive_sync_log(claims: dict = Depends(_get_current_tenant)):
    """Recent sync history (tenant sees only their own rows)."""
    tenant_id = claims["tenant_id"]
    db = get_service_supabase()
    result = (
        db.table("integration_sync_log")
        .select("synced_at, files_added, files_updated, files_skipped, files_pii_flagged, error")
        .eq("client_id", tenant_id)
        .order("synced_at", desc=True)
        .limit(20)
        .execute()
    )
    return {"log": result.data or []}


@router.delete("/")
async def drive_disconnect(claims: dict = Depends(_get_current_tenant)):
    """Remove the Drive connection (synced documents stay until deleted)."""
    tenant_id = claims["tenant_id"]
    removed = disconnect(tenant_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Drive is not connected")
    return {"disconnected": True}
