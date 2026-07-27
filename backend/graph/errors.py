"""Exceptions raised by the agent graph runtime.

Kept in their own module so every other module in the package can import them
without creating a cycle.
"""


class GraphError(Exception):
    """Base class for every error this package raises."""


class GraphValidationError(GraphError):
    """The graph is structurally invalid and must not be executed.

    Raised by :meth:`backend.graph.graph.Graph.validate` — dangling edges,
    unreachable nodes, an unreachable END, duplicate node names.
    """


class ChannelConflictError(GraphError):
    """Two nodes wrote a ``once`` channel, or a reducer rejected a value.

    This is the error that surfaces a genuine race in a parallel branch rather
    than letting one write silently clobber the other.
    """


class NodeExecutionError(GraphError):
    """A node raised and its retry budget and error policy are exhausted.

    The original exception is available as ``__cause__``; ``node`` names the
    node so the caller does not have to parse the message.
    """

    def __init__(self, node: str, message: str):
        super().__init__(f"node {node!r} failed: {message}")
        self.node = node


class BudgetExhausted(GraphError):
    """A run hit one of its :class:`~backend.graph.budget.RunBudget` limits.

    The runtime catches this and converts it into a terminal
    ``budget_exhausted`` status; it is only raised out of the package when a
    caller drives ``RunBudget`` directly.
    """

    def __init__(self, limit: str, message: str):
        super().__init__(message)
        self.limit = limit


class Interrupt(GraphError):  # noqa: N818 - control flow, deliberately not "…Error"
    """Raised by a node to pause the run and wait for outside input.

    Not a failure. The runtime checkpoints the run as ``awaiting_input`` and
    returns; :func:`backend.graph.runtime.resume` re-runs the interrupting node
    with the supplied value available on the node context.
    """

    def __init__(self, reason: str, payload: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.payload = payload or {}
