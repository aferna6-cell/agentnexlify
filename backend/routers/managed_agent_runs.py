"""Example FastAPI routes that trigger Claude Managed Agents runs.

WARNING: PEP 563 deferred annotations are incompatible with FastAPI —
they break Pydantic body model introspection. Do not enable them in
this file (see `.claude/rules/python-fastapi.md`).

These endpoints are intentionally minimal and serve as a reference for how
to integrate a Managed Agent into a tenant-scoped request path. They run
synchronously inside a threadpool because the Managed Agents client is
blocking (httpx sync); upgrade to an async client if you need request-path
throughput higher than a handful of concurrent runs per worker.

Routes:
    POST /api/v1/managed-agents/{tenant_id}/lead-qualify
        Run the Lead Qualifier agent for a specific lead.

    GET  /api/v1/managed-agents/{tenant_id}/health
        Report which agents are provisioned and reachable from this worker.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from backend.config import settings
from backend.limiter import limiter
from backend.routers.auth import _get_current_tenant
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
