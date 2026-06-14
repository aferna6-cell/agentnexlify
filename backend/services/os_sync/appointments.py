"""Agent OS sync: appointments — incremental pull from ``appointments`` into
semantic memory.

Reads the tenant's appointment rows updated since ``last_seen_cursor`` (ISO
timestamp on ``appointments.updated_at``), renders a compact summary for
each, and upserts into ``os_memory_entries`` with
``source_ref='appointments:<id>'``.

Schema note: ``appointments.tenant_id`` is the correct column (NOT
client_id) per the schema-discipline rule. ``tenant_table`` handles that
mapping internally because ``client_id`` and ``tenant_id`` resolve to the
same value here.
"""

import logging

from backend.services.embeddings import embed_text
from backend.services.os_sync.base import SyncContext, SyncResult, SyncSpec, now_iso
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_BATCH_SIZE = 200


def _summarize_appointment(row: dict) -> str:
    parts: list[str] = []
    name = (row.get("customer_name") or "").strip() or "Unnamed customer"
    parts.append(f"Appointment for {name}")
    service = row.get("service_type")
    if service:
        parts.append(f"service={service}")
    start_time = row.get("start_time")
    if start_time:
        parts.append(f"start={start_time}")
    status = row.get("status")
    if status:
        parts.append(f"status={status}")
    email = row.get("customer_email")
    if email:
        parts.append(f"email={email}")
    phone = row.get("customer_phone")
    if phone:
        parts.append(f"phone={phone}")
    notes = (row.get("notes") or "").strip()
    if notes:
        parts.append("notes: " + notes[:280])
    return ". ".join(parts)


async def _upsert_memory(db, client_id: str, row: dict) -> None:
    source_ref = f"appointments:{row['id']}"
    content = _summarize_appointment(row)
    try:
        embedding = await embed_text(content)
    except Exception:
        logger.warning(
            "os_sync.appointments: embed failed client_id=%s appt_id=%s",
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
            "source": "sync:appointments",
            "source_ref": source_ref,
        }
    ).execute()


async def _run(ctx: SyncContext) -> SyncResult:
    client_id = ctx.client_id
    db = ctx.db

    builder = (
        tenant_table(db, "appointments", client_id)
        .select(
            "id, customer_name, customer_email, customer_phone, start_time, "
            "end_time, status, service_type, notes, updated_at"
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
        logger.exception("os_sync.appointments: query failed client_id=%s", client_id)
        return SyncResult(status="error", error_detail=str(e)[:300])

    rows = result.data or []
    if not rows:
        return SyncResult(status="ok", rows_seen=0, new_cursor=cursor)

    max_cursor = cursor
    for row in rows:
        try:
            await _upsert_memory(db, client_id, row)
        except Exception:
            logger.exception(
                "os_sync.appointments: upsert failed client_id=%s appt_id=%s",
                client_id,
                row.get("id"),
            )
            continue
        updated_at = row.get("updated_at")
        if updated_at and (max_cursor is None or updated_at > max_cursor):
            max_cursor = updated_at

    return SyncResult(status="ok", rows_seen=len(rows), new_cursor=max_cursor)


SPEC = SyncSpec(
    name="appointments",
    run=_run,
    description="Pull updated appointments into semantic memory, dedup by appt id.",
    required_connectors=[],
)
