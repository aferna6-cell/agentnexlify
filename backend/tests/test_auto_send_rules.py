"""Per-agent auto-send rules (gap G6) — resolve_deliverable_status gate.

Contract:
  - per-agent rule in tenants.os_auto_send_rules beats the global flag
  - never-auto-send agents cannot be overridden by rules
  - read failure always falls back to pending_approval
"""

from unittest.mock import MagicMock

from backend.services.agent_os_bridge import resolve_deliverable_status


def _db(enabled: bool, rules: dict | None):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"os_auto_send_enabled": enabled, "os_auto_send_rules": rules}]
    )
    return db


def test_per_agent_true_overrides_global_off():
    db = _db(enabled=False, rules={"booking": True})
    assert resolve_deliverable_status(db, "t1", "booking", False) == "approved"


def test_per_agent_false_overrides_global_on():
    db = _db(enabled=True, rules={"marketing": False})
    assert resolve_deliverable_status(db, "t1", "marketing", False) == "pending_approval"


def test_unlisted_agent_follows_global():
    db = _db(enabled=True, rules={"booking": True})
    assert resolve_deliverable_status(db, "t1", "generalist", False) == "approved"
    db = _db(enabled=False, rules={"booking": True})
    assert resolve_deliverable_status(db, "t1", "generalist", False) == "pending_approval"


def test_never_auto_send_agent_ignores_rules():
    # invoicing is in NEVER_AUTO_SEND_AGENTS — a rule cannot open the gate
    db = _db(enabled=True, rules={"invoicing": True})
    assert resolve_deliverable_status(db, "t1", "invoicing", False) == "pending_approval"


def test_engine_requires_approval_wins():
    db = _db(enabled=True, rules={"booking": True})
    assert resolve_deliverable_status(db, "t1", "booking", True) == "pending_approval"


def test_db_failure_forces_approval():
    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    assert resolve_deliverable_status(db, "t1", "booking", False) == "pending_approval"


def test_malformed_rules_fall_back_to_global():
    db = _db(enabled=True, rules="not-a-dict")  # type: ignore[arg-type]
    assert resolve_deliverable_status(db, "t1", "booking", False) == "approved"
