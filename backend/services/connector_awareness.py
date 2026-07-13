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

Schema notes (schema-discipline.md):
- ``integrations``        -> tenant_id  (google_calendar / m365_calendar / hubspot)
- ``tenant_integrations`` -> client_id  (drive)
- ``tenant_api_keys``     -> tenant_id  (zapier)
- ``tenants.twilio_number``            (dedicated AI phone line)
"""

import logging
import re

logger = logging.getLogger(__name__)

# Connector registry. Patterns are deliberately high-precision: they must
# name the product or the platform feature, never a bare generic word - a
# false prompt ("connect your calendar" after someone merely said the word
# "call") erodes trust in the agent.
CONNECTORS: dict = {
    "calendar": {
        "label": "Google or Outlook calendar",
        "path": "/dashboard/integrations",
        "patterns": (
            r"\bgoogle calendar\b",
            r"\boutlook calendar\b",
            r"\b(sync|connect|link|check|pull from|add to)\b[^.?!]{0,30}\bcalendar\b",
            r"\bcalendar\b[^.?!]{0,20}\b(sync|synced|integration)\b",
        ),
    },
    "hubspot": {
        "label": "HubSpot",
        "path": "/dashboard/integrations",
        "patterns": (
            r"\bhubspot\b",
            r"\b(push|sync|send|export)\b[^.?!]{0,30}\bcrm\b",
            r"\bcrm\b[^.?!]{0,20}\b(sync|integration|connect)\b",
        ),
    },
    "drive": {
        "label": "Google Drive",
        "path": "/dashboard/knowledge",
        "patterns": (
            r"\bgoogle drive\b",
            r"\bdrive folder\b",
            r"\b(sync|connect|link)\b[^.?!]{0,20}\bdrive\b",
        ),
    },
    "phone": {
        "label": "AI phone line",
        "path": "/dashboard/settings",
        "patterns": (
            r"\banswer\b[^.?!]{0,20}\b(calls|phone)\b",
            r"\b(ai|virtual) receptionist\b",
            r"\bphone (assistant|agent|line|number for the ai)\b",
            r"\bvoice (assistant|agent|line)\b",
            r"\bmissed calls?\b",
        ),
    },
    "zapier": {
        "label": "Zapier",
        "path": "/dashboard/integrations",
        "patterns": (r"\bzapier\b", r"\bzaps?\b"),
    },
}

_COMPILED = {
    key: tuple(re.compile(p, re.IGNORECASE) for p in cfg["patterns"])
    for key, cfg in CONNECTORS.items()
}


def infer_needed_connectors(text: str) -> list[str]:
    """Connector keys the message appears to need. Deterministic, ordered."""
    if not text:
        return []
    return [
        key
        for key, patterns in _COMPILED.items()
        if any(p.search(text) for p in patterns)
    ]


def connection_status(db, client_id: str) -> dict:
    """Which connectors are live for this tenant. Best-effort per connector -
    a failed lookup reports False (prompting to connect an already-connected
    tool is annoying but harmless; the connect page shows the true state)."""
    status = {key: False for key in CONNECTORS}

    try:
        rows = (
            db.table("integrations")
            .select("provider")
            .eq("tenant_id", client_id)
            .execute()
        ).data or []
        providers = {r.get("provider") for r in rows}
        status["calendar"] = bool(providers & {"google_calendar", "m365_calendar"})
        status["hubspot"] = "hubspot" in providers
    except Exception:
        logger.warning(
            "connector_awareness: integrations lookup failed for %s",
            client_id,
            exc_info=True,
        )

    try:
        rows = (
            db.table("tenant_integrations")
            .select("provider, enabled")
            .eq("client_id", client_id)
            .eq("provider", "drive")
            .execute()
        ).data or []
        status["drive"] = any(r.get("enabled") for r in rows)
    except Exception:
        logger.warning(
            "connector_awareness: drive lookup failed for %s", client_id, exc_info=True
        )

    try:
        rows = (
            db.table("tenants")
            .select("twilio_number")
            .eq("id", client_id)
            .limit(1)
            .execute()
        ).data or []
        status["phone"] = bool(rows and rows[0].get("twilio_number"))
    except Exception:
        logger.warning(
            "connector_awareness: phone lookup failed for %s", client_id, exc_info=True
        )

    try:
        rows = (
            db.table("tenant_api_keys")
            .select("id")
            .eq("tenant_id", client_id)
            .limit(1)
            .execute()
        ).data or []
        status["zapier"] = bool(rows)
    except Exception:
        logger.warning(
            "connector_awareness: zapier lookup failed for %s", client_id, exc_info=True
        )

    return status


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
        {"key": key, "label": CONNECTORS[key]["label"], "path": CONNECTORS[key]["path"]}
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
