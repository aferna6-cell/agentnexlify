"""Calendar + CRM + Invoice Action Executor flags. Defaults fail-closed.

CALENDAR_ACTIONS_ENABLED / CRM_ACTIONS_ENABLED / INVOICE_ACTIONS_ENABLED
must stay off in production until offline evals + controlled smoke pass.
Mirrors SEND_EMAIL_ENABLED / RAG_ENABLED — unset is off.
"""

import os

CALENDAR_ACTIONS_FLAG = "CALENDAR_ACTIONS_ENABLED"
CRM_ACTIONS_FLAG = "CRM_ACTIONS_ENABLED"
INVOICE_ACTIONS_FLAG = "INVOICE_ACTIONS_ENABLED"
# Owner-chat Google Calendar read/book and its approval insert.
# Unset is off. The allowlist is optional: empty means every tenant when
# the flag is on; a comma-separated list limits it to those tenant ids.
CALENDAR_CHAT_FLAG = "CALENDAR_CHAT_ENABLED"
CALENDAR_CHAT_ALLOWLIST_ENV = "CALENDAR_CHAT_TENANT_ALLOWLIST"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _flag(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() in _TRUTHY


def calendar_actions_enabled() -> bool:
    """Live Calendar Action Executor gate. Unset / empty / non-truthy is off."""
    return _flag(CALENDAR_ACTIONS_FLAG)


def crm_actions_enabled() -> bool:
    """Live CRM Action Executor gate. Unset / empty / non-truthy is off."""
    return _flag(CRM_ACTIONS_FLAG)


def calendar_chat_enabled(tenant_id: str | None) -> bool:
    """Owner-chat calendar fast path and its events.insert approval.

    Off unless ``CALENDAR_CHAT_ENABLED`` is truthy. When
    ``CALENDAR_CHAT_TENANT_ALLOWLIST`` is non-empty, only those tenant ids
    are included. An empty allowlist with the flag on includes every tenant.
    """
    if not _flag(CALENDAR_CHAT_FLAG):
        return False
    raw = os.environ.get(CALENDAR_CHAT_ALLOWLIST_ENV, "").strip()
    if not raw:
        return True
    allowed = {part.strip() for part in raw.split(",") if part.strip()}
    return bool(tenant_id) and tenant_id in allowed


def invoice_actions_enabled() -> bool:
    """Live invoice Action Executor gate. Unset / empty / non-truthy is off."""
    return _flag(INVOICE_ACTIONS_FLAG)
