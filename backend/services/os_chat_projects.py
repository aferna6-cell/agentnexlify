"""Chat-originated OS Projects (round-4 item 3 - orchestration from chat).

An owner typing "start a project: launch a spring promo" in a workforce
thread should not have to find the Projects card - the ask becomes an
os_projects row right there. Detection is a deterministic prefix match (no
LLM in the loop); the row is queued at status='planning' and the background
runner (os_projects.plan_pending_projects, 5-minute tier) turns it into an
approvable draft plan through the exact same validated planner path the
endpoint uses. Nothing executes until the owner approves the draft.

Guardrails mirror the plan-gated /projects endpoint: the os_projects_enabled
platform flag, the agent_os plan set (chat is not a gate bypass), the
MAX_ACTIVE_PROJECTS cap, and an inbound-thread exclusion - end customers in
widget/email/SMS threads can never start the owner's projects. Any failure
returns None and the normal engine turn proceeds.
"""

import logging
import re
from datetime import datetime, timezone

from backend.services.os_constants import INBOUND_THREAD_SOURCES
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

# Owner-facing dashboard threads only. Alias kept for existing callers/tests.
_INBOUND_THREAD_SOURCES = INBOUND_THREAD_SOURCES

# Deterministic triggers: explicit project phrasing at the start of the
# message. Ordinary asks ("plan my week") never match.
_TRIGGER_RE = re.compile(
    r"^(?:please\s+)?"
    r"(?:plan\s+this\s+as\s+a\s+project"
    r"|make\s+this\s+a\s+project"
    r"|(?:start|create|kick\s+off|launch)\s+a\s+(?:new\s+)?project)"
    r"\b[\s:,.-]*(?P<ask>.*)$",
    re.IGNORECASE | re.DOTALL,
)

_ASK_LEAD_IN_RE = re.compile(r"^(?:to|for|about|on)\s+", re.IGNORECASE)

MIN_ASK_LEN = 10

HOW_TO_REPLY = (
    "Tell me what the project should accomplish and I'll queue it - for "
    'example: "Start a project: launch a spring promo for returning '
    'customers."'
)

CAP_REPLY = (
    "You already have the maximum number of active projects. Finish or "
    "cancel one in the Projects card first, then ask again."
)

UPGRADE_REPLY = (
    "Multi-department projects are part of the Agent OS plan. Upgrade at "
    "/billing to unlock them."
)

QUEUED_REPLY_TEMPLATE = (
    'Project queued: "{title}". The planner will draft a step-by-step '
    "department plan within about 5 minutes - review and approve it in the "
    "Projects card on the Agent Controls page. Nothing runs until you "
    "approve the plan."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def extract_project_ask(content: str) -> str | None:
    """The project ask from a trigger message, or None when not a trigger.

    Returns "" for a bare trigger ("start a project") so the caller can
    reply with usage guidance instead of routing to the engine.
    """
    match = _TRIGGER_RE.match((content or "").strip())
    if match is None:
        return None
    ask = _ASK_LEAD_IN_RE.sub("", (match.group("ask") or "").strip(), count=1)
    return ask.strip()


def _thread_is_owner_facing(db, client_id: str, thread_id: str) -> bool:
    rows = (
        tenant_table(db, "os_threads", client_id)
        .select("id, source")
        .eq("id", thread_id)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return False
    return (rows[0].get("source") or "chat") not in _INBOUND_THREAD_SOURCES


def _plan_allows_projects(db, client_id: str) -> bool:
    """Same plan set as the /projects router gate; fail-open on read errors."""
    from backend.services.agent_os_gate import AGENT_OS_PLANS

    try:
        rows = (
            db.table("tenants")
            .select("plan")
            .eq("id", client_id)
            .limit(1)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "os_chat_projects: plan read failed tenant=%s - failing open",
            client_id,
            exc_info=True,
        )
        return True
    if not rows:
        return True
    return str(rows[0].get("plan") or "") in AGENT_OS_PLANS


def _reply(db, client_id: str, thread_id: str, user_message_row: dict, text: str, **extra) -> dict:
    assistant_message = (
        tenant_table(db, "os_messages", client_id)
        .insert({"thread_id": thread_id, "role": "assistant", "content": text})
        .execute()
        .data[0]
    )
    tenant_table(db, "os_threads", client_id).update({"updated_at": _now()}).eq(
        "id", thread_id
    ).execute()
    return {
        "user_message": user_message_row,
        "assistant_message": assistant_message,
        "action": "answer",
        "agent_runs": [],
        "chat_project": True,
        **extra,
    }


async def try_start_project(
    db, client_id: str, thread_id: str, user_message_row: dict
) -> dict | None:
    """Queue a project from an explicit chat trigger, or None to proceed.

    None means "not a project ask (or projects unavailable) - run the normal
    engine turn". A dict is a completed turn in the shape process_user_turn
    returns.
    """
    ask = extract_project_ask(str(user_message_row.get("content") or ""))
    if ask is None:
        return None

    from backend.services.os_projects import (
        ACTIVE_STATUSES,
        MAX_ACTIVE_PROJECTS,
        MAX_ASK_LEN,
    )
    from backend.services.platform_flags import flag_enabled

    try:
        if not flag_enabled("os_projects_enabled"):
            return None
        if not _thread_is_owner_facing(db, client_id, thread_id):
            return None
        if not _plan_allows_projects(db, client_id):
            return _reply(db, client_id, thread_id, user_message_row, UPGRADE_REPLY)
        if len(ask) < MIN_ASK_LEN:
            return _reply(db, client_id, thread_id, user_message_row, HOW_TO_REPLY)

        active = (
            tenant_table(db, "os_projects", client_id)
            .select("id")
            .in_("status", list(ACTIVE_STATUSES))
            .limit(MAX_ACTIVE_PROJECTS)
            .execute()
        ).data or []
        if len(active) >= MAX_ACTIVE_PROJECTS:
            return _reply(db, client_id, thread_id, user_message_row, CAP_REPLY)

        ask = ask[:MAX_ASK_LEN]
        project = (
            tenant_table(db, "os_projects", client_id)
            .insert({"title": ask[:60], "ask": ask, "status": "planning"})
            .execute()
        ).data[0]
        try:
            from backend.services.activity import log_activity

            log_activity(
                tenant_id=client_id,
                activity_type="os_fast_path_chat_project",
                description=f"Project queued from chat: {ask[:80]}",
            )
        except Exception:
            logger.warning("os_chat_projects: usage log failed", exc_info=True)
        return _reply(
            db,
            client_id,
            thread_id,
            user_message_row,
            QUEUED_REPLY_TEMPLATE.format(title=ask[:60]),
            project=project,
        )
    except Exception:
        # Best-effort fast path: any failure falls through to the engine so
        # the owner's message is never lost to a broken shortcut.
        logger.warning(
            "os_chat_projects: failed tenant=%s thread=%s",
            client_id,
            thread_id,
            exc_info=True,
        )
        return None
