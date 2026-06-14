"""Agent OS sync: leads — incremental pull from ``leads`` into semantic memory.

Reads the tenant's ``leads`` rows updated since ``last_seen_cursor`` (ISO
timestamp on ``leads.updated_at``), renders a short text summary for each,
and upserts into ``os_memory_entries`` with ``source_ref='leads:<id>'``.

Dedup: the partial unique index on ``(client_id, source_ref) WHERE
source_ref IS NOT NULL`` (migration 127) enforces one memory row per lead;
re-syncs update the existing row's content + embedding in place.

Cursor: max ``updated_at`` across this batch. Next run picks up from that
value. ``backfill=True`` ignores the cursor and pulls every lead.
"""

import logging

from backend.services.embeddings import embed_text
from backend.services.os_sync.base import SyncContext, SyncResult, SyncSpec, now_iso
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_BATCH_SIZE = 200


def _summarize_lead(row: dict) -> str:
    """Short, embeddable text for memory. Owner-readable, no PII beyond name."""
    parts: list[str] = []
    name = (row.get("name") or "").strip() or "Unnamed lead"
    parts.append(f"Lead: {name}")
    status = row.get("status")
    if status:
        parts.append(f"status={status}")
    temp = row.get("lead_temperature")
    if temp:
        parts.append(f"temperature={temp}")
    score = row.get("lead_score")
    if score is not None:
        parts.append(f"score={score}")
    areas = row.get("areas_of_interest")
    if areas:
        if isinstance(areas, list):
            parts.append("interest=" + ", ".join(str(a) for a in areas))
        else:
            parts.append(f"interest={areas}")
    deal = row.get("deal_value")
    if deal:
        parts.append(f"deal_value={deal}")
    notes = (row.get("notes") or "").strip()
    if notes:
        parts.append("notes: " + notes[:280])
    return ". ".join(parts)


async def _upsert_memory_for_lead(db, client_id: str, row: dict) -> None:
    source_ref = f"leads:{row['id']}"
    content = _summarize_lead(row)
    try:
        embedding = await embed_text(content)
    except Exception:
        logger.warning(
            "os_sync.leads: embed failed client_id=%s lead_id=%s",
            client_id,
            row.get("id"),
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
                "content": content,
                "embedding": embedding,
                "updated_at": now_iso(),
            }
        ).eq("id", existing.data[0]["id"]).execute()
        return

    tenant_table(db, "os_memory_entries", client_id).insert(
        {
            "kind": "fact",
            "content": content,
            "embedding": embedding,
            "source": "sync:leads",
            "source_ref": source_ref,
        }
    ).execute()


async def _run(ctx: SyncContext) -> SyncResult:
    client_id = ctx.client_id
    db = ctx.db

    builder = (
        tenant_table(db, "leads", client_id)
        .select(
            "id, name, email, phone, status, lead_score, lead_temperature, "
            "areas_of_interest, deal_value, notes, updated_at"
        )
        .order("updated_at", desc=False)
        .limit(_BATCH_SIZE)
    )
    cursor = ctx.state_row.get("last_seen_cursor")
    if cursor and not ctx.backfill:
        builder = builder.gt("updated_at", cursor)

    try:
        result = builder.execute()
    except Exception as e:
        logger.exception("os_sync.leads: leads query failed client_id=%s", client_id)
        return SyncResult(status="error", error_detail=str(e)[:300])

    rows = result.data or []
    if not rows:
        return SyncResult(status="ok", rows_seen=0, new_cursor=cursor)

    max_cursor = cursor
    for row in rows:
        try:
            await _upsert_memory_for_lead(db, client_id, row)
        except Exception:
            logger.exception(
                "os_sync.leads: upsert failed client_id=%s lead_id=%s",
                client_id,
                row.get("id"),
            )
            continue
        updated_at = row.get("updated_at")
        if updated_at and (max_cursor is None or updated_at > max_cursor):
            max_cursor = updated_at

    return SyncResult(status="ok", rows_seen=len(rows), new_cursor=max_cursor)


SPEC = SyncSpec(
    name="leads",
    run=_run,
    description="Pull updated leads into semantic memory, dedup by lead id.",
    required_connectors=[],
)
