"""Label constants and transitions for the GitHub issue autopilot loop."""

from dataclasses import dataclass

AI_READY = "ai-ready"
NEEDS_INFO = "needs-info"
WIP_AUTOPILOT = "wip-autopilot"
AUTOPILOT_FAILED = "autopilot-failed"
AUTOPILOT_SKIPPED = "autopilot-skipped"
AUTOPILOT_PR = "autopilot-pr"
AI_ROUTINE = "ai-routine"
AI_DOCS = "ai-docs"
AI_TESTS = "ai-tests"
AI_RISKY = "ai-risky"

READY = "READY"
NEEDS_INFO_DECISION = "NEEDS_INFO"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
DISPATCH_FAILED = "DISPATCH_FAILED"
DISPATCH_SUCCEEDED = "DISPATCH_SUCCEEDED"

ALL_LABELS = (
    AI_READY,
    NEEDS_INFO,
    WIP_AUTOPILOT,
    AUTOPILOT_FAILED,
    AUTOPILOT_SKIPPED,
    AUTOPILOT_PR,
    AI_ROUTINE,
    AI_DOCS,
    AI_TESTS,
    AI_RISKY,
)

ROUTING_LABELS = (
    AI_ROUTINE,
    AI_DOCS,
    AI_TESTS,
    AI_RISKY,
)


@dataclass(frozen=True)
class LabelTransition:
    """Labels to add and remove for a state transition."""

    add: tuple[str, ...] = ()
    remove: tuple[str, ...] = ()


def normalize_label_names(raw_labels: list[dict[str, str]] | list[str]) -> set[str]:
    """Return label names from GitHub API label objects or plain strings."""

    names: set[str] = set()
    for label in raw_labels:
        if isinstance(label, str):
            names.add(label)
        elif isinstance(label, dict) and label.get("name"):
            names.add(str(label["name"]))
    return names


def transition_for(action: str, current_labels: set[str] | None = None) -> LabelTransition:
    """Return the label changes for an autopilot state action."""

    existing = current_labels or set()
    action = action.upper()

    if action == READY:
        return LabelTransition(
            add=(WIP_AUTOPILOT,),
            remove=tuple(
                label
                for label in (NEEDS_INFO, AUTOPILOT_FAILED, AUTOPILOT_SKIPPED)
                if label in existing
            ),
        )

    if action == NEEDS_INFO_DECISION:
        return LabelTransition(
            add=(NEEDS_INFO,),
            remove=tuple(
                label
                for label in (WIP_AUTOPILOT, AUTOPILOT_FAILED, AUTOPILOT_SKIPPED)
                if label in existing
            ),
        )

    if action == OUT_OF_SCOPE:
        return LabelTransition(
            add=(AUTOPILOT_SKIPPED,),
            remove=tuple(
                label
                for label in (WIP_AUTOPILOT, NEEDS_INFO, AUTOPILOT_FAILED, AI_READY)
                if label in existing
            ),
        )

    if action == DISPATCH_FAILED:
        return LabelTransition(
            add=(AUTOPILOT_FAILED,),
            remove=tuple(label for label in (WIP_AUTOPILOT,) if label in existing),
        )

    if action == DISPATCH_SUCCEEDED:
        return LabelTransition(
            add=(WIP_AUTOPILOT,),
            remove=tuple(
                label
                for label in (NEEDS_INFO, AUTOPILOT_FAILED, AUTOPILOT_SKIPPED)
                if label in existing
            ),
        )

    raise ValueError(f"unknown autopilot label transition: {action}")
