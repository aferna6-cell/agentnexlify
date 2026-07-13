"""Tenant KB documents API — bulk upload, provenance list, delete, recompile.

Serves the dashboard drag-and-drop uploader AND the local folder-sync CLI
(both post multipart batches here); Drive sync writes through the same
service in backend/services/drive_kb_sync.py. Every write ends with a
compile so the widget/voice KB is live immediately.

client_id (NOT tenant_id) on tenant_kb_documents — schema discipline.
Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services.tenant_kb import (
    compile_tenant_kb,
    count_active_documents,
    doc_limit_for_plan,
    ingest_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kb", tags=["tenant-kb"])


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


def _require_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{tenant_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
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
        limit=doc_limit_for_plan(claims.get("plan")),
    )


@router.post("/{tenant_id}/documents", response_model=UploadResponse)
async def upload_documents(
    tenant_id: str,
    files: list[UploadFile] = File(...),
    claims: dict = Depends(_get_current_tenant),
):
    """Bulk-ingest documents (PDF/DOCX/TXT/MD). One bad file never fails the
    batch — each gets a per-file result. Compiles the KB once at the end."""
    _require_tenant(claims, tenant_id)
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Max 100 files per batch")

    limit = doc_limit_for_plan(claims.get("plan"))
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
        outcome = ingest_file(
            tenant_id,
            source="upload",
            external_id=filename,
            filename=filename,
            data=data,
        )
        if outcome.get("status") == "added":
            active += 1
        results.append(outcome)

    compiled = compile_tenant_kb(tenant_id)
    return UploadResponse(results=results, compiled=compiled)


@router.delete("/{tenant_id}/documents/{doc_id}")
async def delete_document(
    tenant_id: str,
    doc_id: str,
    claims: dict = Depends(_get_current_tenant),
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
    compiled = compile_tenant_kb(tenant_id)
    return {"deleted": True, "compiled": compiled}


@router.post("/{tenant_id}/recompile")
async def recompile(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Rebuild widget_configs.knowledge_base from the active documents."""
    _require_tenant(claims, tenant_id)
    return {"compiled": compile_tenant_kb(tenant_id)}
