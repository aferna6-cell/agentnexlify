"""Tests for backend.graph.registry — name+version graph lookup.

The registry is module-global, so every test runs against a cleared registry
that is restored afterwards; a leaked registration would otherwise turn
``duplicate registration raises`` into a false positive somewhere else.
"""

import pytest

from backend.graph import registry
from backend.graph.graph import Graph
from backend.graph.registry import _version_key, clear, get, names, register


@pytest.fixture(autouse=True)
def _clean_registry():
    saved = dict(registry._FACTORIES)
    clear()
    try:
        yield
    finally:
        clear()
        registry._FACTORIES.update(saved)


def _factory(name: str, version: str = "1"):
    def build() -> Graph:
        return Graph(name, version=version)

    return build


# ---------------------------------------------------------------------------
# register / get
# ---------------------------------------------------------------------------


def test_register_then_get_builds_the_graph():
    @register("lead_qualification")
    def build() -> Graph:
        return Graph("lead_qualification")

    graph = get("lead_qualification")
    assert isinstance(graph, Graph)
    assert graph.name == "lead_qualification"


def test_register_returns_the_factory_unchanged():
    factory = _factory("g")
    decorated = register("g")(factory)
    assert decorated is factory


def test_get_calls_the_factory_on_every_lookup():
    """Factories are lazy: a graph closing over settings is built when asked
    for, not at import time."""
    calls = {"n": 0}

    @register("lazy")
    def build() -> Graph:
        calls["n"] += 1
        return Graph("lazy")

    assert calls["n"] == 0
    first = get("lazy")
    second = get("lazy")
    assert calls["n"] == 2
    assert first is not second


def test_default_version_is_one():
    register("g")(_factory("g"))
    assert names() == [("g", "1")]
    assert get("g", "1").name == "g"


def test_duplicate_registration_raises():
    register("g")(_factory("g"))

    with pytest.raises(ValueError) as exc:
        register("g")(_factory("g"))
    assert "graph 'g' v1 is already registered" in str(exc.value)


def test_same_name_different_version_is_not_a_duplicate():
    register("g", version="1")(_factory("g", "1"))
    register("g", version="2")(_factory("g", "2"))
    assert names() == [("g", "1"), ("g", "2")]


# ---------------------------------------------------------------------------
# version resolution
# ---------------------------------------------------------------------------


def test_get_with_no_version_picks_the_highest():
    register("g", version="1")(_factory("g", "1"))
    register("g", version="3")(_factory("g", "3"))
    register("g", version="2")(_factory("g", "2"))

    assert get("g").version == "3"


def test_get_with_no_version_sorts_numerically_not_lexically():
    """'10' must win over '9' — string ordering would pick '9'."""
    register("g", version="9")(_factory("g", "9"))
    register("g", version="10")(_factory("g", "10"))

    assert get("g").version == "10"


def test_get_with_an_explicit_version_pins():
    register("g", version="1")(_factory("g", "1"))
    register("g", version="2")(_factory("g", "2"))

    assert get("g", "1").version == "1"


def test_version_key_sorts_ten_after_nine():
    assert _version_key("10") > _version_key("9")
    assert _version_key("2") > _version_key("1")


def test_version_key_handles_dotted_versions():
    assert _version_key("1.10") > _version_key("1.9")
    assert _version_key("2.0") > _version_key("1.99")


def test_version_key_falls_back_to_string_order_for_non_numeric_versions():
    assert _version_key("beta") == (1, "beta")
    # Numeric versions always sort before the string fallback bucket.
    assert _version_key("999") < _version_key("beta")


def test_get_with_no_version_tolerates_a_non_numeric_version():
    register("g", version="1")(_factory("g", "1"))
    register("g", version="beta")(_factory("g", "beta"))

    assert get("g").version == "beta"


# ---------------------------------------------------------------------------
# failure modes
# ---------------------------------------------------------------------------


def test_get_unknown_name_raises_key_error():
    with pytest.raises(KeyError) as exc:
        get("nope")
    assert "no graph registered under 'nope'" in exc.value.args[0]


def test_get_unknown_version_raises_key_error():
    register("g", version="1")(_factory("g", "1"))

    with pytest.raises(KeyError) as exc:
        get("g", "7")
    assert "no graph registered under 'g' v7" in exc.value.args[0]


# ---------------------------------------------------------------------------
# names / clear
# ---------------------------------------------------------------------------


def test_names_is_empty_on_a_fresh_registry():
    assert names() == []


def test_names_returns_sorted_name_version_pairs():
    register("zeta")(_factory("zeta"))
    register("alpha", version="2")(_factory("alpha", "2"))
    register("alpha", version="1")(_factory("alpha", "1"))

    assert names() == [("alpha", "1"), ("alpha", "2"), ("zeta", "1")]


def test_clear_drops_every_registration():
    register("g")(_factory("g"))
    clear()

    assert names() == []
    with pytest.raises(KeyError):
        get("g")
