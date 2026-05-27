"""Agent OS orchestrator.

Classifies a user message and routes it one of three ways:
  - answer:   reply directly in chat, no worker agent
  - delegate: spawn a worker-agent run that produces an approval-gated draft
  - backlog:  no available worker agent fits — park it for an owner decision

Opus 4.7 makes the routing decision. Worker agents are auto-discovered from the
``os_workers`` package — the registry there is the single source of truth for
which agents the orchestrator may route to.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.services import os_workers
from backend.services.llm_runtime import call_claude_messages
from backend.services.os_memory import search_memory, write_memory

logger = logging.getLogger(__name__)

ORCHESTRATOR_MODEL = "claude-opus-4-7"


@dataclass
class OrchestratorDecision:
    action: str  # answer | delegate | backlog
    reply: str
    agent_name: str | None = None
    deliverable_title: str | None = None
    reason: str = ""
    thought_process: list[dict] = field(default_factory=list)
    memory_writes: list[dict] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def available_agents() -> dict[str, str]:
    return os_workers.worker_descriptions()


def _system_prompt(memory_hits: list[dict]) -> str:
    agent_lines = "\n".join(
        f"- {name}: {desc}" for name, desc in available_agents().items()
    )
    memory_block = "none"
    if memory_hits:
        memory_block = "\n".join(
            f"- ({hit.get('kind', 'fact')}) {hit.get('content', '')}"
            for hit in memory_hits
        )
    return (
        "You are the orchestrator for AgentNexLiFy's Agent OS. You route a "
        "small-business owner's request to the right place.\n\n"
        f"Available worker agents:\n{agent_lines}\n\n"
        f"Relevant memory about this business:\n{memory_block}\n\n"
        "Respond with ONLY a JSON object, no prose, no code fences:\n"
        "{\n"
        '  "action": "answer" | "delegate" | "backlog",\n'
        '  "reply": "<one short chat reply to the user>",\n'
        '  "agent_name": "<worker name when action=delegate, else null>",\n'
        '  "deliverable_title": "<short draft title when action=delegate, else null>",\n'
        '  "reason": "<why this routing — required for backlog>",\n'
        '  "memory": [{"kind": "fact|preference|decision", "content": "<durable fact worth remembering>"}]\n'
        "}\n\n"
        'Use "answer" for greetings and simple questions you can resolve in chat.\n'
        'Use "delegate" when the user wants a task done that yields a reviewable draft.\n'
        'Use "backlog" only when no available worker agent can serve the request.\n'
        'Leave "memory" empty unless the message states a durable fact about the business.'
    )


def _parse_decision(text: str) -> dict | None:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        logger.warning("orchestrator decision JSON parse failed", exc_info=True)
        return None


def _fallback_decision(user_message: str) -> OrchestratorDecision:
    """Used when the LLM is unavailable or returns unparseable output."""
    return OrchestratorDecision(
        action="delegate",
        reply="On it — I'll prepare a draft and post it here for your review.",
        agent_name="generalist",
        deliverable_title="Draft",
        reason="orchestrator fallback (LLM unavailable or invalid output)",
        thought_process=[
            {
                "step": 1,
                "label": "Routed to generalist",
                "status": "done",
                "detail": "Fallback routing — orchestrator LLM unavailable.",
                "at": _now(),
            }
        ],
    )


async def orchestrate(
    db,
    client_id: str,
    user_message: str,
    history: list[dict] | None = None,
) -> OrchestratorDecision:
    """Classify a user message and return a routing decision."""
    memory_hits = await search_memory(db, client_id, user_message, match_count=6)
    messages: list[dict] = []
    for turn in (history or [])[-8:]:
        role = "assistant" if turn.get("role") in ("assistant", "agent") else "user"
        content = (turn.get("content") or "").strip()
        if content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        result = await call_claude_messages(
            operation="os_orchestrate",
            model=ORCHESTRATOR_MODEL,
            max_tokens=1200,
            system=_system_prompt(memory_hits),
            messages=messages,
            metadata={"client_id": client_id},
        )
    except Exception:
        logger.warning("orchestrator LLM call failed; using fallback", exc_info=True)
        return _fallback_decision(user_message)

    decision = _parse_decision(result.text)
    if not decision:
        return _fallback_decision(user_message)

    action = decision.get("action")
    if action not in ("answer", "delegate", "backlog"):
        return _fallback_decision(user_message)

    agent_name = decision.get("agent_name")
    if action == "delegate" and agent_name not in available_agents():
        # LLM picked a worker that does not exist yet — that is a no-fit.
        action = "backlog"

    memory_writes = [
        m
        for m in (decision.get("memory") or [])
        if isinstance(m, dict) and (m.get("content") or "").strip()
    ]

    thought: list[dict] = []
    if action == "delegate":
        thought = [
            {
                "step": 1,
                "label": "Request classified",
                "status": "done",
                "detail": f"Routed to '{agent_name}' worker agent.",
                "at": _now(),
            }
        ]

    return OrchestratorDecision(
        action=action,
        reply=(decision.get("reply") or "").strip() or "Got it.",
        agent_name=agent_name if action == "delegate" else None,
        deliverable_title=(decision.get("deliverable_title") or "Draft").strip(),
        reason=(decision.get("reason") or "").strip(),
        thought_process=thought,
        memory_writes=memory_writes,
    )


async def record_memory_writes(
    db, client_id: str, memory_writes: list[dict], source: str
) -> None:
    """Persist orchestrator-detected durable facts as semantic memory."""
    for entry in memory_writes:
        try:
            await write_memory(
                db,
                client_id,
                content=entry["content"].strip(),
                kind=entry.get("kind", "fact"),
                source=source,
                created_by="orchestrator",
            )
        except Exception:
            logger.warning("orchestrator memory write failed", exc_info=True)
