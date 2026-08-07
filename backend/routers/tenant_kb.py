"""Tenant KB documents API — bulk upload, provenance list, delete, recompile.

Serves the dashboard drag-and-drop uploader AND the local folder-sync CLI
(both post multipart batches here); Drive sync writes through the same
service in backend/services/drive_kb_sync.py. Every write ends with a
compile so the widget/voice KB is live immediately.

client_id (NOT tenant_id) on tenant_kb_documents — schema discipline.
Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from jose import jwt
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.auth_service import _decode_token, _jwt_secret
from backend.services.tenant_kb import (
    compile_tenant_kb,
    count_active_documents,
    doc_limit_for_plan,
    ingest_file,
    upsert_document,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kb", tags=["tenant-kb"])

# Long-lived token for the folder-sync CLI (local-sync/anx_kb_sync.py).
# Dashboard sessions expire in 24h (stale-plan policy) which would kill
# --watch mode; kb_sync tokens carry NO plan claim (resolved live instead)
# and are rejected by get_current_tenant everywhere outside this router.
KB_SYNC_TOKEN_DAYS = 180


async def _get_kb_claims(authorization: str = Header(...)) -> dict:
    """Accept a normal dashboard token OR a purpose='kb_sync' token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    claims = _decode_token(authorization.removeprefix("Bearer ").strip())
    purpose = claims.get("purpose")
    if purpose and purpose != "kb_sync":
        raise HTTPException(status_code=401, detail="Token not valid for this endpoint")
    return claims


def _resolve_plan(claims: dict, tenant_id: str) -> str | None:
    """Dashboard tokens carry a fresh plan claim; kb_sync tokens don't
    (180-day tokens would serve stale plans), so look the plan up live."""
    if "plan" in claims:
        return claims.get("plan")
    try:
        db = get_service_supabase()
        result = (
            db.table("tenants").select("plan").eq("id", tenant_id).limit(1).execute()
        )
        rows = result.data or []
        return rows[0].get("plan") if rows else None
    except Exception:
        logger.warning("kb: live plan lookup failed for %s", tenant_id, exc_info=True)
        return None


class DocumentRow(BaseModel):
    id: str
    source: str
    filename: str
    status: str
    pii_flags: int = 0
    chars: int = 0
    synced_at: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentRow]
    total: int
    limit: int


class UploadResponse(BaseModel):
    results: list[dict]
    compiled: dict


class NoteRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=100_000)


class NoteResponse(BaseModel):
    filename: str
    status: str
    chars: int
    compiled: dict


_NOTE_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _note_external_id(title: str) -> str:
    """Stable per-title ID so retyping the same title updates the note."""
    slug = _NOTE_SLUG_RE.sub("-", title.strip().lower()).strip("-")
    return slug[:120] or "note"


def _require_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{tenant_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    tenant_id: str,
    claims: dict = Depends(_get_kb_claims),
):
    """Every KB source document with provenance — the second-brain index."""
    _require_tenant(claims, tenant_id)
    db = get_service_supabase()
    result = (
        db.table("tenant_kb_documents")
        .select("id, source, filename, status, pii_flags, content_md, synced_at")
        .eq("client_id", tenant_id)
        .neq("status", "deleted")
        .order("synced_at", desc=True)
        .execute()
    )
    rows = [
        DocumentRow(
            id=str(r["id"]),
            source=r.get("source") or "upload",
            filename=r.get("filename") or "",
            status=r.get("status") or "active",
            pii_flags=r.get("pii_flags") or 0,
            chars=len(r.get("content_md") or ""),
            synced_at=r.get("synced_at"),
        )
        for r in (result.data or [])
    ]
    return DocumentListResponse(
        documents=rows,
        total=len(rows),
        limit=doc_limit_for_plan(_resolve_plan(claims, tenant_id)),
    )


@router.post("/{tenant_id}/documents", response_model=UploadResponse)
async def upload_documents(
    tenant_id: str,
    files: list[UploadFile] = File(...),
    source: str = Form("upload"),
    claims: dict = Depends(_get_kb_claims),
):
    """Bulk-ingest documents (PDF/DOCX/TXT/MD). One bad file never fails the
    batch — each gets a per-file result. Compiles the KB once at the end.

    source: 'upload' (dashboard drag-drop, default) or 'local_sync' (the
    folder-sync CLI in local-sync/anx_kb_sync.py) — kept separate so the
    provenance table shows where each document came from."""
    _require_tenant(claims, tenant_id)
    if source not in ("upload", "local_sync"):
        raise HTTPException(status_code=400, detail="Invalid source")
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Max 100 files per batch")

    limit = doc_limit_for_plan(_resolve_plan(claims, tenant_id))
    active = count_active_documents(tenant_id)

    results = []
    for upload in files:
        filename = upload.filename or "unnamed"
        if active >= limit:
            results.append(
                {
                    "filename": filename,
                    "status": "skipped",
                    "reason": f"plan document limit reached ({limit})",
                }
            )
            continue
        data = await upload.read()
        # Threadpool: extract (PDF/DOCX parse) + per-file DB round-trips must
        # not run on the event loop — a 100-file batch would starve every
        # other request on this worker (audit 2026-07-14 H2).
        outcome = await run_in_threadpool(
            ingest_file,
            tenant_id,
            source=source,
            external_id=filename,
            filename=filename,
            data=data,
        )
        if outcome.get("status") == "added":
            active += 1
        results.append(outcome)

    compiled = await run_in_threadpool(compile_tenant_kb, tenant_id)
    return UploadResponse(results=results, compiled=compiled)


@router.post("/{tenant_id}/notes", response_model=NoteResponse)
async def add_note(
    tenant_id: str,
    note: NoteRequest,
    claims: dict = Depends(_get_kb_claims),
):
    """Add or update a typed knowledge note.

    Same ingest spine as file uploads: the note lands in tenant_kb_documents
    (source='note', external_id = title slug, so saving the same title again
    updates that note in place) and the KB recompiles immediately. The plan
    document limit applies only to NEW notes — editing an existing note is
    always allowed, even at the limit."""
    _require_tenant(claims, tenant_id)
    title = note.title.strip()
    content = note.content.strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="Title and content are required")

    external_id = _note_external_id(title)
    filename = f"{external_id}.md"
    content_md = f"# {title}\n\n{content}"

    def _ingest() -> str:
        db = get_service_supabase()
        existing = (
            db.table("tenant_kb_documents")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("source", "note")
            .eq("external_id", external_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if not existing.data:
            limit = doc_limit_for_plan(_resolve_plan(claims, tenant_id))
            if count_active_documents(tenant_id) >= limit:
                raise HTTPException(
                    status_code=400,
                    detail=f"plan document limit reached ({limit})",
                )
        return upsert_document(
            tenant_id,
            source="note",
            external_id=external_id,
            filename=filename,
            content_md=content_md,
        )

    outcome = await run_in_threadpool(_ingest)
    compiled = await run_in_threadpool(compile_tenant_kb, tenant_id)
    return NoteResponse(
        filename=filename,
        status=outcome,
        chars=len(content_md),
        compiled=compiled,
    )


@router.delete("/{tenant_id}/documents/{doc_id}")
async def delete_document(
    tenant_id: str,
    doc_id: str,
    claims: dict = Depends(_get_kb_claims),
):
    """Soft-delete one document and recompile the KB without it."""
    _require_tenant(claims, tenant_id)
    db = get_service_supabase()
    result = (
        db.table("tenant_kb_documents")
        .update({"status": "deleted"})
        .eq("id", doc_id)
        .eq("client_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    compiled = await run_in_threadpool(compile_tenant_kb, tenant_id)
    return {"deleted": True, "compiled": compiled}


@router.post("/{tenant_id}/recompile")
async def recompile(
    tenant_id: str,
    claims: dict = Depends(_get_kb_claims),
):
    """Rebuild widget_configs.knowledge_base from the active documents."""
    _require_tenant(claims, tenant_id)
    return {"compiled": await run_in_threadpool(compile_tenant_kb, tenant_id)}


@router.post("/{tenant_id}/sync-token")
async def create_sync_token(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Mint a long-lived token for the folder-sync CLI.

    Requires a live dashboard session (get_current_tenant rejects scoped
    tokens, so a sync token can never mint another). The token is scoped:
    purpose='kb_sync' works only on this router's document endpoints."""
    _require_tenant(claims, tenant_id)
    expires = datetime.now(timezone.utc) + timedelta(days=KB_SYNC_TOKEN_DAYS)
    token = jwt.encode(
        {"tenant_id": tenant_id, "purpose": "kb_sync", "exp": expires},
        _jwt_secret(),
        algorithm="HS256",
    )
    return {
        "token": token,
        "tenant_id": tenant_id,
        "expires_at": expires.isoformat(),
        "expires_in_days": KB_SYNC_TOKEN_DAYS,
    }
