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
        Stream the persisted inline bytes of a drafted document from
        documents.file_bytes (no Files API round-trip in the live path).

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
from backend.models.database import get_service_supabase
from backend.dependencies import _get_current_tenant
from backend.services.document_drafting import (
    DocumentDraftingError,
    draft_document,
)
from backend.services.structured_extractor import extract_structured
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
from backend.services.support_agent import run_support_query

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


def _managed_agents_unavailable(exc: ManagedAgentNotConfigured) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "error": "managed_agents_unavailable",
            "message": (
                "Managed Agent workflows are planned for a future update and "
                "are not enabled in this environment yet."
            ),
            "planned_update": True,
            "missing_config": exc.env_var,
        },
    )


def _managed_agents_health_payload() -> dict[str, Any]:
    any_configured = is_any_configured()
    return {
        "status": "configured" if any_configured else "planned",
        "message": (
            "Managed Agent workflows are configured."
            if any_configured
            else "Managed Agent workflows are planned for a future update."
        ),
        "any_configured": any_configured,
        "environment": bool(settings.managed_agents_environment_id),
        "lead_qualifier": bool(settings.lead_qualifier_agent_id),
        "document_drafter": bool(settings.document_drafter_agent_id),
        "codebase_reviewer": bool(settings.codebase_reviewer_agent_id),
        "support_agent": bool(settings.support_agent_id),
        "structured_extractor": bool(settings.structured_extractor_agent_id),
        "deep_researcher": bool(settings.deep_researcher_agent_id),
        "field_monitor": bool(settings.field_monitor_agent_id),
        "data_analyst": bool(settings.data_analyst_agent_id),
    }


@router.get("/health")
async def managed_agents_public_health():
    """Tenant-safe health probe for deploy and uptime verification.

    This endpoint intentionally avoids tenant auth and external API calls so
    operators can verify the managed-agents surface without a dashboard JWT.
    """
    payload = _managed_agents_health_payload()
    managed_agents_status = payload.pop("status")
    return {
        "status": "ok",
        "service": "managed-agents",
        "managed_agents_status": managed_agents_status,
        **payload,
    }


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
        terminated=False,
        stop_reason_type=None,
        last_event_id=None,
        session_id=session_id,
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
                session_id=session_id,
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
                    session_id=session_id,
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
        raise _managed_agents_unavailable(exc)

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
        session_id=terminal.session_id or "",
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
    return _managed_agents_health_payload()


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


class SupportQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    conversation_id: str | None = Field(default=None, max_length=128)


class SupportQueryResponse(BaseModel):
    answer: str
    confidence: str
    escalate_reason: str | None = None


class ExtractRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=20000)
    target_schema: Literal["lead", "appointment", "invoice", "contact"]


class ExtractResponse(BaseModel):
    data: dict[str, Any]


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
        raise _managed_agents_unavailable(exc)

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


@router.post("/{tenant_id}/support-query", response_model=SupportQueryResponse)
@limiter.limit("20/minute")
async def support_query_endpoint(
    tenant_id: str,
    request: Request,
    body: SupportQueryRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Run the tenant-scoped support agent with KB grounding."""
    _verify_tenant(claims, tenant_id)

    try:
        result = await run_in_threadpool(
            run_support_query,
            tenant_id,
            body.question,
            body.conversation_id,
        )
    except ManagedAgentNotConfigured as exc:
        raise _managed_agents_unavailable(exc)
    except ManagedAgentsError as exc:
        logger.exception("support_query failed for tenant %s", tenant_id)
        status = exc.status or 502
        if status < 400 or status >= 500:
            status = 502
        raise HTTPException(status_code=status, detail=str(exc))
    except ValueError as exc:
        logger.warning("support_query invalid response for tenant %s: %s", tenant_id, exc)
        raise HTTPException(status_code=502, detail=str(exc))

    return SupportQueryResponse(**result)


@router.post("/{tenant_id}/extract", response_model=ExtractResponse)
@limiter.limit("30/minute")
async def extract_endpoint(
    tenant_id: str,
    request: Request,
    body: ExtractRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Run the structured extractor managed agent for this tenant."""
    _verify_tenant(claims, tenant_id)

    try:
        extracted = await run_in_threadpool(
            extract_structured,
            tenant_id,
            body.raw_text,
            body.target_schema,
        )
    except ManagedAgentNotConfigured as exc:
        raise _managed_agents_unavailable(exc)
    except ManagedAgentsError as exc:
        logger.exception("extract failed for tenant %s", tenant_id)
        status = exc.status or 502
        if status < 400 or status >= 500:
            status = 502
        raise HTTPException(status_code=status, detail=str(exc))
    except ValueError as exc:
        logger.warning("extract invalid response for tenant %s: %s", tenant_id, exc)
        status = 400 if "unsupported target_schema" in str(exc) else 502
        raise HTTPException(status_code=status, detail=str(exc))

    return ExtractResponse(data=extracted)


_CONTENT_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _safe_content_disposition(file_name: str) -> str:
    """Build a safe Content-Disposition header value for ``file_name``.

    Prevents HTTP response-splitting via CR/LF in filenames and neutralises
    the double-quote used for the RFC 6266 ``filename=""`` parameter. For
    non-ASCII filenames we emit a UTF-8 ``filename*=`` value alongside an
    ASCII fallback.
    """
    from urllib.parse import quote

    # Strip CR/LF + null + control chars — these are the header-injection
    # vectors. Also replace path separators and quotes which would break
    # the ``filename=""`` parameter.
    cleaned = "".join(
        ch for ch in (file_name or "") if ch >= " " and ch not in ("\x7f",)
    )
    cleaned = cleaned.replace("\\", "_").replace("/", "_").replace('"', "_")
    if not cleaned:
        cleaned = "download"

    ascii_fallback = cleaned.encode("ascii", "replace").decode("ascii").replace("?", "_")
    quoted = quote(cleaned, safe="")
    return (
        f'attachment; filename="{ascii_fallback}"; '
        f"filename*=UTF-8''{quoted}"
    )


def _decode_bytea(raw: Any) -> bytes | None:
    """Decode a PostgREST-returned bytea value to raw bytes.

    PostgREST serializes bytea as a JSON string. Depending on server
    config it may come back as:
      - `\\x<hex>` escape (PostgreSQL default bytea_output = hex)
      - base64 (rare, only if `bytea_output = base64` is set)
    We handle both. Returns None if the input is empty/invalid.
    """
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    if not isinstance(raw, str) or not raw:
        return None
    if raw.startswith("\\x") or raw.startswith("\\\\x"):
        hex_part = raw.lstrip("\\").lstrip("x")
        try:
            return bytes.fromhex(hex_part)
        except ValueError:
            return None
    # Fallback: try base64 (covers bytea_output=escape as well, since
    # b64decode will raise on non-b64 input which we catch).
    import base64
    try:
        return base64.b64decode(raw, validate=True)
    except Exception:
        return None


def _fetch_drafted_document_bytes(tenant_id: str, document_id: str) -> tuple[bytes, str, str]:
    """Load a drafted document's bytes + filename + type. Enforces
    tenant isolation. Raises HTTPException on missing rows.
    """
    db = get_service_supabase()
    result = (
        db.table("documents")
        .select("id, tenant_id, file_name, file_type, file_bytes, generated_by_agent")
        .eq("id", document_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    row = result.data[0]

    raw = row.get("file_bytes")
    decoded = _decode_bytea(raw)
    if not decoded:
        raise HTTPException(
            status_code=404,
            detail="Document has no AI-drafted file bytes",
        )

    file_type = (row.get("file_type") or "").lower()
    file_name = row.get("file_name") or f"{document_id}.{file_type or 'bin'}"
    return decoded, file_name, file_type


@router.get("/{tenant_id}/documents/{document_id}/download")
@limiter.limit("30/minute")
async def download_drafted_document(
    tenant_id: str,
    document_id: str,
    request: Request,
    claims: dict = Depends(_get_current_tenant),
):
    """Stream the bytes of a drafted document from inline bytea
    storage. No upstream calls — the file was captured at draft time
    via the agent's base64 reply.
    """
    _verify_tenant(claims, tenant_id)

    file_bytes, file_name, file_type = await run_in_threadpool(
        _fetch_drafted_document_bytes, tenant_id, document_id,
    )

    content_type = _CONTENT_TYPES.get(file_type, "application/octet-stream")
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": _safe_content_disposition(file_name),
        },
    )
