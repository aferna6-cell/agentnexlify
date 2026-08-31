"""Calendar + CRM Action Executor flags. Defaults fail-closed.

CALENDAR_ACTIONS_ENABLED / CRM_ACTIONS_ENABLED must stay off in production
until offline evals + controlled smoke pass. Mirrors SEND_EMAIL_ENABLED /
RAG_ENABLED — unset is off.
"""

import os

CALENDAR_ACTIONS_FLAG = "CALENDAR_ACTIONS_ENABLED"
CRM_ACTIONS_FLAG = "CRM_ACTIONS_ENABLED"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _flag(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() in _TRUTHY


def calendar_actions_enabled() -> bool:
    """Live Calendar Action Executor gate. Unset / empty / non-truthy is off."""
    return _flag(CALENDAR_ACTIONS_FLAG)


def crm_actions_enabled() -> bool:
    """Live CRM Action Executor gate. Unset / empty / non-truthy is off."""
    return _flag(CRM_ACTIONS_FLAG)
