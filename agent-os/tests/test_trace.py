"""Honest reasoning trace (rule 1).

There is no API for asserting a successful load of empty data — that is the
structural fix the QA report demanded.
"""

from __future__ import annotations

from agent_os.trace import ReasoningTrace


def test_record_load_marks_loaded_when_data_present():
    t = ReasoningTrace()
    loaded = t.record_load("Business profile", ["a", "b"], describe=lambda d: f"{len(d)} fields")
    assert loaded is True
    step = t.steps[-1]
    assert step.loaded is True
    assert step.summary == "2 fields"
    assert step.render().startswith("✓")


def test_record_load_is_honest_when_empty():
    t = ReasoningTrace()
    loaded = t.record_load("Widget conversations", [])
    assert loaded is False
    step = t.steps[-1]
    assert step.loaded is False
    assert step.summary is None
    assert step.render().startswith("○")


def test_record_load_can_skip_empty():
    t = ReasoningTrace()
    loaded = t.record_load("Pipeline", [], skip_if_empty=True)
    assert loaded is False
    assert t.steps == []  # nothing recorded at all


def test_empty_string_counts_as_no_load():
    t = ReasoningTrace()
    assert t.record_load("Knowledge base", "   ") is False
    assert t.steps[-1].loaded is False


def test_note_is_never_marked_loaded():
    t = ReasoningTrace()
    t.note("Decision", "chose email channel")
    assert t.steps[-1].loaded is False


def test_action_is_marked_loaded_with_summary():
    t = ReasoningTrace()
    t.action("Drafted reply", "Hi Mike, ...")
    step = t.steps[-1]
    assert step.loaded is True
    assert step.summary == "Hi Mike, ..."


def test_to_list_shape():
    t = ReasoningTrace()
    t.record_load("Business profile", "name, phone", describe=lambda s: s)
    t.note("Decision", "x")
    rows = t.to_list()
    assert rows[0].keys() == {"name", "loaded", "detail", "summary"}
    assert rows[0]["loaded"] is True
    assert rows[1]["loaded"] is False
