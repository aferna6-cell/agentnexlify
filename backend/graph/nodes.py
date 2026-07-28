"""Nodes — the unit of work in a graph.

A node is a name plus an async callable. Everything else (retries, error
policy, timeouts) is declarative config the runtime honors, so node bodies stay
free of boilerplate.
"""

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

# Node kinds are observability metadata, not behavior. They let the dashboard
# and the step ledger distinguish "this step called a model" from "this step
# read the database" without inspecting the callable.
NODE_KINDS = ("task", "agent", "router", "human", "terminal")

# Error policies. "goto:<node>" is also accepted and routes to a recovery node.
ON_ERROR_RAISE = "raise"
ON_ERROR_CONTINUE = "continue"


@dataclass
class NodeContext:
    """Everything a node body is handed.

    ``state`` is the state as of the *start* of this superstep — every node in
    a superstep sees the identical snapshot, so a node can never observe a
    half-applied sibling write.
    """

    state: dict[str, Any]
    node: str
    superstep: int
    run_id: str
    tenant_id: str | None = None
    # Value supplied by resume() when this node previously raised Interrupt.
    resume_value: Any = None
    # Mutable scratch space shared across the run: the LLM adapter puts the
    # RunBudget here so it can charge tokens without the node body threading it.
    extras: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)


@dataclass
class NodeResult:
    """What a node returns.

    A node that returns a plain dict has it treated as ``updates`` — the common
    case stays a one-liner.
    """

    updates: dict[str, Any] = field(default_factory=dict)
    # Overrides static edges for this node on this superstep. Use for routers
    # whose target set is computed rather than declared.
    goto: str | list[str] | None = None
    # Recorded on the step ledger row. Not merged into state.
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def coerce(cls, value: Any) -> "NodeResult":
        if value is None:
            return cls()
        if isinstance(value, NodeResult):
            return value
        if isinstance(value, dict):
            return cls(updates=value)
        raise TypeError(
            f"node returned {type(value).__name__}; expected NodeResult, dict, or None"
        )


NodeFn = Callable[[NodeContext], Awaitable[Any] | Any]


@dataclass
class Node:
    """A named step with its execution policy."""

    name: str
    fn: NodeFn
    kind: str = "task"
    # Retries are attempts *after* the first, so retries=2 means up to 3 calls.
    retries: int = 0
    retry_backoff_seconds: float = 0.5
    timeout_seconds: float | None = None
    on_error: str = ON_ERROR_RAISE
    description: str = ""

    def __post_init__(self) -> None:
        if self.kind not in NODE_KINDS:
            raise ValueError(
                f"node {self.name!r}: unknown kind {self.kind!r}; valid: {NODE_KINDS}"
            )
        if self.retries < 0:
            raise ValueError(f"node {self.name!r}: retries must be >= 0")
        if not (
            self.on_error in (ON_ERROR_RAISE, ON_ERROR_CONTINUE)
            or self.on_error.startswith("goto:")
        ):
            raise ValueError(
                f"node {self.name!r}: on_error must be 'raise', 'continue', "
                f"or 'goto:<node>'; got {self.on_error!r}"
            )

    @property
    def error_goto(self) -> str | None:
        """The recovery node when ``on_error`` is ``goto:<node>``."""
        if self.on_error.startswith("goto:"):
            return self.on_error.split(":", 1)[1]
        return None

    async def invoke(self, ctx: NodeContext) -> NodeResult:
        """Call the body, awaiting it when it is async. No retry logic here —
        the runtime owns retries so they can be recorded on the step ledger."""
        result = self.fn(ctx)
        if inspect.isawaitable(result):
            result = await result
        return NodeResult.coerce(result)
