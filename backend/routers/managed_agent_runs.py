"""FastAPI routes that trigger Claude Managed Agents runs.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI —
they break Pydantic body model introspection. Do not enable them in
this file (see `.claude/rules/python-fastapi.md`).

These endpoints run synchronously inside a threadpool because the
Managed Agents client is blocking (httpx sync); upgrade to an async
client if you need request-path throughput higher than a handful of
concurrent runs per worker.

Routes:
    POST /api/v1/managed-agents/{tenant_id}/lead-qualify
        Run the Lead Qualifier agent for a specific lead.

    POST /api/v1/managed-agents/{tenant_id}/draft-document
        Run the Document Drafter agent to produce a DOCX/XLSX/PDF
        quote, invoice, or proposal.

    GET  /api/v1/managed-agents/{tenant_id}/documents/{document_id}/download
        Stream the bytes of a drafted document via the Anthropic
        Files API (lazy fetch — bytes are not stored inline in V1).

    GET  /api/v1/managed-agents/{tenant_id}/health
        Report which agents are provisioned and reachable from this worker.
"""

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.document_drafting import (
    DocumentDraftingError,
    draft_document,
)
from backend.services.managed_agents import (
    ManagedAgentsClient,
    ManagedAgentsError,
    SessionTerminalState,
)
from backend.services.managed_agents_registry import (
    ManagedAgentNotConfigured,
    is_any_configured,
    lead_qualifier,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/managed-agents", tags=["managed-agents"])


class LeadQualifyRequest(BaseModel):
    lead_name: str = Field(..., min_length=1, max_length=200)
    lead_email: str | None = Field(default=None, max_length=320)
    lead_phone: str | None = Field(default=None, max_length=64)
    lead_interest: str | None = Field(default=None, max_length=2000)
    business_type: str | None = Field(default=None, max_length=120)
    business_name: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=500)


class LeadQualifyResponse(BaseModel):
    session_id: str
    terminated: bool
    stop_reason: str | None
    transcript: list[dict[str, Any]]


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")


def _qualify_lead_blocking(
    client: ManagedAgentsClient,
    *,
    agent_id: str,
    environment_id: str,
    prompt: str,
    tenant_id: str,
) -> tuple[SessionTerminalState, list[dict[str, Any]]]:
    """Run a single lead-qualifier session end-to-end. Blocking — call from
    a threadpool.
    """
    session = client.create_session(
        agent_id=agent_id,
        environment_id=environment_id,
        title=f"lead-qualify {tenant_id}",
        metadata={"tenant_id": tenant_id, "flow": "lead_qualify"},
    )
    session_id = session["id"]
    logger.info("managed_agents: created session %s for tenant %s", session_id, tenant_id)

    transcript: list[dict[str, Any]] = []

    # Stream first, then send kickoff.
    stream = client.stream_events(session_id)
    client.send_user_message(session_id, prompt)

    terminal = SessionTerminalState(
        terminated=False, stop_reason_type=None, last_event_id=None,
    )

    for event in stream:
        event_type = event.get("type", "")
        if event_type == "agent.message":
            transcript.append(
                {
                    "role": "assistant",
                    "content": event.get("content", []),
                    "id": event.get("id"),
                }
            )
        elif event_type == "agent.custom_tool_use":
            # Lead Qualifier has no custom tools — surface this as an error
            # so we notice a config drift loudly.
            logger.error(
                "lead_qualifier unexpectedly requested custom tool %s",
                event.get("tool_name"),
            )
            break
        elif event_type == "session.status_terminated":
            terminal = SessionTerminalState(
                terminated=True,
                stop_reason_type=None,
                last_event_id=event.get("id"),
            )
            break
        elif event_type == "session.status_idle":
            stop_reason = event.get("stop_reason") or {}
            stop_type = (
                stop_reason.get("type") if isinstance(stop_reason, dict) else None
            )
            if stop_type != "requires_action":
                terminal = SessionTerminalState(
                    terminated=False,
                    stop_reason_type=stop_type,
                    last_event_id=event.get("id"),
                )
                break

    return terminal, transcript


def _build_lead_qualify_prompt(req: LeadQualifyRequest) -> str:
    lines = ["Qualify this inbound lead:", ""]
    lines.append(f"- Lead name: {req.lead_name}")
    if req.lead_email:
        lines.append(f"- Email: {req.lead_email}")
    if req.lead_phone:
        lines.append(f"- Phone: {req.lead_phone}")
    if req.lead_interest:
        lines.append(f"- Stated interest: {req.lead_interest}")
    if req.business_name:
        lines.append(f"- Tenant business: {req.business_name}")
    if req.business_type:
        lines.append(f"- Tenant business type: {req.business_type}")
    if req.website:
        lines.append(f"- Lead website / company: {req.website}")
    lines.append("")
    lines.append(
        "Return the structured JSON summary described in your system prompt."
    )
    return "\n".join(lines)


@router.post("/{tenant_id}/lead-qualify", response_model=LeadQualifyResponse)
@limiter.limit("10/minute")
async def qualify_lead(
    tenant_id: str,
    request: Request,
    body: LeadQualifyRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Run the Lead Qualifier managed agent for this tenant's lead."""
    _verify_tenant(claims, tenant_id)

    try:
        handle = lead_qualifier()
    except ManagedAgentNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    prompt = _build_lead_qualify_prompt(body)
    client = ManagedAgentsClient()

    try:
        terminal, transcript = await run_in_threadpool(
            _qualify_lead_blocking,
            client,
            agent_id=handle.agent_id,
            environment_id=handle.environment_id,
            prompt=prompt,
            tenant_id=tenant_id,
        )
    except ManagedAgentsError as exc:
        logger.exception("lead qualify failed for tenant %s", tenant_id)
        status = exc.status or 502
        # Fold 4xx API errors into 4xx; 5xx into 502 bad gateway.
        if status < 400 or status >= 500:
            status = 502
        raise HTTPException(status_code=status, detail=str(exc))

    return LeadQualifyResponse(
        session_id=terminal.last_event_id or "",
        terminated=terminal.terminated,
        stop_reason=terminal.stop_reason_type,
        transcript=transcript,
    )


@router.get("/{tenant_id}/health")
async def managed_agents_health(
    tenant_id: str,
    request: Request,
    claims: dict = Depends(_get_current_tenant),
):
    """Report whether managed agents are provisioned. Does not make any
    outbound API calls — it only checks configured env vars so it is safe
    to call from dashboards.
    """
    _verify_tenant(claims, tenant_id)
    return {
        "any_configured": is_any_configured(),
        "environment": bool(settings.managed_agents_environment_id),
        "lead_qualifier": bool(settings.lead_qualifier_agent_id),
        "document_drafter": bool(settings.document_drafter_agent_id),
        "codebase_reviewer": bool(settings.codebase_reviewer_agent_id),
    }


# ---------------------------------------------------------------------------
# Document drafter — quotes / invoices / proposals
# ---------------------------------------------------------------------------


class DraftDocumentLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    qty: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)


class DraftDocumentCustomer(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)


class DraftDocumentRequest(BaseModel):
    kind: Literal["quote", "invoice", "proposal"]
    lead_id: str | None = Field(default=None, max_length=64)
    customer: DraftDocumentCustomer
    line_items: list[DraftDocumentLineItem] = Field(..., min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)


class DraftDocumentResponse(BaseModel):
    document_id: str
    title: str
    kind: str
    file_type: str
    file_name: str
    file_size_bytes: int | None = None
    download_url: str


@router.post("/{tenant_id}/draft-document", response_model=DraftDocumentResponse)
@limiter.limit("5/minute")
async def draft_document_endpoint(
    tenant_id: str,
    request: Request,
    body: DraftDocumentRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Run the Document Drafter managed agent to produce a file.

    Rate-limited tighter than lead-qualify (5/min vs 10/min) because
    each call spends container runtime on Opus + skill execution. The
    service-level plan gate blocks free-tier tenants before the agent
    is ever invoked.
    """
    _verify_tenant(claims, tenant_id)

    # Convert Pydantic models to plain dicts for the service (the
    # service is framework-agnostic and mockable in tests).
    customer_dict = body.customer.model_dump(exclude_none=True)
    line_items_dicts = [li.model_dump() for li in body.line_items]

    try:
        persisted = await run_in_threadpool(
            draft_document,
            tenant_id=tenant_id,
            lead_id=body.lead_id,
            kind=body.kind,
            customer=customer_dict,
            line_items=line_items_dicts,
            notes=body.notes,
        )
    except DocumentDraftingError as exc:
        logger.warning("draft_document failed for tenant %s: %s", tenant_id, exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except ManagedAgentNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    doc_id = persisted.get("id")
    metadata = persisted.get("draft_metadata") or {}
    return DraftDocumentResponse(
        document_id=doc_id,
        title=persisted.get("title", ""),
        kind=persisted.get("kind", body.kind),
        file_type=persisted.get("file_type", ""),
        file_name=persisted.get("file_name", ""),
        file_size_bytes=metadata.get("file_size_bytes") if isinstance(metadata, dict) else None,
        download_url=f"/api/v1/managed-agents/{tenant_id}/documents/{doc_id}/download",
    )


_CONTENT_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _fetch_drafted_document(tenant_id: str, document_id: str) -> dict[str, Any]:
    """Load a drafted document row, enforcing tenant isolation. Raises
    HTTPException on missing, cross-tenant, or legacy-format rows.
    """
    db = get_supabase()
    result = (
        db.table("documents")
        .select("id, tenant_id, file_name, file_type, anthropic_file_id, generated_by_agent")
        .eq("id", document_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    row = result.data[0]
    if not row.get("anthropic_file_id"):
        raise HTTPException(
            status_code=404,
            detail="Document has no AI-drafted file attached",
        )
    return row


def _download_drafted_blocking(file_id: str) -> bytes:
    """Blocking Files API fetch — wrap in run_in_threadpool."""
    return ManagedAgentsClient().get_file_content(file_id)


@router.get("/{tenant_id}/documents/{document_id}/download")
@limiter.limit("30/minute")
async def download_drafted_document(
    tenant_id: str,
    document_id: str,
    request: Request,
    claims: dict = Depends(_get_current_tenant),
):
    """Stream the bytes of a drafted document.

    V1 fetches fresh from the Anthropic Files API every time. If
    retention proves too short we will cache inline or in Supabase
    storage.
    """
    _verify_tenant(claims, tenant_id)

    row = _fetch_drafted_document(tenant_id, document_id)
    file_id = row["anthropic_file_id"]
    file_type = (row.get("file_type") or "").lower()
    file_name = row.get("file_name") or f"{document_id}.{file_type or 'bin'}"

    try:
        file_bytes = await run_in_threadpool(_download_drafted_blocking, file_id)
    except ManagedAgentsError as exc:
        logger.warning(
            "download_drafted_document failed tenant=%s doc=%s: %s",
            tenant_id, document_id, exc,
        )
        status = exc.status or 502
        # Upstream 404 → treat as gone (session file expired)
        if status == 404:
            raise HTTPException(
                status_code=410,
                detail="Upstream file is no longer available; regenerate the document",
            )
        if status < 400 or status >= 500:
            status = 502
        raise HTTPException(status_code=status, detail=str(exc))

    content_type = _CONTENT_TYPES.get(file_type, "application/octet-stream")
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
        },
    )
