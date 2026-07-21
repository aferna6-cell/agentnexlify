"""Deep research v1 (round-3 item 3 - the research pillar).

Quick Suite and Gemini Enterprise headline research agents; this is the
smallest honest version for a small business: a research ask produces a
propose-only document deliverable synthesized ONLY from sources the tenant
already owns or connected - their knowledge base, FAQs, per-department
instructions, knowledge-graph memory, and owner-designated MCP context
tools. No live web crawl in v1, so provenance is exact: every brief ends
with the list of source kinds it drew from, and the model is instructed to
say what it could not answer rather than fill gaps.

The output is an os_agent_runs deliverable at pending_approval - research
briefs ride the same approval rails as every other artifact.
"""

import logging
from datetime import datetime, timezone

from backend.services import (
    os_custom_instructions,
    os_graph_memory,
    os_kb_feed,
    os_mcp_context,
)
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

MAX_TOPIC_LEN = 500
_MAX_SOURCE_CHARS = 12000
_RESEARCH_MODEL = "claude-sonnet-5"
_HANDOFF_BRIEF_CHARS = 1500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def gather_sources(db, client_id: str, topic: str) -> tuple[str, list[str]]:
    """(corpus, source_kinds) from everything the tenant already owns."""
    entries: list[dict] = []
    kinds: list[str] = []

    def _extend(new_entries: list[dict], kind: str) -> None:
        if new_entries:
            entries.extend(new_entries)
            kinds.append(kind)

    try:
        _extend(
            os_custom_instructions.kb_entries(db, client_id),
            "department instructions",
        )
    except Exception:
        logger.warning("os_research: instructions read failed", exc_info=True)
    try:
        _extend(
            os_kb_feed.tenant_kb_entries(db, client_id, None), "knowledge base"
        )
    except Exception:
        logger.warning("os_research: kb feed read failed", exc_info=True)
    try:
        _extend(
            await os_graph_memory.graph_kb_entries(db, client_id, topic),
            "learned memory",
        )
    except Exception:
        logger.warning("os_research: graph memory read failed", exc_info=True)
    try:
        _extend(
            await os_mcp_context.tool_context_entries(db, client_id),
            "connected tools (MCP)",
        )
    except Exception:
        logger.warning("os_research: mcp context read failed", exc_info=True)

    corpus = "\n\n".join(
        f"[{e.get('topic', 'note')}]\n{e.get('answer', '')}" for e in entries
    )[:_MAX_SOURCE_CHARS]
    return corpus, kinds


async def run_research(db, client_id: str, topic: str) -> dict:
    """Produce a propose-only research brief run. Raises ValueError on bad
    input; returns {"run": row} or {"error": ...} on synthesis failure."""
    topic = (topic or "").strip()[:MAX_TOPIC_LEN]
    if len(topic) < 10:
        raise ValueError("research topic too short")

    corpus, kinds = await gather_sources(db, client_id, topic)
    if not corpus.strip():
        return {
            "error": (
                "No owned sources to research from yet - add knowledge in "
                "Second Brain or connect a tool first."
            )
        }

    from backend.services.llm_runtime import call_claude_messages

    try:
        result = await call_claude_messages(
            operation="os_research_brief",
            model=_RESEARCH_MODEL,
            max_tokens=2000,
            temperature=None,
            system=(
                "You are a business research analyst. Write a concise research "
                "brief on the owner's topic using ONLY the provided sources. "
                "Structure: summary, key findings (bulleted, each traceable to "
                "a source), and open questions the sources cannot answer. When "
                "the sources do not cover something, say so plainly - never "
                "fill gaps from general knowledge."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Topic: {topic}\n\nSOURCES:\n{corpus}",
                }
            ],
            timeout=60.0,
            metadata={"client_id": client_id},
        )
        brief = (result.text or "").strip()
    except Exception as exc:
        logger.warning(
            "os_research: synthesis failed tenant=%s", client_id, exc_info=True
        )
        return {"error": f"research synthesis failed: {exc}"[:300]}

    footer = "\n\n---\nSources drawn from: " + (", ".join(kinds) or "none")
    run_row = {
        "agent_name": "research",
        "status": "succeeded",
        "deliverable": {
            "title": f"Research brief: {topic[:80]}",
            "body": brief + footer,
            "channel": "document",
            "metadata": {"source_kinds": kinds},
        },
        # Research briefs are documents for the owner - always parked at the
        # human gate, never auto-sent anywhere.
        "deliverable_status": "pending_approval",
        "completed_at": _now(),
        "thought_process": [
            {
                "step": "research_v1",
                "detail": f"Synthesized from owned sources: {', '.join(kinds)}",
            }
        ],
    }
    try:
        created = (
            tenant_table(db, "os_agent_runs", client_id).insert(run_row).execute()
        ).data[0]
    except Exception:
        logger.warning(
            "os_research: run persist failed tenant=%s", client_id, exc_info=True
        )
        return {"error": "could not save the research brief"}
    return {"run": created}


async def research_to_project(db, client_id: str, run_id: str) -> dict:
    """Seed a multi-department project from a research brief (round-4 item 4).

    The suite loop: deep research produces a brief, the owner clicks "Act on
    this brief", and the orchestration pillar turns it into an approvable
    plan. The project ask carries the topic plus the brief's first chunk so
    the planner grounds its steps in the findings. Raises ValueError on a
    missing/empty brief; plan_project enforces the active-project cap.
    """
    from backend.services.tenant_scope import tenant_select

    rows = (
        tenant_select(db, "os_agent_runs", client_id, "id, agent_name, deliverable")
        .eq("id", run_id)
        .limit(1)
        .execute()
    ).data or []
    if not rows or rows[0].get("agent_name") != "research":
        raise ValueError("research brief not found")
    deliverable = rows[0].get("deliverable") or {}
    if not isinstance(deliverable, dict):
        raise ValueError("research brief not found")
    title = str(deliverable.get("title") or "")
    body = str(deliverable.get("body") or "").strip()
    if not body:
        raise ValueError("research brief has no content")

    topic = title.removeprefix("Research brief: ").strip() or "the research topic"
    ask = (
        f"Act on this research brief about {topic}. Turn its findings into "
        "concrete department work.\n\nBrief:\n"
        f"{body[:_HANDOFF_BRIEF_CHARS]}"
    )

    from backend.services.os_projects import MAX_ASK_LEN, plan_project

    return await plan_project(db, client_id, ask[:MAX_ASK_LEN])
