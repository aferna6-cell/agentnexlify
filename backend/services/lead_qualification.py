"""AI lead qualification via Claude Managed Agents.

Runs the `lead_qualifier` Managed Agent asynchronously after a new lead
is captured. Persists the structured JSON response back to the lead
record for dashboard display.

This is the paid-plan counterpart to `backend/services/lead_scoring.py`:

    lead_scoring   — rule-based, instant, runs on EVERY lead.
    lead_qualification — Claude Managed Agent, takes 10-30s + API cost,
                         runs only on paid plans (>= growth).

Qualification output shape (matches the agent system prompt in
`config/managed_agents.yaml`):

    {
      "intent_score":         1-10,
      "fit_score":            1-10,
      "recommendation":       "hot_call_now" | "warm_nurture_sequence"
                              | "cold_drop" | "disqualify_spam",
      "reasoning":            "<paragraph>",
      "suggested_first_reply":"<paragraph>"
    }

This service is blocking (the Managed Agents client is sync httpx).
Call it from a FastAPI BackgroundTask or a threadpool — never from
the request path directly.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from backend.models.database import get_supabase
from backend.services.managed_agents import (
    ManagedAgentsClient,
    ManagedAgentsError,
    SessionTerminalState,
)
from backend.services.managed_agents_registry import (
    ManagedAgentNotConfigured,
    lead_qualifier,
)

logger = logging.getLogger(__name__)

# Plans that are allowed to spend on Claude Managed Agents for auto
# qualification. Free tier is explicitly excluded so we don't burn
# credits on drive-by traffic.
_ELIGIBLE_PLANS = frozenset({"growth", "professional", "autopilot", "enterprise"})

_VALID_RECOMMENDATIONS = frozenset({
    "hot_call_now",
    "warm_nurture_sequence",
    "cold_drop",
    "disqualify_spam",
})


class LeadQualificationError(Exception):
    """Raised when qualification cannot be run or its output can't be parsed."""


def _build_prompt(lead: dict[str, Any], tenant: dict[str, Any]) -> str:
    """Build the single user message we send to the agent."""
    lines = ["Qualify this inbound lead:", ""]
    lines.append(f"- Lead name: {lead.get('name') or '(unknown)'}")
    if lead.get("email"):
        lines.append(f"- Email: {lead['email']}")
    if lead.get("phone"):
        lines.append(f"- Phone: {lead['phone']}")
    if lead.get("areas_of_interest"):
        lines.append(f"- Stated interest: {lead['areas_of_interest']}")
    if lead.get("timeline"):
        lines.append(f"- Timeline: {lead['timeline']}")
    if lead.get("budget"):
        lines.append(f"- Budget: {lead['budget']}")
    business_name = tenant.get("business_name") or tenant.get("name")
    if business_name:
        lines.append(f"- Tenant business: {business_name}")
    if tenant.get("business_type"):
        lines.append(f"- Tenant business type: {tenant['business_type']}")
    lines.append("")
    lines.append(
        "Return ONLY the structured JSON summary described in your system "
        "prompt. No prose before or after the JSON block."
    )
    return "\n".join(lines)


def _extract_text_blocks(content: list[Any] | None) -> str:
    """Flatten the content array of an agent.message event into a string."""
    if not content:
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def _extract_json_from_reply(text: str) -> dict[str, Any] | None:
    """Pull the first JSON object out of an agent reply.

    The agent may return a ```json fenced block, a bare object, or prose
    wrapping a JSON blob. We try the most specific strategies first, then
    fall back to regex.
    """
    text = text.strip()
    if not text:
        return None

    # Strategy 1: direct parse (clean JSON-only reply)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip a markdown fence and try again
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Strategy 3: greedy match for the outermost {...} block
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            parsed = json.loads(brace.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


def _normalize_qualification(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce a raw parsed reply into a persisted shape. Drops unknown keys,
    clamps numeric scores, rejects out-of-range recommendations.
    """
    normalized: dict[str, Any] = {}

    for key in ("intent_score", "fit_score"):
        val = raw.get(key)
        if isinstance(val, (int, float)):
            normalized[key] = max(1, min(10, int(val)))
        elif isinstance(val, str):
            try:
                normalized[key] = max(1, min(10, int(val)))
            except ValueError:
                pass

    rec = raw.get("recommendation")
    if isinstance(rec, str) and rec in _VALID_RECOMMENDATIONS:
        normalized["recommendation"] = rec

    for key in ("reasoning", "suggested_first_reply"):
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            normalized[key] = val.strip()

    return normalized


def _run_qualifier_session(
    client: ManagedAgentsClient,
    *,
    agent_id: str,
    environment_id: str,
    prompt: str,
    tenant_id: str,
    lead_id: str,
) -> tuple[SessionTerminalState, str]:
    """Run the managed agent session and return the final assistant text."""
    session = client.create_session(
        agent_id=agent_id,
        environment_id=environment_id,
        title=f"lead-qualify {tenant_id}",
        metadata={
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "flow": "lead_qualification",
        },
    )
    session_id = session["id"]
    logger.info(
        "lead_qualification: session %s created for lead %s (tenant %s)",
        session_id, lead_id, tenant_id,
    )

    stream = client.stream_events(session_id)
    client.send_user_message(session_id, prompt)

    assistant_chunks: list[str] = []
    terminal = SessionTerminalState(
        terminated=False, stop_reason_type=None, last_event_id=None,
    )

    for event in stream:
        event_type = event.get("type", "")
        if event_type == "agent.message":
            assistant_chunks.append(_extract_text_blocks(event.get("content")))
        elif event_type == "agent.custom_tool_use":
            logger.error(
                "lead_qualification: agent unexpectedly used custom tool %s",
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

    return terminal, "\n".join(c for c in assistant_chunks if c)


def qualify_lead(lead_id: str) -> dict[str, Any] | None:
    """Run the qualifier agent for one lead and persist the result.

    Returns the persisted qualification dict, or None if qualification
    was skipped (free tier, missing data, not configured).

    Raises:
        LeadQualificationError: the agent ran but its output could not
            be parsed or normalized.
    """
    db = get_supabase()

    # 1. Load lead
    lead_res = (
        db.table("leads")
        .select("id, client_id, name, email, phone, areas_of_interest, timeline, budget")
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    if not lead_res.data:
        logger.warning("lead_qualification: lead %s not found, skipping", lead_id)
        return None
    lead = lead_res.data[0]

    # 2. Load tenant + plan gate
    tenant_id = lead.get("client_id")
    if not tenant_id:
        logger.warning("lead_qualification: lead %s has no client_id, skipping", lead_id)
        return None

    tenant_res = (
        db.table("tenants")
        .select("id, business_name, business_type, plan")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not tenant_res.data:
        logger.warning("lead_qualification: tenant %s not found for lead %s", tenant_id, lead_id)
        return None
    tenant = tenant_res.data[0]

    plan = (tenant.get("plan") or "free").lower()
    if plan not in _ELIGIBLE_PLANS:
        logger.info(
            "lead_qualification: skipping lead %s — plan %r not eligible",
            lead_id, plan,
        )
        return None

    # 3. Get agent handle (may raise ManagedAgentNotConfigured)
    try:
        handle = lead_qualifier()
    except ManagedAgentNotConfigured as exc:
        logger.warning("lead_qualification: not configured (%s)", exc)
        return None

    # 4. Run the session
    prompt = _build_prompt(lead, tenant)
    client = ManagedAgentsClient()

    try:
        terminal, reply_text = _run_qualifier_session(
            client,
            agent_id=handle.agent_id,
            environment_id=handle.environment_id,
            prompt=prompt,
            tenant_id=tenant_id,
            lead_id=lead_id,
        )
    except ManagedAgentsError as exc:
        logger.warning(
            "lead_qualification: session failed for lead %s: %s (request_id=%s)",
            lead_id, exc, exc.request_id,
        )
        return None

    if not reply_text:
        logger.warning(
            "lead_qualification: lead %s got no assistant messages "
            "(terminated=%s stop=%s)",
            lead_id, terminal.terminated, terminal.stop_reason_type,
        )
        return None

    # 5. Parse + normalize JSON output
    raw = _extract_json_from_reply(reply_text)
    if not raw:
        raise LeadQualificationError(
            f"lead {lead_id}: agent reply did not contain parseable JSON"
        )
    normalized = _normalize_qualification(raw)
    if not normalized.get("recommendation"):
        raise LeadQualificationError(
            f"lead {lead_id}: normalized qualification missing recommendation "
            f"(raw={raw!r})"
        )

    # 6. Persist back to lead
    update_payload: dict[str, Any] = {
        "qualification_json": normalized,
        "qualification_recommendation": normalized["recommendation"],
        "qualified_at": datetime.now(timezone.utc).isoformat(),
    }
    db.table("leads").update(update_payload).eq("id", lead_id).execute()

    # 7. Activity log entry (best-effort)
    try:
        db.table("activity_log").insert(
            {
                "tenant_id": tenant_id,
                "lead_id": lead_id,
                "activity_type": "lead_qualified_ai",
                "description": (
                    f"AI qualification: {normalized['recommendation']} "
                    f"(intent={normalized.get('intent_score', '?')}, "
                    f"fit={normalized.get('fit_score', '?')})"
                ),
                "metadata": normalized,
            }
        ).execute()
    except Exception:
        logger.warning(
            "lead_qualification: failed to log activity for lead %s",
            lead_id, exc_info=True,
        )

    logger.info(
        "lead_qualification: lead %s qualified as %s (intent=%s fit=%s)",
        lead_id,
        normalized["recommendation"],
        normalized.get("intent_score"),
        normalized.get("fit_score"),
    )
    return normalized


def qualify_lead_background(lead_id: str) -> None:
    """Fire-and-forget wrapper for FastAPI BackgroundTasks."""
    try:
        qualify_lead(lead_id)
    except LeadQualificationError as exc:
        logger.warning("lead_qualification: %s", exc)
    except Exception:
        logger.exception(
            "lead_qualification: unexpected failure for lead %s", lead_id,
        )
