"""Per-conversation sentiment + intent classification (off the hot path).

The widget stores chat turns in ``chat_messages`` (tenant_id-scoped) and one
summary row per session in ``conversations`` (client_id-scoped). This service
reads a conversation's transcript, asks Haiku for a single sentiment label plus
a short intent phrase, and writes them back onto the ``conversations`` row.

Design notes:
- Runs off the user hot path (conversation close / batch job), never inside the
  per-message chat request, so a slow or failed classification never delays a
  widget reply.
- Sentiment vocabulary mirrors the calls table exactly: positive, neutral,
  negative. Anything else falls back to None rather than a fabricated label.
- Every external step degrades gracefully: an LLM error, malformed JSON, or a
  Supabase write failure leaves the columns NULL and is logged, never raised.
- ``client_id`` is always the JWT tenant id, the same value used for the
  tenant_id-scoped chat_messages read. chat_messages uses tenant_id; the
  conversations write uses client_id (handled by the tenant_scope helpers).
"""

import json
import logging
import re
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages
from backend.services.tenant_scope import tenant_select, tenant_update

logger = logging.getLogger(__name__)

CLASSIFY_MODEL = "claude-haiku-4-5-20251001"

# Sentiment labels accepted on the conversations row (mirror of calls table).
VALID_SENTIMENTS = ("positive", "neutral", "negative")

# Caps so one classification call stays small and cheap.
_MAX_TURNS = 40
_MAX_TURN_CHARS = 600
_MAX_INTENT_CHARS = 80
_MAX_OUTPUT_TOKENS = 120

_CLASSIFY_SYSTEM = (
    "You classify one customer support chat between a small-business AI front "
    "desk and a customer. Return ONLY a JSON object, no prose, shaped exactly "
    'like: {"sentiment": "neutral", "intent": "booking request"}. '
    "Rules: sentiment must be one of positive, neutral, negative and reflects "
    "the customer's overall tone across the chat. intent is a short noun phrase "
    "(two to four words) naming what the customer wanted, like booking request, "
    "pricing question, complaint, or hours question. Use lower case for intent. "
    "When the chat is empty or unreadable, return "
    '{"sentiment": "neutral", "intent": "unknown"}.'
)


def build_transcript(messages: list[dict[str, Any]]) -> str:
    """Render ordered chat_messages rows into a compact transcript string.

    Rows are expected oldest-first. Each turn is truncated and the whole list is
    capped so the prompt stays small. Empty content rows are skipped.
    """
    lines: list[str] = []
    for row in messages[:_MAX_TURNS]:
        role = (row.get("role") or "").strip().lower()
        content = (row.get("content") or "").strip()
        if not content:
            continue
        speaker = "Customer" if role == "user" else "Assistant"
        lines.append(f"{speaker}: {content[:_MAX_TURN_CHARS]}")
    return "\n".join(lines)


def parse_classification(text: str) -> dict[str, Any]:
    """Parse the model JSON into {'sentiment': str|None, 'intent': str|None}.

    Tolerates code fences and surrounding prose. Returns null values (not a
    fabricated label) whenever parsing fails or the sentiment is off-vocabulary.
    """
    result: dict[str, Any] = {"sentiment": None, "intent": None}
    if not text or not text.strip():
        return result

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        logger.warning("conversation_enrichment: no JSON object in classifier output")
        return result

    try:
        parsed = json.loads(match.group())
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("conversation_enrichment: classifier JSON parse failed: %s", exc)
        return result

    if not isinstance(parsed, dict):
        return result

    raw_sentiment = str(parsed.get("sentiment", "")).strip().lower()
    if raw_sentiment in VALID_SENTIMENTS:
        result["sentiment"] = raw_sentiment

    raw_intent = parsed.get("intent")
    if isinstance(raw_intent, str):
        intent = raw_intent.strip().lower()[:_MAX_INTENT_CHARS]
        if intent and intent != "unknown":
            result["intent"] = intent

    return result


def _load_transcript(db: Any, client_id: str, session_id: str) -> str:
    """Read a session's chat turns (tenant_id-scoped) oldest-first."""
    resp = (
        tenant_select(db, "chat_messages", client_id, "role, content, created_at")
        .eq("session_id", session_id)
        .order("created_at")
        .limit(_MAX_TURNS)
        .execute()
    )
    rows = getattr(resp, "data", None) or []
    return build_transcript(rows)


async def _classify_transcript(transcript: str, *, client_id: str, session_id: str) -> dict[str, Any]:
    """Ask Haiku for {sentiment, intent}; null values on any failure."""
    if not transcript.strip():
        return {"sentiment": None, "intent": None}

    try:
        result = await call_claude_messages(
            operation="conversation.classify_sentiment_intent",
            model=CLASSIFY_MODEL,
            max_tokens=_MAX_OUTPUT_TOKENS,
            messages=[{"role": "user", "content": transcript}],
            system=_CLASSIFY_SYSTEM,
            temperature=0.0,
            timeout=20.0,
            metadata={
                "client_id": client_id,
                "session_id": session_id,
                "transcript_chars": len(transcript),
            },
        )
    except Exception:
        logger.warning(
            "conversation_enrichment: classify call failed session=%s", session_id, exc_info=True
        )
        return {"sentiment": None, "intent": None}

    return parse_classification(result.text)


def _persist(db: Any, client_id: str, session_id: str, values: dict[str, Any]) -> bool:
    """Write sentiment/intent onto the conversations row (client_id-scoped)."""
    try:
        tenant_update(db, "conversations", client_id, values).eq(
            "session_id", session_id
        ).execute()
        return True
    except Exception:
        logger.warning(
            "conversation_enrichment: persist failed session=%s", session_id, exc_info=True
        )
        return False


async def enrich_conversation(client_id: str, session_id: str, db: Any | None = None) -> dict[str, Any]:
    """Classify one conversation and store sentiment + intent.

    Returns the stored {'sentiment': str|None, 'intent': str|None}. Safe to call
    off the hot path (conversation close, batch job): all failures degrade to
    null values and are logged, never raised.
    """
    if not client_id or not session_id:
        logger.warning("conversation_enrichment: missing client_id/session_id")
        return {"sentiment": None, "intent": None}

    db = db or get_service_supabase()

    try:
        transcript = _load_transcript(db, client_id, session_id)
    except Exception:
        logger.warning(
            "conversation_enrichment: transcript load failed session=%s", session_id, exc_info=True
        )
        return {"sentiment": None, "intent": None}

    classification = await _classify_transcript(
        transcript, client_id=client_id, session_id=session_id
    )

    # Only write columns we actually resolved, so a partial classification never
    # clobbers an earlier good value with NULL.
    values = {k: v for k, v in classification.items() if v is not None}
    if values:
        _persist(db, client_id, session_id, values)

    return classification
