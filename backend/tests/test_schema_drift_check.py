"""Tests for the schema drift diff logic (scripts/check_schema_drift.py).

Born from the 2026-06-10 incident: migrations/001 listed referral columns the
live schema never had — code trusted the file, prod /register 500'd.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from scripts.check_schema_drift import diff_schema


def test_match_returns_empty():
    expected = {"tenants": ["id", "plan"], "_comment": "ignored"}
    live = {"tenants": ["id", "plan"]}
    assert diff_schema(expected, live) == {}


def test_missing_column_detected():
    # The exact incident shape: manifest/code expects referral_code, live lacks it
    expected = {"tenants": ["id", "plan", "referral_code"]}
    live = {"tenants": ["id", "plan"]}
    drift = diff_schema(expected, live)
    assert drift["tenants"]["missing"] == ["referral_code"]
    assert drift["tenants"]["unexpected"] == []


def test_unexpected_column_detected():
    expected = {"tenants": ["id", "plan"]}
    live = {"tenants": ["id", "plan", "new_col"]}
    drift = diff_schema(expected, live)
    assert drift["tenants"]["unexpected"] == ["new_col"]
    assert drift["tenants"]["missing"] == []


def test_whole_table_missing_live():
    expected = {"ghost_table": ["id"]}
    drift = diff_schema(expected, {})
    assert drift["ghost_table"]["missing"] == ["id"]


def test_comment_key_ignored():
    assert diff_schema({"_comment": "x"}, {}) == {}


def test_manifest_matches_repo_file():
    """The committed manifest parses and covers the full live schema.

    Migration 140 (audit H3) expanded the guard from 7 hot tables to every
    public table — the old exact-set assertion is now a superset check.
    """
    import json
    from pathlib import Path

    manifest = json.loads(
        (Path(__file__).resolve().parent.parent.parent / "ops/schema/expected-columns.json").read_text()
    )
    tables = {k for k in manifest if not k.startswith("_")}
    # the original hot tables must always stay covered
    assert {
        "tenants", "leads", "conversations", "invoices",
        "appointments", "chat_messages", "widget_configs",
    } <= tables
    # full-schema expansion: far more than the original 7
    assert len(tables) > 100
    # The incident columns are pinned in the manifest now
    assert "referral_code" in manifest["tenants"]
    assert "client_id" in manifest["leads"]
    assert "client_id" in manifest["conversations"]
    # G6 column from migration 141
    assert "os_auto_send_rules" in manifest["tenants"]
