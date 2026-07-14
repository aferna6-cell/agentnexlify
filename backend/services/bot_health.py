"""Per-tenant Bot-Health evals (opportunity #R4) — retention lever.

Scores each tenant's chat-widget bot quality on recent conversations using an
LLM-as-judge, so the dashboard can show a "Bot Health" score and alert when a
bot is degrading. One Haiku call per tenant per run — cheap, high-volume
judging, per the #R7 cost-floor discipline in .claude/rules/model-routing.md.

Two entrypoints:
  - ``score_tenant_bot_health(tenant_id, window_days=7)`` — reconstructs that
    tenant's recent chat_messages into conversations, judges the whole batch
    in one Claude call, aggregates the results, and inserts one row into
    ``bot_health_scores`` (migration 170). Returns the inserted row, or
    ``None`` when the tenant has no recent activity (or the judge call/parse
    fails — logged either way, never raised into the caller).
  - ``score_all_tenants(window_days=7)`` — iterates every tenant and calls
    ``score_tenant_bot_health`` for each. Tenants with no recent chat_messages
    activity come back ``None`` from the per-tenant call and are counted as
    skipped, so no separate DISTINCT query over chat_messages is needed —
    same iterate-all-tenants shape as ``backend/services/churn_watch.py``.

chat_messages uses tenant_id (migration 006), and bot_health_scores is a
per-tenant AGGREGATE table (not leads/conversations), so it also uses
tenant_id — NOT client_id. See .claude/rules/schema-discipline.md.

Health score formula (documented, not tunable at runtime):
  health_score = 100 * (
      0.50 * resolution_rate               # fraction of judged conversations resolved
    + 0.25 * (1 - hallucination_rate)      # hallucination_flag_count / sample_size
    + 0.15 * (1 - unresolved_rate)         # unresolved_intent_count / sample_size
    + 0.10 * normalized_sentiment          # (avg_sentiment + 1) / 2, sentiment in [-1, 1]
  )
Weights: resolution 50%, low-hallucination 25%, low-unresolved-intent 15%,
positive sentiment 10%. Resolution and hallucination avoidance are weighted
highest because they are the two failure modes most likely to churn a
tenant — a bot that doesn't resolve questions or invents answers is actively
harmful, whereas sentiment is a softer signal.
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_JUDGE_MODEL = "claude-haiku-4-5-20251001"

# Caps keep the judge call bounded for busy tenants — a 7-day window on a
# high-volume widget could otherwise mean hundreds of conversations in one
# prompt. sample_size in the stored row reflects the (possibly capped) set
# actually judged, so the math stays internally consistent.
_MAX_CONVERSATIONS = 25
_MAX_MESSAGES_PER_CONVERSATION = 20
_MAX_CONTENT_CHARS = 600  # per-message truncation inside the transcript

_JUDGE_SYSTEM_PROMPT = (
    "You are a strict QA judge for an AI customer-support chat widget. You "
    "will be given a numbered list of conversations, each a transcript of "
    "User/Assistant turns. For EACH conversation, judge the assistant's "
    "performance and return a JSON array with exactly one object per "
    "conversation, in the same order they were given. Each object must have "
    "exactly these keys:\n"
    '  "resolved": true if the assistant answered the user\'s question or '
    "completed their request by the end of the transcript, false otherwise.\n"
    '  "hallucination_risk": true if the assistant stated something as fact '
    "that it could not have known (invented pricing, invented policies, "
    "invented availability) or contradicted itself, false otherwise.\n"
    '  "unresolved_intent": true if the user\'s stated goal (booking, '
    "question, complaint) was never addressed or the conversation ended with "
    "the user still stuck, false otherwise.\n"
    '  "sentiment": a number from -1.0 (very negative) to 1.0 (very positive) '
    "reflecting the user's apparent satisfaction by the end of the "
    "conversation.\n"
    "Return ONLY the JSON array. No prose, no markdown fences, no "
    "explanation."
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _fence_strip(raw: str) -> str:
    """Strip a ```json ... ``` fence if the model added one despite instructions."""
    text = (raw or "").strip()
    fence = re.match(r"^```(?:json)?\s*(.+?)\s*```$", text, re.DOTALL)
    return fence.group(1).strip() if fence else text


def _parse_judge_json(raw: str, expected_count: int) -> list[dict[str, Any]] | None:
    """Parse the judge response into a list of per-conversation verdicts.

    Returns None (not []) when the response is unusable or doesn't match
    expected_count — the caller treats that as a failed judge run.
    """
    text = _fence_strip(raw)
    if not text:
        return None
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, list) or len(parsed) != expected_count:
        return None
    if not all(isinstance(item, dict) for item in parsed):
        return None
    return parsed


def _reconstruct_conversations(messages: list[dict[str, Any]]) -> list[list[dict[str, str]]]:
    """Group chat_messages rows (already ordered by created_at) by session_id,
    preserving first-seen session order. Caps conversation count + turns per
    conversation per the module-level limits.
    """
    by_session: dict[str, list[dict[str, str]]] = {}
    order: list[str] = []
    for msg in messages:
        session_id = msg.get("session_id") or ""
        if not session_id:
            continue
        if session_id not in by_session:
            if len(order) >= _MAX_CONVERSATIONS:
                continue
            by_session[session_id] = []
            order.append(session_id)
        turns = by_session[session_id]
        if len(turns) >= _MAX_MESSAGES_PER_CONVERSATION:
            continue
        role = msg.get("role") or "user"
        content = (msg.get("content") or "")[:_MAX_CONTENT_CHARS]
        turns.append({"role": role, "content": content})
    return [by_session[sid] for sid in order if by_session[sid]]


def _format_transcript(conversations: list[list[dict[str, str]]]) -> str:
    blocks = []
    for idx, turns in enumerate(conversations, start=1):
        lines = [f"Conversation {idx}:"]
        for turn in turns:
            speaker = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{speaker}: {turn['content']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _clamp_sentiment(value: Any) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(-1.0, min(1.0, num))


def _compute_health_score(
    *,
    resolution_rate: float,
    hallucination_rate: float,
    unresolved_rate: float,
    avg_sentiment: float,
) -> float:
    """See module docstring for the weighted formula this implements."""
    normalized_sentiment = (avg_sentiment + 1.0) / 2.0
    score = 100.0 * (
        0.50 * resolution_rate
        + 0.25 * (1.0 - hallucination_rate)
        + 0.15 * (1.0 - unresolved_rate)
        + 0.10 * normalized_sentiment
    )
    return round(max(0.0, min(100.0, score)), 1)


async def score_tenant_bot_health(tenant_id: str, window_days: int = 7) -> dict[str, Any] | None:
    """Score one tenant's bot quality on its recent chat_messages.

    Returns the inserted bot_health_scores row, or None when the tenant has
    no recent messages (nothing to score) or the judge call/parse fails.
    Never raises — every failure is logged and treated as a skip.
    """
    db = get_service_supabase()
    since = (_now_utc() - timedelta(days=window_days)).isoformat()

    try:
        result = (
            db.table("chat_messages")
            .select("session_id, role, content, created_at")
            .eq("tenant_id", tenant_id)
            .gte("created_at", since)
            .order("created_at")
            .execute()
        )
        messages = result.data or []
    except Exception:
        logger.error(
            "bot_health: chat_messages query failed tenant=%s", tenant_id, exc_info=True
        )
        return None

    if not messages:
        logger.info("bot_health: no recent messages tenant=%s window_days=%d", tenant_id, window_days)
        return None

    conversations = _reconstruct_conversations(messages)
    if not conversations:
        logger.info(
            "bot_health: no usable conversations after reconstruction tenant=%s", tenant_id
        )
        return None

    sample_size = len(conversations)
    transcript = _format_transcript(conversations)

    try:
        judge_result = await call_claude_messages(
            operation="bot_health.judge",
            model=_JUDGE_MODEL,
            max_tokens=2000,
            temperature=0.0,
            timeout=45.0,
            system=_JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": transcript}],
            metadata={"tenant_id": tenant_id, "conversation_count": sample_size},
        )
    except Exception:
        logger.error("bot_health: judge call failed tenant=%s", tenant_id, exc_info=True)
        return None

    verdicts = _parse_judge_json(judge_result.text, sample_size)
    if verdicts is None:
        logger.error(
            "bot_health: judge response unparseable or count mismatch tenant=%s sample_size=%d",
            tenant_id,
            sample_size,
        )
        return None

    resolved_count = sum(1 for v in verdicts if v.get("resolved") is True)
    hallucination_flag_count = sum(1 for v in verdicts if v.get("hallucination_risk") is True)
    unresolved_intent_count = sum(1 for v in verdicts if v.get("unresolved_intent") is True)
    sentiments = [_clamp_sentiment(v.get("sentiment")) for v in verdicts]
    avg_sentiment = round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0

    resolution_rate = round(resolved_count / sample_size, 3)
    hallucination_rate = hallucination_flag_count / sample_size
    unresolved_rate = unresolved_intent_count / sample_size

    health_score = _compute_health_score(
        resolution_rate=resolution_rate,
        hallucination_rate=hallucination_rate,
        unresolved_rate=unresolved_rate,
        avg_sentiment=avg_sentiment,
    )

    row = {
        "window_days": window_days,
        "sample_size": sample_size,
        "resolution_rate": resolution_rate,
        "hallucination_flag_count": hallucination_flag_count,
        "unresolved_intent_count": unresolved_intent_count,
        "avg_sentiment": avg_sentiment,
        "health_score": health_score,
        "details": {"per_conversation": verdicts},
    }

    try:
        inserted = tenant_table(db, "bot_health_scores", tenant_id).insert(row).execute()
    except Exception:
        logger.error("bot_health: insert failed tenant=%s", tenant_id, exc_info=True)
        return None

    result_row = inserted.data[0] if inserted.data else None
    if result_row:
        logger.info(
            "bot_health: scored tenant=%s health_score=%s sample_size=%d",
            tenant_id,
            health_score,
            sample_size,
        )
    return result_row


async def score_all_tenants(window_days: int = 7) -> dict[str, int]:
    """Score every tenant with recent chat activity. Never raises.

    Iterates all tenants and delegates to score_tenant_bot_health, which
    returns None (skip) for tenants with no recent chat_messages activity —
    so no separate DISTINCT query over chat_messages is needed here.
    """
    db = get_service_supabase()
    try:
        result = db.table("tenants").select("id").execute()
        tenant_rows = result.data or []
    except Exception:
        logger.error("bot_health: failed to fetch tenants", exc_info=True)
        return {"scored": 0, "skipped": 0}

    scored = 0
    skipped = 0
    for row in tenant_rows:
        tenant_id = row.get("id")
        if not tenant_id:
            continue
        try:
            scored_row = await score_tenant_bot_health(tenant_id, window_days=window_days)
        except Exception:
            # score_tenant_bot_health already catches its own failures; this
            # is a last-resort guard so one bad tenant never aborts the batch.
            logger.error(
                "bot_health: unexpected failure scoring tenant=%s", tenant_id, exc_info=True
            )
            scored_row = None
        if scored_row:
            scored += 1
        else:
            skipped += 1

    logger.info("bot_health: run complete scored=%d skipped=%d", scored, skipped)
    return {"scored": scored, "skipped": skipped}
