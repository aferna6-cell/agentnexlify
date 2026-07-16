"""Routing memory v1 — owner corrections become standing routing preferences.

Contract:
  1. ``learned_agent_for`` returns the corrected department when a new ask
     is highly similar (token Jaccard >= 0.7) to an ask the owner previously
     re-routed, and None otherwise. Deterministic - no LLM.
  2. Only known department ids are ever returned; junk in changed_to is
     ignored. Most recent qualifying correction wins.
  3. ``resolve_force_agent`` passes an explicit force_agent_id through
     untouched and falls back to the learned route only when none is given.
  4. Never raises - any DB failure degrades to None (classifier decides).
"""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.os_routing_memory import (
    _similarity,
    learned_agent_for,
    resolve_force_agent,
)

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


def _db(rows, raise_on_query=False):
    db = MagicMock()
    chain = MagicMock()
    for attr in ("select", "eq", "not_", "is_", "gte", "order", "limit", "or_"):
        getattr(chain, attr).return_value = chain
    if raise_on_query:
        chain.execute.side_effect = RuntimeError("db down")
    else:
        chain.execute.return_value = MagicMock(data=rows)
    db.table.return_value = chain
    return db


def _override(ask, target, decision="routed", changed_to=None, chosen=None):
    return {
        "ask": ask,
        "decision": decision,
        "chosen_agent": chosen or target,
        "changed_to": changed_to,
        "created_at": "2026-07-10T00:00:00+00:00",
    }


# --- similarity ---------------------------------------------------------------
def test_similarity_identical_and_disjoint():
    assert _similarity("send tomorrow's reminders", "send tomorrow's reminders") == 1.0
    assert _similarity("send reminders", "write a blog post") == 0.0


def test_similarity_ignores_stopwords_and_case():
    a = "Please send the reminders for tomorrow"
    b = "send reminders tomorrow"
    assert _similarity(a, b) == 1.0


def test_similarity_empty_asks_are_zero():
    assert _similarity("", "anything") == 0.0
    assert _similarity("the a an", "the a an") == 0.0  # all stopwords


# --- learned_agent_for ----------------------------------------------------------
def test_returns_correction_for_near_identical_ask():
    rows = [
        _override(
            "send our customers the spring promo",
            None,
            changed_to="marketing",
        )
    ]
    got = learned_agent_for(_db(rows), _TENANT, "send customers the spring promo")
    assert got == "marketing"


def test_owner_override_rows_also_teach():
    rows = [
        _override(
            "chase the wallace invoice again",
            "invoicing",
            decision="owner_override",
            chosen="invoicing",
        )
    ]
    got = learned_agent_for(_db(rows), _TENANT, "chase the Wallace invoice again")
    assert got == "invoicing"


def test_low_similarity_returns_none():
    rows = [_override("send the spring promo", None, changed_to="marketing")]
    assert learned_agent_for(_db(rows), _TENANT, "book Mike for Thursday") is None


def test_unknown_agent_id_is_ignored():
    rows = [_override("send the spring promo", None, changed_to="not_a_dept")]
    assert learned_agent_for(_db(rows), _TENANT, "send the spring promo") is None


def test_no_overrides_returns_none():
    assert learned_agent_for(_db([]), _TENANT, "send the spring promo") is None


def test_db_failure_returns_none():
    assert (
        learned_agent_for(_db([], raise_on_query=True), _TENANT, "send the promo")
        is None
    )


def test_most_recent_qualifying_correction_wins():
    rows = [
        dict(
            _override("send the spring promo", None, changed_to="sales"),
            created_at="2026-07-12T00:00:00+00:00",
        ),
        dict(
            _override("send the spring promo", None, changed_to="marketing"),
            created_at="2026-07-01T00:00:00+00:00",
        ),
    ]
    # Rows arrive most-recent-first (the query orders desc); first hit wins.
    got = learned_agent_for(_db(rows), _TENANT, "send the spring promo")
    assert got == "sales"


# --- resolve_force_agent ----------------------------------------------------------
def test_explicit_force_agent_wins():
    rows = [_override("send the spring promo", None, changed_to="marketing")]
    got = resolve_force_agent(_db(rows), _TENANT, "send the spring promo", "operations")
    assert got == "operations"


def test_falls_back_to_learned_when_no_explicit():
    rows = [_override("send the spring promo", None, changed_to="marketing")]
    got = resolve_force_agent(_db(rows), _TENANT, "send the spring promo", None)
    assert got == "marketing"


def test_returns_none_when_nothing_learned():
    assert resolve_force_agent(_db([]), _TENANT, "hello there", None) is None
