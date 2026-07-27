"""Run budgets — the thing that makes a cyclic graph safe to execute.

`.claude/rules/task-budgets.md` requires every long agentic loop to be budgeted.
Anthropic's `task_budget` parameter is per-API-call and advisory; it cannot see
that a graph has looped forty times. This is the enforcement point that can.

Every limit is optional. A budget with all limits ``None`` never trips, which
is the right default for a short, acyclic graph.
"""

import time
from dataclasses import dataclass, field

from backend.graph.errors import BudgetExhausted

# A cyclic graph with no explicit per-node cap still terminates. 25 visits is
# high enough that a legitimate reflect/critique loop is never cut short, and
# low enough that a runaway loop costs a bounded amount of money.
DEFAULT_MAX_NODE_VISITS = 25


@dataclass
class RunBudget:
    """Caps on a single graph run.

    ``max_node_visits`` is per node, not total, and it is the limit that
    actually catches infinite loops: it fails with the offending node's name
    instead of letting the run spin until the wall-clock limit.
    """

    max_supersteps: int | None = 100
    max_node_runs: int | None = None
    max_node_visits: int | None = DEFAULT_MAX_NODE_VISITS
    max_tokens: int | None = None
    max_seconds: float | None = None

    # Live counters. Not constructor arguments.
    supersteps: int = field(default=0, init=False)
    node_runs: int = field(default=0, init=False)
    tokens: int = field(default=0, init=False)
    visits: dict[str, int] = field(default_factory=dict, init=False)
    started_at: float | None = field(default=None, init=False)

    def start(self) -> None:
        """Begin (or resume) wall-clock accounting."""
        self.started_at = time.monotonic()

    @property
    def elapsed_seconds(self) -> float:
        if self.started_at is None:
            return 0.0
        return time.monotonic() - self.started_at

    def check_superstep(self) -> None:
        """Called before each superstep. Raises when a limit is already spent."""
        if self.max_supersteps is not None and self.supersteps >= self.max_supersteps:
            raise BudgetExhausted(
                "supersteps",
                f"run reached the superstep limit ({self.max_supersteps}); "
                f"the graph is looping without converging",
            )
        if self.max_seconds is not None and self.elapsed_seconds >= self.max_seconds:
            raise BudgetExhausted(
                "seconds",
                f"run exceeded {self.max_seconds}s wall clock "
                f"(elapsed {self.elapsed_seconds:.1f}s)",
            )
        if self.max_tokens is not None and self.tokens >= self.max_tokens:
            raise BudgetExhausted(
                "tokens",
                f"run consumed {self.tokens} tokens, limit {self.max_tokens}",
            )

    def check_node(self, node: str) -> None:
        """Called before running ``node``. Raises when this node has looped too far."""
        visits = self.visits.get(node, 0)
        if self.max_node_visits is not None and visits >= self.max_node_visits:
            raise BudgetExhausted(
                "node_visits",
                f"node {node!r} was visited {visits} times, limit "
                f"{self.max_node_visits}; the loop through it is not converging",
            )
        if self.max_node_runs is not None and self.node_runs >= self.max_node_runs:
            raise BudgetExhausted(
                "node_runs",
                f"run executed {self.node_runs} nodes, limit {self.max_node_runs}",
            )

    def charge_node(self, node: str) -> None:
        self.node_runs += 1
        self.visits[node] = self.visits.get(node, 0) + 1

    def refund_node_visit(self, node: str) -> None:
        """Un-count a *visit* for a node that paused instead of looping.

        ``max_node_visits`` bounds looping. A node that raises ``Interrupt``
        has not looped — it asked a question and stopped. Without this refund a
        human gate costs two visits per real attempt (one to ask, one to
        resume), so a graph with an approval step hits its visit cap at roughly
        half the retries its own policy allows.

        ``node_runs`` is deliberately NOT refunded. The node body did execute,
        and leaving that charge in place is what stops a caller from resuming a
        forever-pausing node an unbounded number of times for free.
        """
        remaining = self.visits.get(node, 0) - 1
        if remaining > 0:
            self.visits[node] = remaining
        else:
            self.visits.pop(node, None)

    def charge_tokens(self, count: int) -> None:
        """Charge model usage. Called by the agent-node adapter, not the runtime."""
        self.tokens += max(0, count)

    def charge_superstep(self) -> None:
        self.supersteps += 1

    def snapshot(self) -> dict:
        """Serializable counters, stored on the run row for cost review."""
        return {
            "supersteps": self.supersteps,
            "node_runs": self.node_runs,
            "tokens": self.tokens,
            "visits": dict(self.visits),
            "elapsed_seconds": round(self.elapsed_seconds, 3),
        }

    def limits(self) -> dict:
        return {
            "max_supersteps": self.max_supersteps,
            "max_node_runs": self.max_node_runs,
            "max_node_visits": self.max_node_visits,
            "max_tokens": self.max_tokens,
            "max_seconds": self.max_seconds,
        }

    def restore(self, snapshot: dict | None) -> None:
        """Reload counters when resuming a checkpointed run.

        Without this, a run resumed after an interrupt would get a fresh budget
        and could loop forever across enough resumes.
        """
        if not snapshot:
            return
        self.supersteps = snapshot.get("supersteps", 0)
        self.node_runs = snapshot.get("node_runs", 0)
        self.tokens = snapshot.get("tokens", 0)
        self.visits = dict(snapshot.get("visits") or {})
