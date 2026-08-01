"""Unified connector registry — single source of truth for what "connected"
means across Agent OS chat awareness, the dashboard integrations page, and
the (future) in-chat connect card.

Phase 1b of ``plans/nexlify-capabilities-roadmap_plan.md``: read-side
unification only. The three underlying tables keep their existing key
columns — no schema changes, no migrations.

Schema notes (schema-discipline.md):
- ``integrations``        -> tenant_id  (google_calendar / m365_calendar /
  hubspot / gmail / facebook / instagram / twilio_byo)
- ``tenant_integrations`` -> client_id  (drive; migration 109)
- ``tenant_api_keys``     -> client_id  (zapier; migration 110/117)
- ``tenants.twilio_number``            (dedicated AI phone line)

Bug fixed here (2026-08-01): the pre-refactor ``connector_awareness.py``
queried ``tenant_api_keys`` with ``.eq("tenant_id", client_id)``, but the
table's actual tenant-scope column is ``client_id`` (migrations 110/117;
confirmed against ``backend/services/api_key_auth.py`` and
``backend/routers/zapier.py``, both of which use ``client_id``). Every
zapier connector-status lookup silently reported "not connected" even for
tenants with a live key. Fixed by querying the correct column. See
``docs/dev-knowledge/bug-patterns.md``.

Deterministic-first: connector inference is regex over the user's message
(no LLM call). Status resolution batches to one query per underlying table
(``connection_status``), not one query per connector.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StatusLoader:
    """Declares which table/row proves a connector is connected.

    ``kind`` values:
      - "provider_in": row's ``provider`` column is one of ``providers``
        (``integrations`` table — one query covers every provider-tagged
        connector).
      - "provider_enabled": a row exists with ``provider == provider`` AND
        ``enabled`` is truthy (``tenant_integrations`` — drive).
      - "column_truthy": the tenant's own row has a truthy ``column``
        (``tenants`` — phone).
      - "any_row": any row scoped to the tenant proves connection
        (``tenant_api_keys`` — zapier; a revoked-only tenant still shows
        connected, matching the pre-refactor behavior this preserves).
    """

    table: str
    kind: str
    providers: tuple[str, ...] = ()
    provider: str | None = None
    column: str | None = None


@dataclass(frozen=True)
class ConnectorSpec:
    key: str
    label: str
    connect_path: str
    category: str
    status_loader: StatusLoader
    oauth: bool = False
    patterns: tuple[str, ...] = field(default_factory=tuple)


# Patterns are deliberately high-precision: they must name the product or
# the platform feature, never a bare generic word — a false prompt
# ("connect your calendar" after someone merely said the word "call")
# erodes trust in the agent. Order matters: it is preserved in every
# registry-derived listing (inference results, GET /status).
_REGISTRY: tuple[ConnectorSpec, ...] = (
    ConnectorSpec(
        key="calendar",
        label="Google or Outlook calendar",
        connect_path="/dashboard/integrations",
        category="calendar",
        oauth=True,
        status_loader=StatusLoader(
            table="integrations",
            kind="provider_in",
            providers=("google_calendar", "m365_calendar"),
        ),
        patterns=(
            r"\bgoogle calendar\b",
            r"\boutlook calendar\b",
            r"\b(sync|connect|link|check|pull from|add to)\b[^.?!]{0,30}\bcalendar\b",
            r"\bcalendar\b[^.?!]{0,20}\b(sync|synced|integration)\b",
        ),
    ),
    ConnectorSpec(
        key="hubspot",
        label="HubSpot",
        connect_path="/dashboard/integrations",
        category="crm",
        oauth=True,
        status_loader=StatusLoader(
            table="integrations", kind="provider_in", providers=("hubspot",)
        ),
        patterns=(
            r"\bhubspot\b",
            r"\b(push|sync|send|export)\b[^.?!]{0,30}\bcrm\b",
            r"\bcrm\b[^.?!]{0,20}\b(sync|integration|connect)\b",
        ),
    ),
    ConnectorSpec(
        key="drive",
        label="Google Drive",
        connect_path="/dashboard/knowledge",
        category="storage",
        status_loader=StatusLoader(
            table="tenant_integrations", kind="provider_enabled", provider="drive"
        ),
        patterns=(
            r"\bgoogle drive\b",
            r"\bdrive folder\b",
            r"\b(sync|connect|link)\b[^.?!]{0,20}\bdrive\b",
        ),
    ),
    ConnectorSpec(
        key="phone",
        label="AI phone line",
        connect_path="/dashboard/settings",
        category="phone",
        status_loader=StatusLoader(
            table="tenants", kind="column_truthy", column="twilio_number"
        ),
        patterns=(
            r"\banswer\b[^.?!]{0,20}\b(calls|phone)\b",
            r"\b(ai|virtual) receptionist\b",
            r"\bphone (assistant|agent|line|number for the ai)\b",
            r"\bvoice (assistant|agent|line)\b",
            r"\bmissed calls?\b",
        ),
    ),
    ConnectorSpec(
        key="zapier",
        label="Zapier",
        connect_path="/dashboard/integrations",
        category="automation",
        status_loader=StatusLoader(table="tenant_api_keys", kind="any_row"),
        patterns=(r"\bzapier\b", r"\bzaps?\b"),
    ),
    ConnectorSpec(
        key="gmail",
        label="Gmail",
        connect_path="/dashboard/integrations",
        category="email",
        # Auth flow owned by the inbox-monitoring lane (Phase 2 of the
        # roadmap plan) — registry metadata + status lookup only for now.
        status_loader=StatusLoader(
            table="integrations", kind="provider_in", providers=("gmail",)
        ),
        patterns=(
            r"\bgmail\b",
            r"\b(connect|sync|check|monitor)\b[^.?!]{0,20}\b(inbox|email account)\b",
        ),
    ),
    ConnectorSpec(
        key="instagram",
        label="Instagram",
        connect_path="/dashboard/integrations",
        category="social",
        status_loader=StatusLoader(
            table="integrations", kind="provider_in", providers=("instagram",)
        ),
        patterns=(r"\binstagram\b", r"\big dms?\b"),
    ),
    ConnectorSpec(
        key="facebook",
        label="Facebook Page",
        connect_path="/dashboard/integrations",
        category="social",
        status_loader=StatusLoader(
            table="integrations", kind="provider_in", providers=("facebook",)
        ),
        patterns=(r"\bfacebook\b", r"\bfb page\b"),
    ),
    ConnectorSpec(
        key="twilio_byo",
        label="your own Twilio number",
        connect_path="/dashboard/integrations",
        category="phone",
        status_loader=StatusLoader(
            table="integrations", kind="provider_in", providers=("twilio_byo",)
        ),
        patterns=(
            r"\bmy own twilio\b",
            r"\bbring your own twilio\b",
            r"\bbyo twilio\b",
        ),
    ),
)

_BY_KEY = {c.key: c for c in _REGISTRY}
_COMPILED = {
    c.key: tuple(re.compile(p, re.IGNORECASE) for p in c.patterns) for c in _REGISTRY
}


def get_registry() -> list[dict]:
    """Full connector catalog, no DB access. Stable declared order."""
    return [
        {
            "key": c.key,
            "label": c.label,
            "connect_path": c.connect_path,
            "category": c.category,
            "oauth": c.oauth,
        }
        for c in _REGISTRY
    ]


def is_oauth_connector(key: str) -> bool:
    """True when the connector's auth flow supports the in-chat
    ``?os_thread_id=`` deep-link round-trip (see
    ``backend/routers/integrations.py`` state JWT)."""
    spec = _BY_KEY.get(key)
    return bool(spec and spec.oauth)


def infer_needed_connectors(text: str) -> list[str]:
    """Connector keys the message appears to need. Deterministic, ordered."""
    if not text:
        return []
    return [
        key for key, patterns in _COMPILED.items() if any(p.search(text) for p in patterns)
    ]


def connection_status(db, *, tenant_id: str, client_id: str | None = None) -> dict[str, bool]:
    """Which connectors are live for this tenant — one indexed lookup per
    underlying table, not per connector.

    ``tenant_id`` scopes the ``integrations`` and ``tenants`` lookups.
    ``client_id`` scopes ``tenant_integrations`` and ``tenant_api_keys``.
    In this codebase the tenant's UUID is the same value under both column
    names, so ``client_id`` defaults to ``tenant_id`` — pass it explicitly
    only when a caller genuinely has two different IDs.

    Best-effort per table: a failed lookup reports False for every
    connector backed by that table (prompting to connect an
    already-connected tool is annoying but harmless; the connect page
    shows the true state).
    """
    if client_id is None:
        client_id = tenant_id

    status = {c.key: False for c in _REGISTRY}

    try:
        rows = (
            db.table("integrations").select("provider").eq("tenant_id", tenant_id).execute()
        ).data or []
        providers = {r.get("provider") for r in rows}
        for c in _REGISTRY:
            if c.status_loader.table == "integrations":
                status[c.key] = bool(providers & set(c.status_loader.providers))
    except Exception:
        logger.warning(
            "connector_registry: integrations lookup failed for %s", tenant_id, exc_info=True
        )

    try:
        rows = (
            db.table("tenant_integrations")
            .select("provider, enabled")
            .eq("client_id", client_id)
            .execute()
        ).data or []
        for c in _REGISTRY:
            if c.status_loader.table == "tenant_integrations":
                status[c.key] = any(
                    r.get("provider") == c.status_loader.provider and r.get("enabled")
                    for r in rows
                )
    except Exception:
        logger.warning(
            "connector_registry: tenant_integrations lookup failed for %s",
            client_id,
            exc_info=True,
        )

    try:
        rows = (
            db.table("tenants").select("twilio_number").eq("id", tenant_id).limit(1).execute()
        ).data or []
        for c in _REGISTRY:
            if c.status_loader.table == "tenants":
                status[c.key] = bool(rows and rows[0].get(c.status_loader.column))
    except Exception:
        logger.warning(
            "connector_registry: tenants lookup failed for %s", tenant_id, exc_info=True
        )

    try:
        rows = (
            db.table("tenant_api_keys").select("id").eq("client_id", client_id).execute()
        ).data or []
        for c in _REGISTRY:
            if c.status_loader.table == "tenant_api_keys":
                status[c.key] = bool(rows)
    except Exception:
        logger.warning(
            "connector_registry: tenant_api_keys lookup failed for %s", client_id, exc_info=True
        )

    return status
