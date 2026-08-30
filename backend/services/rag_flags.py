"""RAG feature flags. Defaults fail-closed.

RAG_ENABLED must stay off in production until isolation + eval gates pass.
Mirrors SEND_EMAIL_ENABLED — unset is off.
"""

import os

RAG_FLAG = "RAG_ENABLED"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def rag_enabled() -> bool:
    """Live Agent OS retrieval gate. Unset / empty / anything but 1/true/yes/on is off."""
    return os.environ.get(RAG_FLAG, "0").strip().lower() in _TRUTHY
