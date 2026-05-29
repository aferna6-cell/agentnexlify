"""Honest reasoning trace (rule 1).

The QA report flagged "theatrical" traces: workers claiming to "Load business
profile / knowledge base / recent chats" even when those were empty. The fix is
structural — a trace step can only be marked *loaded* by passing the real data
through :meth:`ReasoningTrace.record_load`, which inspects whether anything
actually came back. There is no API for asserting a successful load of empty
data, and the registry's validator rejects any step that tries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


def _is_empty(data: Any) -> bool:
    if data is None:
        return True
    if isinstance(data, str):
        return not data.strip()
    if isinstance(data, (list, tuple, dict, set)):
        return len(data) == 0
    return False


@dataclass
class TraceStep:
    """A single line in the reasoning trace.

    ``loaded`` is True only when real data backed the step. ``detail`` always
    reflects reality — either what loaded, or that nothing did.
    """

    name: str
    loaded: bool
    detail: str
    summary: str | None = None  # short description of what loaded

    def render(self) -> str:
        mark = "✓" if self.loaded else "○"
        return f"{mark} {self.name}: {self.detail}"


@dataclass
class ReasoningTrace:
    steps: list[TraceStep] = field(default_factory=list)

    def record_load(
        self,
        name: str,
        data: Any,
        *,
        describe: Callable[[Any], str] | None = None,
        fallback_note: str | None = None,
        skip_if_empty: bool = False,
    ) -> bool:
        """Honestly record an attempt to load *data*.

        Returns True if real data loaded. When *data* is empty we either skip
        the step entirely (``skip_if_empty=True``) or record an honest
        "nothing loaded" line — never a green check.
        """

        if _is_empty(data):
            if skip_if_empty:
                return False
            note = fallback_note or f"no {name.lower()} yet — using fallback"
            self.steps.append(TraceStep(name=name, loaded=False, detail=note))
            return False

        summary = describe(data) if describe else _default_describe(data)
        self.steps.append(
            TraceStep(
                name=name,
                loaded=True,
                detail=f"loaded {summary}",
                summary=summary,
            )
        )
        return True

    def note(self, name: str, detail: str) -> None:
        """Record a non-load reasoning step (e.g. a decision). Marked as not a
        data load so it never implies data was fetched."""

        self.steps.append(TraceStep(name=name, loaded=False, detail=detail))

    def action(self, name: str, summary: str) -> None:
        """Record a step that genuinely produced something (e.g. "drafted
        reply"). Marked loaded with the summary it produced."""

        self.steps.append(
            TraceStep(name=name, loaded=True, detail=summary, summary=summary)
        )

    def render(self) -> str:
        return "\n".join(step.render() for step in self.steps)

    def to_list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "loaded": s.loaded,
                "detail": s.detail,
                "summary": s.summary,
            }
            for s in self.steps
        ]


def _default_describe(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, (list, tuple, set)):
        return f"{len(data)} item(s)"
    if isinstance(data, dict):
        return f"{len(data)} field(s)"
    return str(data)
