"""Structural validation tests for backend.graph.graph.

``Graph.validate()`` is the gate that turns a class of runtime mysteries
(a run that burns its whole budget going nowhere) into a build-time error with
a name attached. Every test here asserts on the *message*, not just that
something raised — a validation error whose text does not identify the defect
is barely better than no validation.
"""

import pytest

from backend.graph.errors import GraphValidationError
from backend.graph.graph import END, START, Edge, Graph


def _noop(ctx):
    return None


def _graph(name: str = "g") -> Graph:
    return Graph(name)


def _validation_message(graph: Graph) -> str:
    with pytest.raises(GraphValidationError) as exc:
        graph.validate()
    return str(exc.value)


# ---------------------------------------------------------------------------
# build-time guards (raise at add_node, before validate)
# ---------------------------------------------------------------------------


def test_add_node_rejects_duplicate_name():
    graph = _graph().add_node("a", _noop)
    with pytest.raises(GraphValidationError) as exc:
        graph.add_node("a", _noop)
    assert "duplicate node name 'a'" in str(exc.value)


@pytest.mark.parametrize("sentinel", [START, END])
def test_add_node_rejects_reserved_sentinel_names(sentinel):
    with pytest.raises(GraphValidationError) as exc:
        _graph().add_node(sentinel, _noop)
    message = str(exc.value)
    assert "reserved sentinel name" in message
    assert repr(sentinel) in message


# ---------------------------------------------------------------------------
# edge defects
# ---------------------------------------------------------------------------


def test_validate_catches_dangling_source():
    graph = _graph().add_node("a", _noop)
    graph.set_entry("a").set_finish("a")
    graph.add_edge("ghost", "a")

    message = _validation_message(graph)
    assert "unknown source 'ghost'" in message


def test_validate_catches_dangling_target():
    graph = _graph().add_node("a", _noop)
    graph.set_entry("a").set_finish("a")
    graph.add_edge("a", "ghost")

    message = _validation_message(graph)
    assert "unknown target 'ghost'" in message


def test_validate_catches_edge_leaving_end():
    graph = _graph().add_node("a", _noop)
    graph.set_entry("a").set_finish("a")
    graph.add_edge(END, "a")

    message = _validation_message(graph)
    assert "leaves END, which is terminal" in message


def test_validate_catches_edge_pointing_back_at_start():
    graph = _graph().add_node("a", _noop)
    graph.set_entry("a").set_finish("a")
    graph.add_edge("a", START)

    message = _validation_message(graph)
    assert "points back at START" in message


# ---------------------------------------------------------------------------
# reachability defects
# ---------------------------------------------------------------------------


def test_validate_catches_missing_entry_point():
    graph = _graph().add_node("a", _noop)
    graph.set_finish("a")

    message = _validation_message(graph)
    assert "no entry point" in message
    assert "set_entry" in message


def test_validate_catches_unreachable_end():
    """A graph that can only loop forever is a budget bonfire, not a workflow."""
    graph = _graph().add_node("a", _noop)
    graph.set_entry("a")
    graph.add_edge("a", "a")

    message = _validation_message(graph)
    assert "END is unreachable" in message
    assert "set_finish" in message


def test_validate_catches_unreachable_node():
    graph = _graph().add_node("a", _noop).add_node("orphan", _noop)
    graph.set_entry("a").set_finish("a")
    graph.set_finish("orphan")

    message = _validation_message(graph)
    assert "node 'orphan' is unreachable from START" in message


def test_validate_catches_node_with_no_outgoing_edge():
    graph = _graph().add_node("a", _noop).add_node("dead_end", _noop)
    graph.set_entry("a")
    graph.add_edge("a", "dead_end")
    graph.set_finish("a")

    message = _validation_message(graph)
    assert "node 'dead_end' has no outgoing edge" in message
    assert "add an edge to END" in message


# ---------------------------------------------------------------------------
# all-conditional edges (needs an else edge)
# ---------------------------------------------------------------------------


def test_validate_catches_node_whose_edges_are_all_conditional():
    graph = _graph().add_node("router", _noop).add_node("hot", _noop)
    graph.set_entry("router")
    graph.add_branch("router", {"hot": lambda s: s.get("score", 0) > 0.8})
    graph.set_finish("hot")

    message = _validation_message(graph)
    assert "node 'router' has only conditional edges" in message
    assert "no else" in message
    assert "add_branch(..., default=...)" in message


def test_validate_accepts_all_conditional_edges_plus_an_else_edge():
    graph = _graph().add_node("router", _noop).add_node("hot", _noop)
    graph.set_entry("router")
    graph.add_branch("router", {"hot": lambda s: s.get("score", 0) > 0.8}, default=END)
    graph.set_finish("hot")

    assert graph.validate() is graph


def test_validate_accepts_a_conditional_edge_beside_an_unconditional_one():
    graph = _graph().add_node("router", _noop).add_node("hot", _noop)
    graph.set_entry("router")
    graph.add_edge("router", "hot", condition=lambda s: s.get("hot"))
    graph.set_finish("router", "hot")

    assert graph.validate() is graph


# ---------------------------------------------------------------------------
# on_error targets
# ---------------------------------------------------------------------------


def test_validate_catches_on_error_goto_missing_node():
    graph = _graph()
    graph.add_node("a", _noop, on_error="goto:recover")
    graph.set_entry("a").set_finish("a")

    message = _validation_message(graph)
    assert "node 'a' has on_error='goto:recover'" in message
    assert "'recover' is not a node in this graph" in message


def test_validate_accepts_on_error_goto_existing_node():
    graph = _graph()
    graph.add_node("a", _noop, on_error="goto:recover")
    graph.add_node("recover", _noop)
    graph.set_entry("a")
    graph.add_edge("a", "recover")
    graph.set_finish("a", "recover")

    assert graph.validate() is graph


def test_validate_accepts_on_error_goto_end():
    graph = _graph()
    graph.add_node("a", _noop, on_error=f"goto:{END}")
    graph.set_entry("a").set_finish("a")

    assert graph.validate() is graph


# ---------------------------------------------------------------------------
# several defects at once
# ---------------------------------------------------------------------------


def test_validate_reports_every_problem_at_once():
    graph = _graph("broken")
    graph.add_node("a", _noop)
    graph.add_edge("a", "ghost")

    message = _validation_message(graph)
    assert "graph 'broken' v1 is invalid" in message
    assert "unknown target 'ghost'" in message
    assert "no entry point" in message
    assert "END is unreachable" in message
    assert "node 'a' is unreachable from START" in message


# ---------------------------------------------------------------------------
# valid graphs
# ---------------------------------------------------------------------------


def test_validate_accepts_a_linear_graph_and_returns_self():
    graph = _graph()
    graph.add_node("a", _noop).add_node("b", _noop)
    graph.set_entry("a")
    graph.add_edge("a", "b")
    graph.set_finish("b")

    assert graph.validate() is graph


def test_validate_accepts_a_valid_cyclic_graph():
    """Cycles are the point of this framework — a bounded loop must validate."""
    graph = _graph("reflect")
    graph.add_node("draft", _noop).add_node("critique", _noop)
    graph.set_entry("draft")
    graph.add_edge("draft", "critique")
    graph.add_branch(
        "critique",
        {"draft": lambda s: not s.get("good_enough")},
        default=END,
    )

    assert graph.validate() is graph


def test_validate_accepts_a_parallel_fan_out_and_fan_in():
    graph = _graph()
    graph.add_node("alpha", _noop).add_node("beta", _noop).add_node("join", _noop)
    graph.set_entry("alpha", "beta")
    graph.add_edge("alpha", "join")
    graph.add_edge("beta", "join")
    graph.set_finish("join")

    assert graph.validate() is graph


# ---------------------------------------------------------------------------
# successors() — else-edge semantics (regression: default fired alongside a
# matching conditional edge and fanned out to both targets)
# ---------------------------------------------------------------------------


def test_successors_takes_only_the_matching_branch_not_the_else_edge():
    graph = _graph().add_node("router", _noop).add_node("hot", _noop).add_node("cold", _noop)
    graph.set_entry("router")
    graph.add_branch("router", {"hot": lambda s: s["score"] > 0.8}, default="cold")
    graph.set_finish("hot", "cold")

    assert graph.successors("router", {"score": 0.9}) == ["hot"]


def test_successors_falls_back_to_the_else_edge_when_nothing_matched():
    graph = _graph().add_node("router", _noop).add_node("hot", _noop).add_node("cold", _noop)
    graph.set_entry("router")
    graph.add_branch("router", {"hot": lambda s: s["score"] > 0.8}, default="cold")
    graph.set_finish("hot", "cold")

    assert graph.successors("router", {"score": 0.1}) == ["cold"]


def test_successors_fans_out_to_every_matching_non_default_edge():
    graph = _graph()
    for name in ("router", "a", "b", "fallback"):
        graph.add_node(name, _noop)
    graph.set_entry("router")
    graph.add_branch(
        "router",
        {"a": lambda s: s["n"] > 0, "b": lambda s: s["n"] > 1},
        default="fallback",
    )
    graph.set_finish("a", "b", "fallback")

    assert graph.successors("router", {"n": 2}) == ["a", "b"]
    assert graph.successors("router", {"n": 1}) == ["a"]
    assert graph.successors("router", {"n": 0}) == ["fallback"]


def test_successors_deduplicates_repeated_targets():
    graph = _graph().add_node("a", _noop).add_node("b", _noop)
    graph.set_entry("a")
    graph.add_edge("a", "b")
    graph.add_edge("a", "b")
    graph.set_finish("b")

    assert graph.successors("a", {}) == ["b"]


def test_add_branch_marks_the_default_edge_as_an_else_edge():
    graph = _graph().add_node("router", _noop).add_node("hot", _noop).add_node("cold", _noop)
    graph.add_branch("router", {"hot": lambda s: True}, default="cold")

    default_edges = [e for e in graph.outgoing("router") if e.is_default]
    assert len(default_edges) == 1
    assert default_edges[0].target == "cold"
    assert default_edges[0].label == "else"
    assert default_edges[0].is_conditional is False


def test_plain_edges_are_not_default_edges():
    graph = _graph().add_node("a", _noop)
    graph.set_entry("a").set_finish("a")
    assert all(edge.is_default is False for edge in graph.edges)


# ---------------------------------------------------------------------------
# Edge helpers
# ---------------------------------------------------------------------------


def test_edge_passes_is_true_for_unconditional_edges():
    assert Edge("a", "b").passes({}) is True


def test_edge_passes_coerces_the_predicate_result_to_bool():
    edge = Edge("a", "b", condition=lambda s: s.get("items"))
    assert edge.passes({"items": ["x"]}) is True
    assert edge.passes({"items": []}) is False


def test_edge_describe_shapes():
    assert Edge("a", "b").describe() == "a -> b"
    assert Edge("a", "b", condition=lambda s: True).describe() == "a -[?]-> b"
    assert Edge("a", "b", label="hot").describe() == "a -[hot]-> b"


# ---------------------------------------------------------------------------
# to_mermaid
# ---------------------------------------------------------------------------


def test_to_mermaid_emits_a_line_for_every_node_and_edge():
    graph = _graph("triage")
    graph.add_node("classify", _noop, kind="router")
    graph.add_node("escalate", _noop)
    graph.set_entry("classify")
    graph.add_branch("classify", {"escalate": lambda s: s["hot"]}, default=END)
    graph.set_finish("escalate")

    mermaid = graph.to_mermaid()
    lines = mermaid.splitlines()

    assert lines[0] == "flowchart TD"
    assert f'    {START}(["START"])' in lines
    assert f'    {END}(["END"])' in lines

    # One declaration line per node; routers render as a diamond.
    assert '    classify{"classify"}' in lines
    assert '    escalate["escalate"]' in lines

    # One connector line per edge.
    connectors = [line for line in lines if "-->" in line or "-.->" in line]
    assert len(connectors) == len(graph.edges)

    assert f"    {START} --> classify" in lines
    assert "    classify -->|escalate| escalate" in lines
    assert f"    classify -->|else| {END}" in lines
    assert f"    escalate --> {END}" in lines


def test_to_mermaid_renders_unlabeled_conditional_edges_as_dotted():
    graph = _graph()
    graph.add_node("a", _noop).add_node("b", _noop)
    graph.set_entry("a")
    graph.add_edge("a", "b", condition=lambda s: True)
    graph.set_finish("a", "b")

    assert "    a -.-> b" in graph.to_mermaid().splitlines()
