"""Agent graph runtime — durable, budgeted execution of cyclic agent workflows.

Spec: ``specs/agent-graph-runtime_spec.md``. Guide: ``docs/dev-knowledge/graph-framework.md``.

    from backend.graph import Graph, run

    graph = Graph("triage")
    graph.declare("findings", reducer="append", default=[])
    graph.add_node("classify", classify_fn, kind="agent")
    graph.add_node("escalate", escalate_fn)
    graph.set_entry("classify")
    graph.add_branch(
        "classify",
        {"escalate": lambda s: s["score"] > 0.8},
        default="__end__",
    )
    graph.set_finish("escalate")

    result = await run(graph, {"lead_id": lead_id}, tenant_id=tenant_id)
"""

from backend.graph.budget import RunBudget
from backend.graph.checkpoint import (
    STATUS_AWAITING_INPUT,
    STATUS_BUDGET_EXHAUSTED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    Checkpoint,
    Checkpointer,
    FileCheckpointer,
    InMemoryCheckpointer,
    NullCheckpointer,
    StepRecord,
)
from backend.graph.errors import (
    BudgetExhausted,
    ChannelConflictError,
    GraphError,
    GraphValidationError,
    Interrupt,
    NodeExecutionError,
)
from backend.graph.graph import END, START, Edge, Graph
from backend.graph.nodes import Node, NodeContext, NodeResult
from backend.graph.registry import register
from backend.graph.runtime import RunResult, resume, run
from backend.graph.state import Channel, StateSchema
from backend.graph.store import SupabaseCheckpointer

__all__ = [
    "END",
    "START",
    "STATUS_AWAITING_INPUT",
    "STATUS_BUDGET_EXHAUSTED",
    "STATUS_COMPLETED",
    "STATUS_FAILED",
    "STATUS_RUNNING",
    "BudgetExhausted",
    "Channel",
    "ChannelConflictError",
    "Checkpoint",
    "Checkpointer",
    "Edge",
    "FileCheckpointer",
    "Graph",
    "GraphError",
    "GraphValidationError",
    "InMemoryCheckpointer",
    "Interrupt",
    "Node",
    "NodeContext",
    "NodeExecutionError",
    "NodeResult",
    "NullCheckpointer",
    "RunBudget",
    "RunResult",
    "StateSchema",
    "StepRecord",
    "SupabaseCheckpointer",
    "register",
    "resume",
    "run",
]
