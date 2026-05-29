"""Wishlist capture — demand signal for agents that don't exist yet.

When the orchestrator routes to the generalist (no specialist owns the ask), it
records the ask here. Accumulated wishlist entries tell the product team which
new worker agents to build next. This is deliberately tiny: an in-memory list
the demo can read back. Persistence is a later concern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WishlistEntry:
    """One unmet owner ask plus the closest specialist we could find."""

    ask_text: str
    closest_agent_id: str | None
    closest_score: float
    captured_at: datetime = field(default_factory=datetime.now)


class Wishlist:
    """In-memory store of asks no specialist owned."""

    def __init__(self) -> None:
        self._entries: list[WishlistEntry] = []

    def capture(
        self,
        ask_text: str,
        *,
        closest_agent_id: str | None = None,
        closest_score: float = 0.0,
    ) -> WishlistEntry:
        entry = WishlistEntry(
            ask_text=ask_text.strip(),
            closest_agent_id=closest_agent_id,
            closest_score=closest_score,
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> list[WishlistEntry]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)
