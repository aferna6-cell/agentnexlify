"""Read-only data tools workers use to ground drafts in real tenant data.

A worker run gets a ``WorkerTools`` handle on ``WorkerContext.tools``. Every
method is tenant-scoped via ``client_id`` (or the canonical ``tenant_id``
column for ``appointments`` / ``chat_messages``) through ``tenant_scope``
helpers — no raw SQL, no cross-tenant reads. Methods return plain dicts the
worker passes into its Claude prompt. Writes are NOT here — those are
approval-gated through action connectors (Group B).

Spec: ``specs/agent-os-worker-tools_spec.md``. Build order: tools first,
then wire into ``WorkerContext``, then rewrite workers one at a time.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.services.os_memory import search_memory as _search_memory
from backend.services.tenant_scope import tenant_select, tenant_table

logger = logging.getLogger(__name__)

HARD_LIMIT = 1000
DEFAULT_LEAD_LIMIT = 50
DEFAULT_CONVO_LIMIT = 20
DEFAULT_MESSAGE_LIMIT = 50
DEFAULT_APPT_LIMIT = 100

_LEAD_COLUMNS = (
    "id, name, email, phone, status, source, areas_of_interest, "
    "conversation_summary, created_at, updated_at"
)
_CONVO_COLUMNS = (
    "id, session_id, customer_name, customer_email, is_read, "
    "needs_handoff, created_at, updated_at"
)
_MESSAGE_COLUMNS = "id, role, content, created_at"
_APPT_COLUMNS = (
    "id, customer_name, customer_email, customer_phone, start_time, end_time, "
    "status, service_type, notes"
)
_TENANT_COLUMNS = (
    "id, business_name, business_type, plan, owner_email, owner_name, "
    "notification_phone, business_phone, timezone, business_hours, "
    "services_offered, city, website_url"
)


def _clamp_limit(limit: int, default: int) -> int:
    """Coerce a worker-supplied limit into ``[1, HARD_LIMIT]``."""
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return default
    if n < 1:
        return default
    return min(n, HARD_LIMIT)


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=max(0, int(days)))).isoformat()


@dataclass(frozen=True)
class WorkerTools:
    """Read-only data access scoped to one tenant for one worker run.

    Constructed in ``run_worker`` with a service-role ``db`` handle and the
    immutable ``client_id``. Frozen so a buggy worker cannot swap the scope
    mid-run.
    """

    db: Any
    client_id: str

    async def recent_leads(
        self,
        *,
        days: int = 30,
        status: str | None = None,
        limit: int = DEFAULT_LEAD_LIMIT,
    ) -> list[dict]:
        """Leads created in the last ``days``. Optional ``status`` filter."""
        capped = _clamp_limit(limit, DEFAULT_LEAD_LIMIT)
        cutoff = _iso_days_ago(days)

        def _run() -> list[dict]:
            query = (
                tenant_select(self.db, "leads", self.client_id, _LEAD_COLUMNS)
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(capped)
            )
            if status:
                query = query.eq("status", status)
            result = query.execute()
            return list(result.data or [])

        try:
            return await asyncio.to_thread(_run)
        except Exception:
            logger.warning(
                "WorkerTools.recent_leads failed client_id=%s",
                self.client_id,
                exc_info=True,
            )
            return []

    async def lead_by_id(self, lead_id: str) -> dict | None:
        """Single lead by id, or ``None`` if missing / cross-tenant."""
        if not lead_id:
            return None

        def _run() -> dict | None:
            result = (
                tenant_select(self.db, "leads", self.client_id, _LEAD_COLUMNS)
                .eq("id", lead_id)
                .limit(1)
                .execute()
            )
            data = result.data or []
            return dict(data[0]) if data else None

        try:
            return await asyncio.to_thread(_run)
        except Exception:
            logger.warning(
                "WorkerTools.lead_by_id failed client_id=%s id=%s",
                self.client_id,
                lead_id,
                exc_info=True,
            )
            return None

    async def stale_leads(
        self,
        *,
        days_since_last_touch: int = 14,
        limit: int = DEFAULT_LEAD_LIMIT,
    ) -> list[dict]:
        """Leads whose ``updated_at`` is older than ``days_since_last_touch``."""
        capped = _clamp_limit(limit, DEFAULT_LEAD_LIMIT)
        cutoff = _iso_days_ago(days_since_last_touch)

        def _run() -> list[dict]:
            result = (
                tenant_select(self.db, "leads", self.client_id, _LEAD_COLUMNS)
                .lte("updated_at", cutoff)
                .neq("status", "closed")
                .neq("status", "unsubscribed")
                .order("updated_at", desc=False)
                .limit(capped)
                .execute()
            )
            return list(result.data or [])

        try:
            return await asyncio.to_thread(_run)
        except Exception:
            logger.warning(
                "WorkerTools.stale_leads failed client_id=%s",
                self.client_id,
                exc_info=True,
            )
            return []

    async def widget_conversation(
        self,
        session_id: str,
        *,
        message_limit: int = DEFAULT_MESSAGE_LIMIT,
    ) -> dict | None:
        """One widget conversation by ``session_id`` plus its recent messages.

        Returns ``{"conversation": {...}, "messages": [...]}`` or ``None`` if
        the conversation does not exist for this tenant.
        """
        if not session_id:
            return None
        cap = _clamp_limit(message_limit, DEFAULT_MESSAGE_LIMIT)

        def _run() -> dict | None:
            convo = (
                tenant_select(self.db, "conversations", self.client_id, _CONVO_COLUMNS)
                .eq("session_id", session_id)
                .limit(1)
                .execute()
            )
            rows = convo.data or []
            if not rows:
                return None
            messages = (
                tenant_select(
                    self.db,
                    "chat_messages",
                    self.client_id,
                    _MESSAGE_COLUMNS,
                )
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(cap)
                .execute()
            )
            msg_rows = list(messages.data or [])
            msg_rows.reverse()  # chronological order for prompt context
            return {"conversation": dict(rows[0]), "messages": msg_rows}

        try:
            return await asyncio.to_thread(_run)
        except Exception:
            logger.warning(
                "WorkerTools.widget_conversation failed client_id=%s session_id=%s",
                self.client_id,
                session_id,
                exc_info=True,
            )
            return None

    async def recent_widget_conversations(
        self,
        *,
        days: int = 7,
        limit: int = DEFAULT_CONVO_LIMIT,
    ) -> list[dict]:
        """Widget conversations whose ``updated_at`` falls in the last ``days``."""
        cap = _clamp_limit(limit, DEFAULT_CONVO_LIMIT)
        cutoff = _iso_days_ago(days)

        def _run() -> list[dict]:
            result = (
                tenant_select(
                    self.db,
                    "conversations",
                    self.client_id,
                    _CONVO_COLUMNS,
                )
                .gte("updated_at", cutoff)
                .order("updated_at", desc=True)
                .limit(cap)
                .execute()
            )
            return list(result.data or [])

        try:
            return await asyncio.to_thread(_run)
        except Exception:
            logger.warning(
                "WorkerTools.recent_widget_conversations failed client_id=%s",
                self.client_id,
                exc_info=True,
            )
            return []

    async def appointments_between(
        self,
        *,
        start: str,
        end: str,
        limit: int = DEFAULT_APPT_LIMIT,
    ) -> list[dict]:
        """Appointments with ``start_time`` between two ISO timestamps."""
        cap = _clamp_limit(limit, DEFAULT_APPT_LIMIT)

        def _run() -> list[dict]:
            result = (
                tenant_select(
                    self.db,
                    "appointments",
                    self.client_id,
                    _APPT_COLUMNS,
                )
                .gte("start_time", start)
                .lte("start_time", end)
                .order("start_time", desc=False)
                .limit(cap)
                .execute()
            )
            return list(result.data or [])

        try:
            return await asyncio.to_thread(_run)
        except Exception:
            logger.warning(
                "WorkerTools.appointments_between failed client_id=%s",
                self.client_id,
                exc_info=True,
            )
            return []

    async def tenant_profile(self) -> dict:
        """Owner-side tenant profile + widget KB blob, merged into one dict.

        Joins ``tenants`` (business name, hours, plan, owner contact) with
        ``widget_configs.knowledge_base`` so a worker has the same context the
        widget chat agent has — without two round trips at the call site.
        """

        def _run() -> dict:
            tenant_row: dict = {}
            try:
                tenant_resp = (
                    self.db.table("tenants")
                    .select(_TENANT_COLUMNS)
                    .eq("id", self.client_id)
                    .limit(1)
                    .execute()
                )
                if tenant_resp.data:
                    tenant_row = dict(tenant_resp.data[0])
            except Exception:
                logger.warning(
                    "WorkerTools.tenant_profile tenants read failed client_id=%s",
                    self.client_id,
                    exc_info=True,
                )

            knowledge_base = ""
            custom_instructions = ""
            try:
                widget_resp = (
                    tenant_table(self.db, "widget_configs", self.client_id)
                    .select("knowledge_base, custom_instructions")
                    .limit(1)
                    .execute()
                )
                if widget_resp.data:
                    row = widget_resp.data[0]
                    knowledge_base = str(row.get("knowledge_base") or "")
                    custom_instructions = str(row.get("custom_instructions") or "")
            except Exception:
                logger.warning(
                    "WorkerTools.tenant_profile widget read failed client_id=%s",
                    self.client_id,
                    exc_info=True,
                )

            tenant_row["knowledge_base"] = knowledge_base
            tenant_row["custom_instructions"] = custom_instructions
            return tenant_row

        try:
            return await asyncio.to_thread(_run)
        except Exception:
            logger.warning(
                "WorkerTools.tenant_profile failed client_id=%s",
                self.client_id,
                exc_info=True,
            )
            return {}

    async def widget_knowledge_base(self) -> str:
        """Raw widget KB text for this tenant. ``""`` when unset."""
        profile = await self.tenant_profile()
        return str(profile.get("knowledge_base") or "")

    async def search_memory(self, query: str, *, match_count: int = 8) -> list[dict]:
        """Semantic search over ``os_memory_entries`` (durable orchestrator facts).

        Thin wrapper so a worker can pull memory hits relevant to its current
        task without re-implementing the embed + RPC dance. Returns ``[]`` on
        any failure — the worker continues with degraded context.
        """
        if not query:
            return []
        try:
            cap = _clamp_limit(match_count, 8)
            return await _search_memory(self.db, self.client_id, query, cap)
        except Exception:
            logger.warning(
                "WorkerTools.search_memory failed client_id=%s",
                self.client_id,
                exc_info=True,
            )
            return []


__all__ = ["WorkerTools"]
