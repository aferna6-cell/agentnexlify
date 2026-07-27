"""Work selection — deciding what the loop builds, and when it refuses to build.

This module exists because of a specific, documented failure. From
``brain/Maps/Open Loops.md``, after the loop shipped 15 PRs in one session:

    "the autonomous loop has exhausted the high-value buildable backlog …
    Continuing the loop now would mean manufacturing low-value niche work,
    against the 'highest value' intent."

An autonomous engineering loop with no floor does not stop when it runs out of
worthwhile work. It keeps producing, and the marginal PR gets steadily worse
until someone notices. The scheduler was never the hard part; this is.

The split of responsibility is deliberate:

- **Judgement is the model's.** Scoring an issue's value, effort, and how
  confident we are that it can be done unattended needs reading the issue.
  The driving session supplies those numbers.
- **Policy is this file's.** The floor, the ordering, the exclusions, and the
  stop condition are plain code with plain tests. A model cannot talk the loop
  past its own guardrail, and the guardrail's behavior is inspectable without
  running a model at all.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# A composite score below this is not worth an autonomous PR. Calibration: a
# item scoring 0.35 is roughly "moderate value, moderate confidence, moderate
# effort" — the exact profile of the niche-vertical work the loop was producing
# when it should have stopped. Raising this makes the loop pickier and idle
# more; lowering it re-opens the make-work failure.
VALUE_FLOOR = 0.35

# Risk tiers the loop will act on unattended. "high" is always escalated to the
# owner instead of implemented, however valuable it looks — an unattended agent
# should not be the thing that decides a high-risk change was fine.
ACTIONABLE_RISK = frozenset({"low", "medium"})

# Consecutive idle rounds after which the loop reports the backlog as genuinely
# dry rather than transiently empty. Two is enough to distinguish "nothing ready
# right now" from "there is nothing left" without waiting days to say so.
DRY_AFTER_IDLE_ROUNDS = 2

_EPSILON = 0.05


@dataclass(frozen=True)
class WorkItem:
    """One candidate piece of work, scored by the session that fetched it."""

    id: str
    title: str
    value: float = 0.0
    effort: float = 0.5
    confidence: float = 0.5
    risk: str = "medium"
    labels: tuple[str, ...] = ()
    blocked: bool = False
    blocked_reason: str = ""
    owner_gated: bool = False
    touches_frontend: bool = False
    url: str = ""

    @property
    def score(self) -> float:
        """Value per unit effort, discounted by how confident we are.

        Effort divides rather than subtracts so that a cheap moderate win
        outranks an expensive one — which is the ordering you want when the
        loop has a bounded number of PRs per day.
        """
        return (self.value * self.confidence) / (self.effort + _EPSILON)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "WorkItem":
        known = {f for f in cls.__dataclass_fields__}
        data = {k: v for k, v in raw.items() if k in known}
        if "labels" in data and data["labels"] is not None:
            data["labels"] = tuple(data["labels"])
        if not data.get("id"):
            raise ValueError(f"work item needs an id: {raw!r}")
        return cls(**data)


@dataclass
class Selection:
    """The outcome of one selection pass."""

    chosen: WorkItem | None
    skipped: list[tuple[str, str]] = field(default_factory=list)
    idle_reason: str = ""
    dry: bool = False

    @property
    def has_work(self) -> bool:
        return self.chosen is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chosen": (
                {
                    "id": self.chosen.id,
                    "title": self.chosen.title,
                    "score": round(self.chosen.score, 3),
                    "risk": self.chosen.risk,
                    "url": self.chosen.url,
                    "touches_frontend": self.chosen.touches_frontend,
                }
                if self.chosen
                else None
            ),
            "skipped": [{"id": i, "reason": r} for i, r in self.skipped],
            "idle_reason": self.idle_reason,
            "dry": self.dry,
        }


def _exclusion(item: WorkItem, floor: float) -> str | None:
    """Why this item is not actionable right now, or None if it is.

    Ordered most-decisive first so the reported reason is the useful one.
    """
    if item.blocked:
        return f"blocked: {item.blocked_reason or 'no reason given'}"
    if item.owner_gated:
        return "owner-gated — needs a decision only the owner can make"
    if item.risk not in ACTIONABLE_RISK:
        return f"risk={item.risk} — escalate rather than implement unattended"
    if item.score < floor:
        return f"score {item.score:.2f} below floor {floor:.2f}"
    return None


def select(
    items: list[WorkItem],
    *,
    floor: float = VALUE_FLOOR,
    exclude_ids: set[str] | None = None,
    allow_frontend: bool = True,
    idle_rounds: int = 0,
) -> Selection:
    """Pick the single highest-scoring actionable item, or report why not.

    One item per run, deliberately. The loop opens at most a few PRs a day
    (see ``gates.deploy_budget_remaining``), and a driver that grabs a batch
    cannot re-evaluate priority after the first one lands.

    Args:
        exclude_ids: items already in flight or attempted this cycle.
        allow_frontend: set False when the deploy quota is spent — backend-only
            work still ships to Railway when Vercel is capped, which is exactly
            what the 2026-06-23 session fell back to.
        idle_rounds: how many consecutive prior rounds found nothing. Used only
            to decide whether an empty result is reported as "dry".
    """
    exclude_ids = exclude_ids or set()
    skipped: list[tuple[str, str]] = []
    actionable: list[WorkItem] = []

    for item in items:
        if item.id in exclude_ids:
            skipped.append((item.id, "already attempted this cycle"))
            continue
        if item.touches_frontend and not allow_frontend:
            skipped.append((item.id, "frontend work paused — deploy quota spent"))
            continue
        reason = _exclusion(item, floor)
        if reason:
            skipped.append((item.id, reason))
            continue
        actionable.append(item)

    if not actionable:
        dry = idle_rounds + 1 >= DRY_AFTER_IDLE_ROUNDS
        return Selection(
            chosen=None,
            skipped=skipped,
            idle_reason=_idle_reason(items, skipped, floor, dry),
            dry=dry,
        )

    # Ties broken by id so a rerun on unchanged input picks the same item.
    actionable.sort(key=lambda i: (-i.score, i.id))
    return Selection(chosen=actionable[0], skipped=skipped)


def _idle_reason(
    items: list[WorkItem],
    skipped: list[tuple[str, str]],
    floor: float,
    dry: bool,
) -> str:
    if not items:
        return "no candidate work items were supplied"
    if dry:
        return (
            f"{len(skipped)} candidates, none actionable across "
            f"{DRY_AFTER_IDLE_ROUNDS} consecutive rounds — treat the backlog as "
            f"dry and stop scheduling until new work is filed"
        )
    return (
        f"{len(skipped)} candidates, none actionable this round "
        f"(floor {floor:.2f})"
    )


def load_items(path: str | Path) -> list[WorkItem]:
    """Read a scored backlog produced by the driving session.

    Accepts either a bare list or ``{"items": [...]}`` so the session can add
    metadata alongside without breaking the reader.
    """
    raw = json.loads(Path(path).read_text())
    entries = raw.get("items", []) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise ValueError(
            f"backlog must be a list or {{'items': [...]}}; got {type(entries).__name__}"
        )
    return [WorkItem.from_dict(e) for e in entries]
