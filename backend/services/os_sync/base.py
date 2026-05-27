"""Agent OS sync base types — shared across every sync module.

A sync module pulls fresh state from one upstream source into the tenant's
semantic memory (``os_memory_entries``) on a recurring cadence. Each module
under ``backend/services/os_sync/`` declares a module-level ``SPEC: SyncSpec``
and an async ``run`` function. The package auto-discovers them; the
scheduled tick (``os_sync_tick``) reads ``os_sync_state``, picks rows
whose ``enabled=true`` and not currently ``running``, and dispatches the
matching SyncSpec.

Source-ref dedup: every memory write carries ``source_ref`` like
``"leads:<uuid>"`` so re-syncs upsert the same memory row instead of
duplicating. Partial unique index ``os_memory_entries (client_id, source_ref)
WHERE source_ref IS NOT NULL`` enforces this at DB level (migration 127).
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SyncContext:
    """Inputs for one sync run."""

    db: object
    client_id: str
    source: str  # matches SyncSpec.name and os_sync_state.source
    state_row: dict  # the current os_sync_state row (cursor, last_run_at, etc.)
    backfill: bool = False  # if true, ignore last_seen_cursor and pull everything


@dataclass
class SyncResult:
    """A sync's outcome.

    ``status`` is one of ``ok`` or ``error``. ``rows_seen`` is how many rows
    the source returned this run (cumulative count lives in os_sync_state).
    ``new_cursor`` is the next ``last_seen_cursor`` value to persist; if
    None, cursor is unchanged. ``error_detail`` is human-readable on error.
    """

    status: str
    rows_seen: int = 0
    new_cursor: str | None = None
    error_detail: str | None = None


SyncRun = Callable[[SyncContext], Awaitable[SyncResult]]


@dataclass
class SyncSpec:
    """A sync module's registry entry."""

    name: str  # canonical source, e.g. "leads", "appointments", "google_calendar"
    run: SyncRun
    description: str = ""
    required_connectors: list[str] = field(default_factory=list)
