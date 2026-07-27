"""Unit tests for backend.graph.state — channels, reducers, and the
superstep merge.

The central guarantee under test is ``apply_updates`` determinism: the folded
result of a superstep must not depend on which node happened to finish first.
Everything else here (MISSING vs None, strict schemas, write-once channels)
exists to make that guarantee legible when it breaks.
"""

import pytest

from backend.graph.errors import ChannelConflictError
from backend.graph.state import (
    MISSING,
    REDUCERS,
    Channel,
    StateSchema,
    _Missing,
    apply_updates,
    reduce_add,
    reduce_append,
    reduce_last,
    reduce_merge,
    reduce_once,
)


# ---------------------------------------------------------------------------
# MISSING sentinel
# ---------------------------------------------------------------------------


def test_missing_is_a_singleton():
    assert _Missing() is MISSING
    assert _Missing() is _Missing()


def test_missing_is_falsy_and_reprs_as_missing():
    assert bool(MISSING) is False
    assert repr(MISSING) == "MISSING"


def test_missing_is_distinct_from_none():
    """None is a legitimate channel value, so it must not read as 'unset'."""
    assert MISSING is not None
    assert (MISSING is None) is False


# ---------------------------------------------------------------------------
# reducers
# ---------------------------------------------------------------------------


def test_reduce_last_takes_the_incoming_value():
    assert reduce_last(MISSING, "a") == "a"
    assert reduce_last("a", "b") == "b"
    assert reduce_last("a", None) is None


def test_reduce_append_starts_a_list_from_missing_or_none():
    assert reduce_append(MISSING, "a") == ["a"]
    assert reduce_append(None, "a") == ["a"]


def test_reduce_append_concatenates_lists_and_appends_scalars():
    assert reduce_append(["a"], "b") == ["a", "b"]
    assert reduce_append(["a"], ["b", "c"]) == ["a", "b", "c"]


def test_reduce_append_does_not_mutate_the_existing_list():
    existing = ["a"]
    merged = reduce_append(existing, "b")
    assert existing == ["a"]
    assert merged is not existing


def test_reduce_merge_shallow_updates():
    assert reduce_merge(MISSING, {"a": 1}) == {"a": 1}
    assert reduce_merge(None, {"a": 1}) == {"a": 1}
    assert reduce_merge({"a": 1, "b": 2}, {"b": 3}) == {"a": 1, "b": 3}


def test_reduce_merge_does_not_mutate_the_existing_dict():
    existing = {"a": 1}
    merged = reduce_merge(existing, {"b": 2})
    assert existing == {"a": 1}
    assert merged is not existing


def test_reduce_merge_rejects_non_dict_incoming():
    with pytest.raises(ChannelConflictError) as exc:
        reduce_merge({"a": 1}, ["not", "a", "dict"])
    assert "merge reducer requires a dict" in str(exc.value)
    assert "list" in str(exc.value)


def test_reduce_add_sums_from_zero():
    assert reduce_add(MISSING, 5) == 5
    assert reduce_add(None, 5) == 5
    assert reduce_add(2, 3) == 5
    assert reduce_add(1.5, 0.5) == 2.0


def test_reduce_once_accepts_the_first_write():
    assert reduce_once(MISSING, "first") == "first"


def test_reduce_once_rejects_a_second_write():
    with pytest.raises(ChannelConflictError) as exc:
        reduce_once("first", "second")
    message = str(exc.value)
    assert "write-once" in message
    assert "'first'" in message
    assert "'second'" in message


def test_reduce_once_treats_none_as_an_existing_value():
    """None is a real value, so a channel holding None is already written."""
    with pytest.raises(ChannelConflictError):
        reduce_once(None, "second")


def test_reducers_registry_exposes_the_five_names():
    assert set(REDUCERS) == {"last", "append", "merge", "add", "once"}


# ---------------------------------------------------------------------------
# Channel
# ---------------------------------------------------------------------------


def test_channel_defaults_to_last_reducer_and_missing_default():
    channel = Channel("summary")
    assert channel.reducer == "last"
    assert channel.default is MISSING


def test_channel_rejects_an_unknown_reducer():
    with pytest.raises(ValueError) as exc:
        Channel("summary", reducer="frobnicate")
    message = str(exc.value)
    assert "unknown reducer 'frobnicate'" in message
    assert "'summary'" in message


# ---------------------------------------------------------------------------
# StateSchema.build / declare / initial
# ---------------------------------------------------------------------------


def test_build_from_compact_mapping():
    schema = StateSchema.build({"messages": "append", "score": "add"})
    assert schema.channels["messages"].reducer == "append"
    assert schema.channels["score"].reducer == "add"
    assert schema.strict is False


def test_build_accepts_channel_objects_verbatim():
    channel = Channel("notes", reducer="append", default=[])
    schema = StateSchema.build({"notes": channel})
    assert schema.channels["notes"] is channel


def test_build_with_no_spec_is_empty():
    schema = StateSchema.build()
    assert schema.channels == {}


def test_build_strict_flag_propagates():
    assert StateSchema.build({"a": "last"}, strict=True).strict is True


def test_declare_registers_a_channel():
    schema = StateSchema()
    schema.declare("findings", reducer="append", default=[])
    assert schema.channels["findings"].reducer == "append"
    assert schema.channels["findings"].default == []


def test_declare_defaults_to_missing_so_the_key_stays_absent():
    schema = StateSchema()
    schema.declare("summary")
    assert schema.channels["summary"].default is MISSING
    assert schema.initial() == {}


def test_initial_only_includes_channels_with_a_default():
    schema = StateSchema.build(
        {
            "seeded": Channel("seeded", default=0),
            "unseeded": Channel("unseeded"),
            "explicit_none": Channel("explicit_none", default=None),
        }
    )
    initial = schema.initial()
    assert initial == {"seeded": 0, "explicit_none": None}
    assert "unseeded" not in initial


def test_initial_deep_copies_mutable_defaults():
    schema = StateSchema()
    schema.declare("log", reducer="append", default=[])

    first = schema.initial()
    first["log"].append("polluted")
    second = schema.initial()

    assert second["log"] == []


def test_reducer_for_returns_the_declared_reducer():
    schema = StateSchema.build({"log": "append"})
    assert schema.reducer_for("log") is reduce_append


def test_reducer_for_permissive_schema_falls_back_to_last():
    schema = StateSchema.build({"log": "append"}, strict=False)
    assert schema.reducer_for("undeclared") is reduce_last


def test_reducer_for_strict_schema_raises_on_undeclared_channel():
    schema = StateSchema.build({"log": "append"}, strict=True)
    with pytest.raises(ChannelConflictError) as exc:
        schema.reducer_for("summry")
    message = str(exc.value)
    assert "undeclared channel 'summry'" in message
    assert "strict=False" in message


def test_strict_schema_rejects_typo_channels_through_apply_updates():
    schema = StateSchema.build({"summary": "last"}, strict=True)
    with pytest.raises(ChannelConflictError) as exc:
        apply_updates({}, [("writer", {"summry": "oops"})], schema)
    assert "undeclared channel 'summry'" in str(exc.value)


# ---------------------------------------------------------------------------
# apply_updates
# ---------------------------------------------------------------------------


def test_apply_updates_folds_a_single_delta():
    schema = StateSchema.build({"summary": "last"})
    merged = apply_updates({"lead_id": "L1"}, [("writer", {"summary": "hi"})], schema)
    assert merged == {"lead_id": "L1", "summary": "hi"}


def test_apply_updates_is_order_independent_for_last_reducer():
    """The core guarantee: same writes, any arrival order, identical result."""
    schema = StateSchema.build({"winner": "last"})
    state = {}

    forward = apply_updates(
        state,
        [("alpha", {"winner": "alpha"}), ("beta", {"winner": "beta"})],
        schema,
    )
    reverse = apply_updates(
        state,
        [("beta", {"winner": "beta"}), ("alpha", {"winner": "alpha"})],
        schema,
    )

    assert forward == reverse
    # Sorted by node name, so the alphabetically-last node wins either way.
    assert forward["winner"] == "beta"


def test_apply_updates_is_order_independent_for_append_reducer():
    schema = StateSchema.build({"log": "append"})
    state = {"log": []}

    forward = apply_updates(
        state,
        [("alpha", {"log": "a"}), ("beta", {"log": "b"}), ("gamma", {"log": "c"})],
        schema,
    )
    shuffled = apply_updates(
        state,
        [("gamma", {"log": "c"}), ("alpha", {"log": "a"}), ("beta", {"log": "b"})],
        schema,
    )

    assert forward == shuffled
    assert forward["log"] == ["a", "b", "c"]


def test_apply_updates_is_order_independent_across_mixed_reducers():
    schema = StateSchema.build(
        {"log": "append", "score": "add", "meta": "merge", "winner": "last"}
    )
    state = {"log": [], "score": 0, "meta": {}}
    updates = [
        ("alpha", {"log": "a", "score": 1, "meta": {"a": 1}, "winner": "alpha"}),
        ("beta", {"log": "b", "score": 2, "meta": {"b": 2}, "winner": "beta"}),
        ("delta", {"log": "d", "score": 3, "meta": {"a": 9}, "winner": "delta"}),
    ]

    import itertools

    results = [apply_updates(state, list(perm), schema) for perm in itertools.permutations(updates)]
    first = results[0]
    for other in results[1:]:
        assert other == first

    assert first["log"] == ["a", "b", "d"]
    assert first["score"] == 6
    assert first["meta"] == {"a": 9, "b": 2}
    assert first["winner"] == "delta"


def test_apply_updates_skips_empty_deltas():
    schema = StateSchema.build({"log": "append"})
    merged = apply_updates({"log": ["a"]}, [("noop", {}), ("noop2", None)], schema)
    assert merged == {"log": ["a"]}


def test_apply_updates_does_not_mutate_the_input_state():
    schema = StateSchema.build({"log": "append", "score": "add"})
    state = {"log": ["existing"], "score": 1}

    merged = apply_updates(state, [("writer", {"log": "new", "score": 2})], schema)

    assert state == {"log": ["existing"], "score": 1}
    assert merged is not state
    assert merged["log"] is not state["log"]
    assert merged["log"] == ["existing", "new"]
    assert merged["score"] == 3


def test_apply_updates_once_channel_double_write_names_the_node():
    schema = StateSchema.build({"decision": "once"})
    with pytest.raises(ChannelConflictError) as exc:
        apply_updates(
            {},
            [("alpha", {"decision": "approve"}), ("beta", {"decision": "deny"})],
            schema,
        )
    message = str(exc.value)
    # The *second* node in sorted order is the one that conflicts.
    assert "node 'beta'" in message
    assert "channel 'decision'" in message
    assert "write-once" in message


def test_apply_updates_once_channel_conflicts_across_supersteps():
    schema = StateSchema.build({"decision": "once"})
    first = apply_updates({}, [("alpha", {"decision": "approve"})], schema)
    assert first == {"decision": "approve"}

    with pytest.raises(ChannelConflictError) as exc:
        apply_updates(first, [("beta", {"decision": "deny"})], schema)
    assert "node 'beta'" in str(exc.value)


def test_apply_updates_once_channel_allows_a_single_write():
    schema = StateSchema.build({"decision": "once"})
    merged = apply_updates({}, [("alpha", {"decision": "approve"})], schema)
    assert merged["decision"] == "approve"


def test_apply_updates_merge_conflict_is_wrapped_with_the_node_name():
    schema = StateSchema.build({"meta": "merge"})
    with pytest.raises(ChannelConflictError) as exc:
        apply_updates({}, [("alpha", {"meta": "not-a-dict"})], schema)
    message = str(exc.value)
    assert "node 'alpha'" in message
    assert "channel 'meta'" in message
