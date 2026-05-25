"""Agent OS sync: conversations — summarize widget chat sessions into memory.

Pulls recent ``chat_messages`` rows newer than ``last_seen_cursor`` (ISO
timestamp on ``chat_messages.created_at``), groups by ``session_id``, asks
Haiku to render a 2-3 sentence summary per session, and upserts one
``os_memory_entries`` row per session keyed by
``source_ref='chat_session:<session_id>'``.

Schema note: ``chat_messages.tenant_id`` is the correct column (NOT
client_id) — separate from leads/conversations which use ``client_id``.
``tenant_table`` handles the mapping; client_id == tenant_id here.
"""

import logging

from backend.services.embeddings import embed_text
from backend.services.llm_runtime import call_claude_messages
from backend.services.os_sync.base import SyncContext, SyncResult, SyncSpec, now_iso
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_MAX_MESSAGES = 600
_MAX_MSG_CHARS = 600
_MAX_SUMMARY_INPUT_CHARS = 8000

_SUMMARY_SYSTEM = """\
You summarize a customer chat session for a small business owner's memory.
Return a single short paragraph (2-3 sentences, <= 400 chars):
- What the customer asked or needed
- Any concrete commitment, appointment, or contact info exchanged
- Outstanding action for the owner, if any

No preamble. No quotes. Just the summary text.\
"""


def _fetch_messages(
    db, client_id: str, cursor: str | None, backfill: bool
) -> list[dict]:
    builder = (
        tenant_table(db, "chat_messages", client_id)
        .select("session_id, role, content, created_at")
        .order("created_at", desc=False)
        .limit(_MAX_MESSAGES)
    )
    if cursor and not backfill:
        builder = builder.gt("created_at", cursor)
    result = builder.execute()
    return result.data or []


def _group_by_session(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        sid = row.get("session_id")
        if not sid:
            continue
        grouped.setdefault(sid, []).append(row)
    return grouped


def _render_transcript(messages: list[dict]) -> str:
    pieces: list[str] = []
    used = 0
    for msg in messages:
        role = (msg.get("role") or "user").strip()
        content = (msg.get("content") or "").strip().replace("\n", " ")
        if not content:
            continue
        line = f"{role}: {content[:_MAX_MSG_CHARS]}"
        if used + len(line) + 1 > _MAX_SUMMARY_INPUT_CHARS:
            break
        pieces.append(line)
        used += len(line) + 1
    return "\n".join(pieces)


async def _summarize_session(client_id: str, transcript: str) -> str:
    response = await call_claude_messages(
        operation="os_sync_conversations_summarize",
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=_SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": f"Transcript:\n\n{transcript}"}],
        metadata={"client_id": client_id},
    )
    return (response.text or "").strip()


async def _upsert_session_memory(
    db, client_id: str, session_id: str, summary: str
) -> None:
    source_ref = f"chat_session:{session_id}"
    try:
        embedding = await embed_text(summary)
    except Exception:
        logger.warning(
            "os_sync.conversations: embed failed client_id=%s session_id=%s",
            client_id,
            session_id,
            exc_info=True,
        )
        embedding = None

    existing = (
        tenant_table(db, "os_memory_entries", client_id)
        .select("id")
        .eq("source_ref", source_ref)
        .limit(1)
        .execute()
    )
    if existing.data:
        tenant_table(db, "os_memory_entries", client_id).update(
            {
                "content": summary,
                "embedding": embedding,
                "updated_at": now_iso(),
            }
        ).eq("id", existing.data[0]["id"]).execute()
        return

    tenant_table(db, "os_memory_entries", client_id).insert(
        {
            "kind": "conversation",
            "content": summary,
            "embedding": embedding,
            "source": "sync:conversations",
            "source_ref": source_ref,
        }
    ).execute()


async def _run(ctx: SyncContext) -> SyncResult:
    client_id = ctx.client_id
    db = ctx.db
    cursor = ctx.state_row.get("last_seen_cursor")

    try:
        rows = _fetch_messages(db, client_id, cursor, ctx.backfill)
    except Exception as e:
        logger.exception("os_sync.conversations: fetch failed client_id=%s", client_id)
        return SyncResult(status="error", error_detail=str(e)[:300])

    if not rows:
        return SyncResult(status="ok", rows_seen=0, new_cursor=cursor)

    grouped = _group_by_session(rows)
    max_cursor = cursor

    for session_id, messages in grouped.items():
        transcript = _render_transcript(messages)
        if not transcript:
            continue
        try:
            summary = await _summarize_session(client_id, transcript)
        except Exception:
            logger.warning(
                "os_sync.conversations: summarize failed client_id=%s session_id=%s",
                client_id,
                session_id,
                exc_info=True,
            )
            continue
        if not summary:
            continue
        try:
            await _upsert_session_memory(db, client_id, session_id, summary)
        except Exception:
            logger.exception(
                "os_sync.conversations: upsert failed client_id=%s session_id=%s",
                client_id,
                session_id,
            )
            continue
        for msg in messages:
            ts = msg.get("created_at")
            if ts and (max_cursor is None or ts > max_cursor):
                max_cursor = ts

    return SyncResult(status="ok", rows_seen=len(rows), new_cursor=max_cursor)


SPEC = SyncSpec(
    name="conversations",
    run=_run,
    description=(
        "Summarize recent widget chat sessions into semantic memory, "
        "one memory row per session_id."
    ),
    required_connectors=[],
)
