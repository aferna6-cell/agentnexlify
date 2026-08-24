"""Tenant-facing support responses via Claude Managed Agents.

Runs the `support_agent` managed agent with tenant business context,
tenant knowledge-base snippets, and recent conversation history. The
agent is intentionally narrow: it should answer only from the tenant's
provided knowledge, escalate when confidence is low, and avoid generic
or invented business facts.

This service is blocking because the Managed Agents client is sync
httpx. Call it from a FastAPI threadpool.
"""

import json
import logging
import re
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.managed_agents import ManagedAgentsClient, SessionTerminalState
from backend.services.managed_agents_registry import support_agent
from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

_DAY_ORDER = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
_VALID_CONFIDENCE = frozenset({"high", "medium", "low"})


class _CapturingManagedAgentClient:
    """Delegate to a real client while capturing assistant text blocks."""

    def __init__(self, inner: Any):
        self._inner = inner
        self._assistant_chunks: list[str] = []

    def create_session(self, **kwargs: Any) -> dict[str, Any]:
        return self._inner.create_session(**kwargs)

    def send_user_message(self, session_id: str, text: str) -> dict[str, Any]:
        return self._inner.send_user_message(session_id, text)

    def stream_events(self, session_id: str):
        stream = self._inner.stream_events(session_id)

        def _capture_events():
            for event in stream:
                if event.get("type") == "agent.message":
                    self._assistant_chunks.append(
                        _extract_text_blocks(event.get("content"))
                    )
                yield event

        return _capture_events()

    def run_until_idle(
        self, session_id: str, *, kickoff_text: str | None = None,
    ) -> SessionTerminalState:
        return ManagedAgentsClient.run_until_idle(
            self, session_id, kickoff_text=kickoff_text,
        )

    @property
    def reply_text(self) -> str:
        return "\n".join(chunk for chunk in self._assistant_chunks if chunk).strip()


def _extract_text_blocks(content: list[Any] | None) -> str:
    if not content:
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def _one_line(value: Any, *, limit: int = 240) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) > limit:
        return f"{text[:limit].rstrip()}..."
    return text


def _extract_json_from_reply(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            parsed = json.loads(brace.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def _normalize_confidence(value: Any) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _VALID_CONFIDENCE:
            return lowered
    if isinstance(value, (int, float)):
        if value >= 0.8:
            return "high"
        if value >= 0.45:
            return "medium"
        return "low"
    # Unrecognized or missing -> "low", NOT "medium".
    #
    # This value is the entire release gate on text shown to a tenant's
    # customer: widget_chat_fallback.py ships the answer when confidence is
    # high or medium, and hands off to a human when it is low. Defaulting an
    # absent or malformed confidence to "medium" made the gate fail OPEN — a
    # model that simply omitted the field had its answer shipped unchecked.
    # A quality gate on customer-facing text fails closed.
    return "low"


def _format_hours(hours_row: dict[str, Any] | None) -> str:
    if not hours_row:
        return "(not configured)"

    timezone = hours_row.get("timezone") or "unspecified timezone"
    from backend.services.booking import coerce_hours

    hours = coerce_hours(hours_row.get("hours"))
    if not isinstance(hours, dict):
        return f"Timezone: {timezone}"

    lines = [f"Timezone: {timezone}"]
    for day in _DAY_ORDER:
        config = hours.get(day)
        if not isinstance(config, dict):
            continue
        if not config.get("enabled", False):
            lines.append(f"- {day.capitalize()}: closed")
            continue
        start = config.get("start") or "?"
        end = config.get("end") or "?"
        lines.append(f"- {day.capitalize()}: {start}-{end}")
    return "\n".join(lines)


def _load_tenant_context(tenant_id: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any] | None]:
    db = get_service_supabase()

    tenant_res = (
        tenant_select(db, "tenants", tenant_id, "id, business_name, business_type")
        .limit(1)
        .execute()
    )
    if not tenant_res.data:
        raise ValueError(f"tenant {tenant_id} not found")
    tenant = tenant_res.data[0]

    widget_res = (
        tenant_select(db, "widget_configs", tenant_id, "knowledge_base, custom_instructions")
        .limit(1)
        .execute()
    )
    widget = widget_res.data[0] if widget_res.data else {}

    faq_res = (
        tenant_select(db, "faq_entries", tenant_id, "question, answer")
        .eq("is_active", True)
        .limit(6)
        .execute()
    )

    hours_res = (
        tenant_select(db, "business_hours", tenant_id, "timezone, hours")
        .limit(1)
        .execute()
    )
    hours_row = hours_res.data[0] if hours_res.data else None

    return tenant, widget, faq_res.data or [], hours_row


def _resolve_session_id(tenant_id: str, conversation_id: str | None) -> str | None:
    if not conversation_id:
        return None

    db = get_service_supabase()
    by_id = (
        tenant_select(db, "conversations", tenant_id, "id, session_id")
        .eq("id", conversation_id)
        .limit(1)
        .execute()
    )
    if by_id.data:
        return by_id.data[0].get("session_id") or conversation_id

    by_session = (
        tenant_select(db, "conversations", tenant_id, "id, session_id")
        .eq("session_id", conversation_id)
        .limit(1)
        .execute()
    )
    if by_session.data:
        return by_session.data[0].get("session_id") or conversation_id

    return conversation_id


def _load_conversation_history(
    tenant_id: str, conversation_id: str | None,
) -> list[dict[str, str]]:
    session_id = _resolve_session_id(tenant_id, conversation_id)
    if not session_id:
        return []

    db = get_service_supabase()
    result = (
        tenant_select(db, "chat_messages", tenant_id, "role, content")
        .eq("session_id", session_id)
        .order("created_at")
        .limit(12)
        .execute()
    )
    history: list[dict[str, str]] = []
    for row in (result.data or []):
        history.append(
            {
                "role": str(row.get("role") or "unknown"),
                "content": _one_line(row.get("content"), limit=400),
            }
        )
    return history


def _build_prompt(
    tenant: dict[str, Any],
    widget: dict[str, Any],
    faq_entries: list[dict[str, Any]],
    hours_row: dict[str, Any] | None,
    conversation_history: list[dict[str, str]],
    customer_question: str,
) -> str:
    tenant_lines = [
        f"Business name: {tenant.get('business_name') or '(unknown)'}",
        f"Business type: {tenant.get('business_type') or '(unknown)'}",
        "Business hours:",
        _format_hours(hours_row),
    ]

    kb_lines: list[str] = []
    custom_instructions = _one_line(widget.get("custom_instructions"), limit=1000)
    if custom_instructions:
        kb_lines.append("Custom instructions:")
        kb_lines.append(custom_instructions)

    knowledge_base = str(widget.get("knowledge_base") or "").strip()
    if knowledge_base:
        kb_lines.append("Knowledge base excerpt:")
        snippet = knowledge_base[:2400]
        if len(knowledge_base) > 2400:
            snippet += "\n[Knowledge base truncated]"
        kb_lines.append(snippet)

    if faq_entries:
        kb_lines.append("FAQ entries:")
        for entry in faq_entries:
            question = _one_line(entry.get("question"), limit=180)
            answer = _one_line(entry.get("answer"), limit=280)
            kb_lines.append(f"- Q: {question}")
            kb_lines.append(f"  A: {answer}")

    history_lines = [
        f"- {item['role']}: {item['content']}"
        for item in conversation_history
        if item.get("content")
    ]

    return "\n".join(
        [
            "[TENANT_CONTEXT]",
            "\n".join(tenant_lines),
            "",
            "[KB_SNIPPET]",
            "\n".join(kb_lines) if kb_lines else "(no tenant knowledge available)",
            "",
            "[CONVERSATION_HISTORY]",
            "\n".join(history_lines) if history_lines else "(no prior conversation history)",
            "",
            "[QUESTION]",
            customer_question.strip(),
            "",
            "Respond to the customer using only the provided tenant context. "
            "Prefer JSON with answer, confidence, and escalate_reason.",
        ]
    )


def _parse_support_reply(reply_text: str) -> dict[str, Any]:
    parsed = _extract_json_from_reply(reply_text)
    if isinstance(parsed, dict):
        answer = (
            parsed.get("answer")
            or parsed.get("response")
            or parsed.get("reply")
            or parsed.get("message")
        )
        if isinstance(answer, str) and answer.strip():
            escalate_reason = parsed.get("escalate_reason") or parsed.get("escalation_reason")
            if escalate_reason is not None and not isinstance(escalate_reason, str):
                escalate_reason = str(escalate_reason)
            return {
                "answer": answer.strip(),
                "confidence": _normalize_confidence(parsed.get("confidence")),
                "escalate_reason": escalate_reason.strip() if isinstance(escalate_reason, str) and escalate_reason.strip() else None,
            }

    answer = reply_text.strip()
    if not answer:
        raise ValueError("support_agent returned no assistant text")

    lowered = answer.lower()
    confidence = "medium"
    escalate_reason = None
    if any(
        phrase in lowered
        for phrase in (
            "human",
            "team can help",
            "support can help",
            "not enough information",
            "can't confirm",
            "cannot confirm",
            "don't have enough",
            "do not have enough",
        )
    ):
        confidence = "low"
        escalate_reason = "low_confidence_or_missing_kb_support"

    return {
        "answer": answer,
        "confidence": confidence,
        "escalate_reason": escalate_reason,
    }


def build_support_prompt(
    tenant_id: str,
    customer_question: str,
    conversation_id: str | None = None,
) -> str:
    """Build the structured prompt for a support query without running an agent.

    Used by widget_chat._run_support_fallback to pre-build context for the
    agent-service path before falling through to managed-agents if needed.
    """
    tenant, widget, faq_entries, hours_row = _load_tenant_context(tenant_id)
    history = _load_conversation_history(tenant_id, conversation_id)
    return _build_prompt(tenant, widget, faq_entries, hours_row, history, customer_question)


def parse_support_reply(reply_text: str) -> dict[str, Any]:
    """Parse a support agent reply (JSON or plain text) into a normalized dict.

    Public alias for the internal _parse_support_reply. Used by
    widget_chat._run_support_fallback to parse agent-service results with
    the same logic applied to managed-agents results.
    """
    return _parse_support_reply(reply_text)


def run_support_query(
    tenant_id: str,
    customer_question: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Run the support agent for a tenant-scoped customer question."""
    tenant, widget, faq_entries, hours_row = _load_tenant_context(tenant_id)
    history = _load_conversation_history(tenant_id, conversation_id)
    prompt = _build_prompt(
        tenant,
        widget,
        faq_entries,
        hours_row,
        history,
        customer_question,
    )

    handle = support_agent()
    client = _CapturingManagedAgentClient(ManagedAgentsClient())
    # Deliberately NOT budget-capped, unlike every other product agent session.
    # This is the interactive widget path: a customer is watching, and it
    # already runs under an 8s wall-clock timeout that bounds spend far more
    # tightly than a dollar cap would. A budget-truncated answer mid-sentence
    # is worse for the customer than the marginal cost. See
    # `.claude/rules/task-budgets.md` "Where NOT to".
    session = client.create_session(
        agent_id=handle.agent_id,
        environment_id=handle.environment_id,
        title=f"support-query {tenant_id}",
        metadata={
            "tenant_id": tenant_id,
            "flow": "support_agent",
            "conversation_id": conversation_id or "",
        },
    )
    session_id = session["id"]
    logger.info("support_agent: session %s created for tenant %s", session_id, tenant_id)

    terminal = client.run_until_idle(session_id, kickoff_text=prompt)
    if not client.reply_text:
        raise ValueError(
            "support_agent returned no assistant text "
            f"(terminated={terminal.terminated} stop={terminal.stop_reason_type})"
        )

    parsed = _parse_support_reply(client.reply_text)
    logger.info(
        "support_agent: tenant=%s confidence=%s escalated=%s",
        tenant_id,
        parsed.get("confidence"),
        bool(parsed.get("escalate_reason")),
    )
    return parsed
