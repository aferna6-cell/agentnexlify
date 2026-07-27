"""Graph definition, edges, and structural validation.

Validation runs before any node executes. Catching a dangling edge or an
unreachable END at build time is the difference between a clear error and a
run that burns budget going nowhere.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from backend.graph.errors import GraphValidationError
from backend.graph.nodes import Node, NodeFn
from backend.graph.state import StateSchema

# Sentinel node names. Not real nodes — the runtime never executes them.
START = "__start__"
END = "__end__"

# A condition is a predicate over state. None means an unconditional edge.
Condition = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True)
class Edge:
    """A directed edge, optionally guarded by a predicate over state.

    ``is_default`` marks an *else* edge: it is taken only when no non-default
    edge out of the same node matched. Without this distinction an
    unconditional fallback would fire alongside a matching conditional edge and
    silently fan out to both targets.
    """

    source: str
    target: str
    condition: Condition | None = None
    label: str = ""
    is_default: bool = False

    @property
    def is_conditional(self) -> bool:
        return self.condition is not None

    def passes(self, state: dict[str, Any]) -> bool:
        if self.condition is None:
            return True
        return bool(self.condition(state))

    def describe(self) -> str:
        if self.label:
            return f"{self.source} -[{self.label}]-> {self.target}"
        if self.condition is not None:
            return f"{self.source} -[?]-> {self.target}"
        return f"{self.source} -> {self.target}"


@dataclass
class Graph:
    """A named, versioned graph of nodes and edges.

    Cycles are legal — that is the point. What is not legal is a structure the
    runtime cannot make progress through, and :meth:`validate` rejects those.
    """

    name: str
    version: str = "1"
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    schema: StateSchema = field(default_factory=StateSchema)

    # ------------------------------------------------------------------ build

    def add_node(
        self,
        name: str,
        fn: NodeFn,
        *,
        kind: str = "task",
        retries: int = 0,
        retry_backoff_seconds: float = 0.5,
        timeout_seconds: float | None = None,
        on_error: str = "raise",
        description: str = "",
    ) -> "Graph":
        if name in (START, END):
            raise GraphValidationError(f"{name!r} is a reserved sentinel name")
        if name in self.nodes:
            raise GraphValidationError(f"duplicate node name {name!r}")
        self.nodes[name] = Node(
            name=name,
            fn=fn,
            kind=kind,
            retries=retries,
            retry_backoff_seconds=retry_backoff_seconds,
            timeout_seconds=timeout_seconds,
            on_error=on_error,
            description=description,
        )
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        *,
        condition: Condition | None = None,
        label: str = "",
        is_default: bool = False,
    ) -> "Graph":
        self.edges.append(Edge(source, target, condition, label, is_default))
        return self

    def set_entry(self, *nodes: str) -> "Graph":
        """Mark nodes as the run's entry points. Several means a parallel start."""
        for node in nodes:
            self.add_edge(START, node)
        return self

    def set_finish(self, *nodes: str, condition: Condition | None = None) -> "Graph":
        for node in nodes:
            self.add_edge(node, END, condition=condition)
        return self

    def add_branch(
        self,
        source: str,
        branches: dict[str, Condition],
        *,
        default: str | None = None,
    ) -> "Graph":
        """Add several conditional edges plus an optional *else* edge.

        The fallback matters: a node whose every outgoing edge is conditional
        can strand a run when no condition holds. ``default`` is how you say
        "and otherwise, go here" — it fires only when none of ``branches``
        matched, not alongside them.
        """
        for target, condition in branches.items():
            self.add_edge(source, target, condition=condition, label=target)
        if default is not None:
            self.add_edge(source, default, label="else", is_default=True)
        return self

    def declare(self, name: str, reducer: str = "last", default: Any = None) -> "Graph":
        self.schema.declare(name, reducer=reducer, default=default)
        return self

    # ------------------------------------------------------------- inspection

    def successors(self, node: str, state: dict[str, Any]) -> list[str]:
        """Targets of ``node`` whose conditions hold for ``state``.

        Every passing non-default edge is taken, so a node with two true
        conditions fans out to both. Default (*else*) edges are consulted only
        when nothing else matched. Order is deduplicated and stable.
        """
        targets: list[str] = []
        defaults: list[str] = []
        for edge in self.edges:
            if edge.source != node:
                continue
            if edge.is_default:
                if edge.target not in defaults:
                    defaults.append(edge.target)
            elif edge.passes(state) and edge.target not in targets:
                targets.append(edge.target)
        return targets or defaults

    def outgoing(self, node: str) -> list[Edge]:
        return [edge for edge in self.edges if edge.source == node]

    def _reachable_from_start(self) -> set[str]:
        """Structural reachability, ignoring conditions (they are runtime facts)."""
        seen: set[str] = set()
        frontier = [START]
        while frontier:
            current = frontier.pop()
            for edge in self.edges:
                if edge.source == current and edge.target not in seen:
                    seen.add(edge.target)
                    frontier.append(edge.target)
        return seen

    # ------------------------------------------------------------- validation

    def validate(self) -> "Graph":
        """Raise :class:`GraphValidationError` on any structural defect.

        Returns self so it can be chained onto a builder expression.
        """
        problems: list[str] = []
        known = set(self.nodes) | {START, END}

        for edge in self.edges:
            if edge.source not in known:
                problems.append(f"edge {edge.describe()} has unknown source {edge.source!r}")
            if edge.target not in known:
                problems.append(f"edge {edge.describe()} has unknown target {edge.target!r}")
            if edge.source == END:
                problems.append(f"edge {edge.describe()} leaves END, which is terminal")
            if edge.target == START:
                problems.append(f"edge {edge.describe()} points back at START")

        entries = [edge for edge in self.edges if edge.source == START]
        if not entries:
            problems.append("no entry point: add an edge from START (use set_entry)")

        reachable = self._reachable_from_start()

        if END not in reachable:
            problems.append(
                "END is unreachable: no path from START can terminate, so every "
                "run would end in budget exhaustion (use set_finish)"
            )

        for name in self.nodes:
            if name not in reachable:
                problems.append(f"node {name!r} is unreachable from START")
            if not self.outgoing(name):
                problems.append(
                    f"node {name!r} has no outgoing edge; it would silently end "
                    f"its branch (add an edge to END if that is intended)"
                )

        # A node whose outgoing edges are all conditional, with no else edge,
        # strands the run when none of them hold. That is a real failure mode,
        # not a style nit.
        for name in self.nodes:
            out = self.outgoing(name)
            if not out:
                continue
            has_fallback = any(
                edge.is_default or not edge.is_conditional for edge in out
            )
            if not has_fallback:
                problems.append(
                    f"node {name!r} has only conditional edges "
                    f"({', '.join(e.describe() for e in out)}) and no else "
                    f"edge; add one via add_branch(..., default=...) so the "
                    f"run cannot strand when no condition holds"
                )

        # Error-recovery targets must exist.
        for name, node in self.nodes.items():
            target = node.error_goto
            if target is not None and target not in known:
                problems.append(
                    f"node {name!r} has on_error='goto:{target}' but "
                    f"{target!r} is not a node in this graph"
                )

        if problems:
            raise GraphValidationError(
                f"graph {self.name!r} v{self.version} is invalid:\n  - "
                + "\n  - ".join(problems)
            )
        return self

    def to_mermaid(self) -> str:
        """Render as a mermaid flowchart for docs and PR descriptions."""
        lines = ["flowchart TD"]
        lines.append(f'    {START}(["START"])')
        lines.append(f'    {END}(["END"])')
        for name, node in self.nodes.items():
            shape = f'{name}{{"{name}"}}' if node.kind == "router" else f'{name}["{name}"]'
            lines.append(f"    {shape}")
        for edge in self.edges:
            if edge.label:
                lines.append(f"    {edge.source} -->|{edge.label}| {edge.target}")
            elif edge.is_conditional:
                lines.append(f"    {edge.source} -.-> {edge.target}")
            else:
                lines.append(f"    {edge.source} --> {edge.target}")
        return "\n".join(lines)
