"""Google Drive → tenant KB sync (specs/drive-kb-onboarding_spec.md).

Tenant OAuths once (drive.readonly), picks a folder, and the platform pulls
changed documents on a daily cadence + manual sync-now. Files flow through
the same ingest spine as dashboard uploads (backend/services/tenant_kb.py),
so provenance, PII flags, sha-diff skip, and compile behavior are identical
across transports.

Uses the Drive REST API directly over httpx — no googleapiclient dependency.
OAuth tokens are encrypted with the Fernet vault (GH #131/#266); if
INTEGRATIONS_ENC_KEY is not provisioned, connecting Drive is REFUSED rather
than storing refresh tokens plaintext (EncryptionRequired -> HTTP 503).

client_id (NOT tenant_id) on tenant_integrations / integration_sync_log.
Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.integration_key_vault import (
    _from_bytea,
    _to_bytea,
    decrypt_key,
    encrypt_key,
    encryption_configured,
)
from backend.services.tenant_kb import compile_tenant_kb, ingest_file

logger = logging.getLogger(__name__)

PROVIDER = "drive"
OAUTH_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_DRIVE_API = "https://www.googleapis.com/drive/v3"

# Google-native docs export as text; binary formats download and go through
# the shared extractor. Everything else is skipped with a logged reason.
_EXPORT_MIMES = {"application/vnd.google-apps.document": "text/plain"}
_DOWNLOAD_MIMES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".md",
}

# Daily cadence: the 30-min automation loop calls run_drive_kb_sync_due();
# an integration is due when it has never synced or synced >22h ago —
# self-gating, no clock-edge logic required.
_SYNC_DUE_HOURS = 22


class EncryptionRequired(Exception):
    """Raised when INTEGRATIONS_ENC_KEY is unset — never store tokens plaintext."""


class DriveNotConfigured(Exception):
    """Raised when the platform Google OAuth app is not configured."""


def _drive_redirect_uri() -> str:
    return getattr(settings, "google_drive_redirect_uri", "") or ""


def drive_oauth_ready() -> bool:
    return bool(
        settings.google_client_id
        and settings.google_client_secret
        and _drive_redirect_uri()
    )


def build_auth_url(state: str) -> str:
    if not drive_oauth_ready():
        raise DriveNotConfigured("Google Drive OAuth is not configured on this platform")
    if not encryption_configured():
        raise EncryptionRequired("INTEGRATIONS_ENC_KEY must be set before connecting Drive")
    params = httpx.QueryParams(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": _drive_redirect_uri(),
            "response_type": "code",
            "scope": OAUTH_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return f"{_AUTH_URL}?{params}"


def exchange_code(code: str) -> dict:
    """Authorization code -> {access_token, refresh_token, expires_in}."""
    resp = httpx.post(
        _TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": _drive_redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=20.0,
    )
    resp.raise_for_status()
    return resp.json()


def _refresh_access_token(refresh_token: str) -> dict:
    resp = httpx.post(
        _TOKEN_URL,
        data={
            "refresh_token": refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        },
        timeout=20.0,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Integration row helpers
# ---------------------------------------------------------------------------


def get_integration(client_id: str) -> dict | None:
    db = get_service_supabase()
    result = (
        db.table("tenant_integrations")
        .select("*")
        .eq("client_id", client_id)
        .eq("provider", PROVIDER)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def save_tokens(client_id: str, tokens: dict) -> None:
    """Upsert the Drive integration row with vault-encrypted tokens."""
    if not encryption_configured():
        raise EncryptionRequired("INTEGRATIONS_ENC_KEY must be set before connecting Drive")
    db = get_service_supabase()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in") or 3600))
    ).isoformat()
    payload: dict = {
        "oauth_token_enc": _to_bytea(encrypt_key(tokens["access_token"])),
        "oauth_expires_at": expires_at,
        "enabled": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if tokens.get("refresh_token"):
        payload["oauth_refresh_token_enc"] = _to_bytea(encrypt_key(tokens["refresh_token"]))

    existing = get_integration(client_id)
    if existing:
        db.table("tenant_integrations").update(payload).eq("id", existing["id"]).execute()
    else:
        db.table("tenant_integrations").insert(
            {"client_id": client_id, "provider": PROVIDER, **payload}
        ).execute()


def set_folder(client_id: str, folder_id: str, folder_name: str) -> None:
    db = get_service_supabase()
    integration = get_integration(client_id)
    if not integration:
        raise ValueError("Drive is not connected for this tenant")
    config = dict(integration.get("config") or {})
    config.update({"folder_id": folder_id, "folder_name": folder_name})
    db.table("tenant_integrations").update(
        {"config": config, "updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", integration["id"]).execute()


def disconnect(client_id: str) -> bool:
    db = get_service_supabase()
    result = (
        db.table("tenant_integrations")
        .delete()
        .eq("client_id", client_id)
        .eq("provider", PROVIDER)
        .execute()
    )
    return bool(result.data)


def _access_token(integration: dict) -> str:
    """Current access token, refreshing through Google when expired."""
    expires_at = integration.get("oauth_expires_at") or ""
    now_iso = datetime.now(timezone.utc).isoformat()
    enc = _from_bytea(integration.get("oauth_token_enc"))
    if enc is not None and expires_at > now_iso:
        return decrypt_key(enc)

    refresh_enc = _from_bytea(integration.get("oauth_refresh_token_enc"))
    if refresh_enc is None:
        raise ValueError("No refresh token stored — reconnect Drive")
    refreshed = _refresh_access_token(decrypt_key(refresh_enc))
    save_tokens(integration["client_id"], refreshed)
    return refreshed["access_token"]


# ---------------------------------------------------------------------------
# Drive API
# ---------------------------------------------------------------------------


def list_folders(client_id: str) -> list[dict]:
    """Folders the tenant can pick from (name-sorted, first 50)."""
    integration = get_integration(client_id)
    if not integration:
        raise ValueError("Drive is not connected for this tenant")
    token = _access_token(integration)
    resp = httpx.get(
        f"{_DRIVE_API}/files",
        params={
            "q": "mimeType='application/vnd.google-apps.folder' and trashed=false",
            "fields": "files(id,name)",
            "pageSize": 50,
            "orderBy": "name",
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=20.0,
    )
    resp.raise_for_status()
    return resp.json().get("files", [])


def _list_folder_files(token: str, folder_id: str) -> list[dict]:
    resp = httpx.get(
        f"{_DRIVE_API}/files",
        params={
            "q": f"'{folder_id}' in parents and trashed=false",
            "fields": "files(id,name,mimeType,modifiedTime,size)",
            "pageSize": 200,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json().get("files", [])


def _fetch_file(token: str, file: dict) -> tuple[str, bytes] | None:
    """Download or export one Drive file. Returns (filename, bytes) or None."""
    mime = file.get("mimeType") or ""
    file_id = file["id"]
    name = file.get("name") or file_id
    headers = {"Authorization": f"Bearer {token}"}

    if mime in _EXPORT_MIMES:
        resp = httpx.get(
            f"{_DRIVE_API}/files/{file_id}/export",
            params={"mimeType": _EXPORT_MIMES[mime]},
            headers=headers,
            timeout=30.0,
        )
        resp.raise_for_status()
        if not name.lower().endswith((".txt", ".md")):
            name = f"{name}.txt"
        return name, resp.content

    if mime in _DOWNLOAD_MIMES:
        resp = httpx.get(
            f"{_DRIVE_API}/files/{file_id}",
            params={"alt": "media"},
            headers=headers,
            timeout=60.0,
        )
        resp.raise_for_status()
        ext = _DOWNLOAD_MIMES[mime]
        if not name.lower().endswith(ext):
            name = f"{name}{ext}"
        return name, resp.content

    return None  # unsupported mime — caller logs a skip


def sync_tenant_drive(client_id: str) -> dict:
    """One full sync pass for one tenant. Never raises — logs + records.

    Lists the picked folder, pulls files modified since last_synced_at (all
    files on first sync), pushes each through the shared ingest spine, writes
    an integration_sync_log row, updates last_synced_at/status, and compiles.
    """
    db = get_service_supabase()
    integration = get_integration(client_id)
    summary = {"added": 0, "updated": 0, "skipped": 0, "pii_flagged": 0, "error": None}

    if not integration or not integration.get("enabled"):
        summary["error"] = "drive not connected or disabled"
        return summary
    folder_id = (integration.get("config") or {}).get("folder_id")
    if not folder_id:
        summary["error"] = "no folder selected"
        return summary

    last_synced = integration.get("last_synced_at") or ""
    status = "ok"
    try:
        token = _access_token(integration)
        files = _list_folder_files(token, folder_id)
        for file in files:
            if last_synced and (file.get("modifiedTime") or "") <= last_synced:
                continue  # unchanged since last pass
            fetched = None
            try:
                fetched = _fetch_file(token, file)
            except Exception:
                logger.warning(
                    "drive_kb_sync: fetch failed for %s (tenant %s)",
                    file.get("name"),
                    client_id,
                    exc_info=True,
                )
            if fetched is None:
                summary["skipped"] += 1
                continue
            name, data = fetched
            outcome = ingest_file(
                client_id,
                source=PROVIDER,
                external_id=file["id"],
                filename=name,
                data=data,
            )
            key = outcome.get("status")
            if key == "added":
                summary["added"] += 1
            elif key == "updated":
                summary["updated"] += 1
            else:
                summary["skipped"] += 1
        if summary["added"] or summary["updated"]:
            compile_tenant_kb(client_id)
    except Exception as exc:
        logger.exception("drive_kb_sync: sync failed for tenant %s", client_id)
        summary["error"] = f"{type(exc).__name__}: {exc}"
        status = "error"

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        db.table("integration_sync_log").insert(
            {
                "client_id": client_id,
                "integration_id": integration.get("id"),
                "provider": PROVIDER,
                "synced_at": now_iso,
                "files_added": summary["added"],
                "files_updated": summary["updated"],
                "files_skipped": summary["skipped"],
                "files_pii_flagged": summary["pii_flagged"],
                "error": summary["error"],
            }
        ).execute()
        db.table("tenant_integrations").update(
            {
                "last_synced_at": now_iso,
                "last_sync_status": status if not summary["error"] else "error",
                "updated_at": now_iso,
            }
        ).eq("id", integration["id"]).execute()
    except Exception:
        logger.exception("drive_kb_sync: failed to record sync log for %s", client_id)

    return summary


def run_drive_kb_sync_due() -> int:
    """Sync every enabled Drive integration not synced in _SYNC_DUE_HOURS.

    Called from the 30-minute automation loop; self-gating gives the spec's
    daily cadence without clock-edge logic. Returns tenants synced.
    """
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=_SYNC_DUE_HOURS)
    ).isoformat()
    try:
        db = get_service_supabase()
        result = (
            db.table("tenant_integrations")
            .select("client_id, last_synced_at")
            .eq("provider", PROVIDER)
            .eq("enabled", True)
            .execute()
        )
    except Exception:
        logger.exception("drive_kb_sync: due-scan query failed")
        return 0

    synced = 0
    for row in result.data or []:
        last = row.get("last_synced_at") or ""
        if last and last > cutoff:
            continue
        sync_tenant_drive(row["client_id"])
        synced += 1
    if synced:
        logger.info("drive_kb_sync: daily pass synced %d tenants", synced)
    return synced
