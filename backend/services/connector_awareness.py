"""Connector-need inference for Agent OS chat.

When a tenant asks their agent for something that requires an integration
that is not connected ("push this lead to HubSpot", "check my Google
Calendar", "answer my phone calls"), the agent should say so and point at
the exact connect page - not silently produce a mock answer.

Deterministic-first: connector inference is regex over the user's message
(no LLM call), and connection status is a handful of indexed lookups. The
result feeds two places in ``os_thread_runner.process_user_turn``:

1. ``connection_status`` rides into the engine's SharedContext so the main
   reply can be grounded in what is actually connected.
2. When an inferred connector is missing, a short follow-up assistant
   message with the connect path is posted after the engine reply - once
   per connector per thread (dedup by path string in prior messages).

Phase 1b refactor (2026-08-01): this module is now a thin adapter over
``backend/services/connector_registry.py``, the single source of truth for
the connector catalog and status resolution across the platform (dashboard
integrations, ``GET /api/v1/connectors/status``, and this chat-awareness
path). This module's public functions keep their exact pre-refactor
signatures and behavior - ``os_thread_runner`` and ``test_connector_awareness.py``
depend on them unchanged - scoped to the five connectors this feature has
always covered. New connectors, and the OAuth in-chat deep-link, are wired
through the registry directly (``connector_registry.get_registry`` /
``is_oauth_connector``) - see ``backend/routers/connectors.py`` and
``os_thread_runner._post_connect_prompt``.

Schema notes (schema-discipline.md) - full, current version lives in
connector_registry.py. Kept here for a quick read of what this feature
covers:
- ``integrations``        -> tenant_id  (google_calendar / m365_calendar / hubspot)
- ``tenant_integrations`` -> client_id  (drive)
- ``tenant_api_keys``     -> client_id  (zapier)
- ``tenants.twilio_number``            (dedicated AI phone line)
"""

import logging

from backend.services import connector_registry

logger = logging.getLogger(__name__)

# The five connectors this chat-awareness feature has always covered, in
# their historical declared order (inference results keep this ordering).
_LEGACY_KEYS = ("calendar", "hubspot", "drive", "phone", "zapier")

# {key: {"label": ..., "connect_path": ..., ...}} sourced live from the
# registry so the two catalogs can never drift apart.
_LEGACY = {
    entry["key"]: entry
    for entry in connector_registry.get_registry()
    if entry["key"] in _LEGACY_KEYS
}


def infer_needed_connectors(text: str) -> list[str]:
    """Connector keys the message appears to need. Deterministic, ordered.

    Scoped to the five legacy chat-awareness connectors - the registry now
    covers more (gmail/instagram/facebook/twilio_byo), but this function's
    contract (and its callers' dedup/prompt copy) predates them.
    """
    full = connector_registry.infer_needed_connectors(text)
    return [key for key in full if key in _LEGACY_KEYS]


def connection_status(db, client_id: str) -> dict:
    """Which connectors are live for this tenant. Best-effort per connector -
    a failed lookup reports False (prompting to connect an already-connected
    tool is annoying but harmless; the connect page shows the true state)."""
    full = connector_registry.connection_status(db, tenant_id=client_id, client_id=client_id)
    return {key: full[key] for key in _LEGACY_KEYS}


def missing_for_message(db, client_id: str, text: str) -> list[dict]:
    """Connectors the message needs but the tenant hasn't connected.

    Returns [{key, label, path}] - empty when nothing is needed or
    everything needed is already connected (the common case costs only
    the regex pass; status lookups run only on an inference hit)."""
    needed = infer_needed_connectors(text)
    if not needed:
        return []
    status = connection_status(db, client_id)
    return [
        {"key": key, "label": _LEGACY[key]["label"], "path": _LEGACY[key]["connect_path"]}
        for key in needed
        if not status.get(key)
    ]


def connect_prompt(missing: list[dict]) -> str:
    """The follow-up chat message asking the owner to connect."""
    if len(missing) == 1:
        m = missing[0]
        return (
            f"To do this for real I need your {m['label']} connected - "
            f"it takes about a minute here: {m['path']}. "
            f"Once it's linked, just ask me again."
        )
    lines = "\n".join(f"- {m['label']}: {m['path']}" for m in missing)
    return (
        "To do this for real I need a couple of things connected first:\n"
        f"{lines}\n"
        "Each takes about a minute. Once they're linked, just ask me again."
    )


def already_prompted(prior_messages: list[dict], missing: list[dict]) -> list[dict]:
    """Filter out connectors whose connect path already appears in an earlier
    assistant message of this thread - one nudge per connector per thread."""
    seen = "\n".join(
        (m.get("content") or "")
        for m in prior_messages
        if m.get("role") == "assistant"
    )
    return [m for m in missing if m["path"] not in seen]
