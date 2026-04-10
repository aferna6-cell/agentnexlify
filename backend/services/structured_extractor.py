"""Structured extraction via Claude Managed Agents.

Runs the `structured_extractor` managed agent with a target schema and
raw text input. The agent contract asks for strict JSON-only output,
but Haiku will occasionally wrap its reply in ```json fences or add a
leading explanation even when told not to — `_extract_json_from_reply`
tolerates those cases so callers do not see spurious ValueError in
production.

This service is blocking because the Managed Agents client is sync
httpx. Call it from a FastAPI threadpool.
"""

import json
import logging
import re
from typing import Any

from backend.services.managed_agents import ManagedAgentsClient, SessionTerminalState
from backend.services.managed_agents_registry import structured_extractor

logger = logging.getLogger(__name__)

_SCHEMA_FIELDS = {
    "lead": [
        "name",
        "email",
        "phone",
        "interest",
        "timeline",
        "budget",
        "source",
    ],
    "appointment": [
        "name",
        "email",
        "phone",
        "service",
        "preferred_date",
        "preferred_time",
        "notes",
    ],
    "invoice": [
        "invoice_number",
        "customer_name",
        "customer_email",
        "due_date",
        "total",
        "balance_due",
        "line_items",
    ],
    "contact": [
        "name",
        "email",
        "phone",
        "company",
        "title",
        "address",
    ],
}


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
        for event in self._inner.stream_events(session_id):
            if event.get("type") == "agent.message":
                self._assistant_chunks.append(_extract_text_blocks(event.get("content")))
            yield event

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


def _extract_json_from_reply(text: str) -> dict[str, Any] | None:
    """Return the first JSON object found in the reply, or None.

    Tolerates three shapes in priority order:
      1. Pure JSON (strict json.loads)
      2. Fenced ```json { ... } ``` or ``` { ... } ```
      3. First {...} substring in the reply (last-resort regex)
    """
    text = text.strip()
    if not text:
        return None

    # 1. Pure JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Fenced code block
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # 3. Greedy brace fallback
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            parsed = json.loads(brace.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


def _build_prompt(raw_text: str, target_schema: str) -> str:
    fields = _SCHEMA_FIELDS[target_schema]
    field_lines = [f"- {field_name}" for field_name in fields]
    return "\n".join(
        [
            "Extract structured data from the raw text into one JSON object.",
            "",
            "[SCHEMA]",
            f"target_schema: {target_schema}",
            "fields:",
            *field_lines,
            "",
            "Rules:",
            "- Return ONLY valid JSON with exactly these keys.",
            "- Use null for any missing or unknown field.",
            "- Preserve line_items as a JSON array when present.",
            "",
            "[RAW_TEXT]",
            raw_text.strip(),
        ]
    )


def extract_structured(
    tenant_id: str, raw_text: str, target_schema: str,
) -> dict[str, Any]:
    """Extract schema-shaped JSON from raw text."""
    if target_schema not in _SCHEMA_FIELDS:
        allowed = ", ".join(sorted(_SCHEMA_FIELDS))
        raise ValueError(f"unsupported target_schema {target_schema!r}; expected one of: {allowed}")

    handle = structured_extractor()
    prompt = _build_prompt(raw_text, target_schema)
    client = _CapturingManagedAgentClient(ManagedAgentsClient())
    session = client.create_session(
        agent_id=handle.agent_id,
        environment_id=handle.environment_id,
        title=f"structured-extract {target_schema}",
        metadata={
            "tenant_id": tenant_id,
            "flow": "structured_extractor",
            "target_schema": target_schema,
        },
    )
    session_id = session["id"]
    logger.info(
        "structured_extractor: session %s created for tenant %s schema=%s",
        session_id, tenant_id, target_schema,
    )

    terminal = client.run_until_idle(session_id, kickoff_text=prompt)
    reply_text = client.reply_text
    if not reply_text:
        raise ValueError(
            "structured_extractor returned no assistant text "
            f"(terminated={terminal.terminated} stop={terminal.stop_reason_type})"
        )

    parsed = _extract_json_from_reply(reply_text)
    if parsed is None:
        raise ValueError(
            f"structured_extractor returned invalid JSON: {reply_text}"
        )

    return parsed
