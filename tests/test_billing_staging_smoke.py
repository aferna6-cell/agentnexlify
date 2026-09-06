"""Billing staging smoke harness — dry-run only, no provider I/O."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

spec = importlib.util.spec_from_file_location(
    "billing_staging_smoke", SCRIPTS / "billing_staging_smoke.py"
)
assert spec is not None and spec.loader is not None
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

VALID = {
    "BILLING_SMOKE_CLIENT_ID": "11111111-1111-1111-1111-111111111111",
    "BILLING_SMOKE_ENV": "staging",
    "BILLING_SMOKE_CONFIRM_ENV": "staging",
    "INVOICE_ACTIONS_ENABLED": "1",
    "BILLING_SMOKE_INVOICE_ID": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    "BILLING_SMOKE_CUSTOMER_EMAIL": "steve@example.com",
}


def _valid_env(monkeypatch, extra=None):
    for key, value in VALID.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("BILLING_SMOKE_EXECUTE", raising=False)
    for key, value in (extra or {}).items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


class TestSequenceAndDryRun:
    def test_prints_exact_create_approve_send_verify_reminder_sequence(self, monkeypatch):
        _valid_env(monkeypatch)
        report = harness.run_harness()
        assert report["sequence"] == [
            "create",
            "approve",
            "send",
            "verify",
            "overdue-reminder",
        ]
        assert report["mode"] == "dry-run"
        assert report["executed"] is False
        assert report["provider_calls"] == []
        assert report["deployed"] is False
        assert report["ready_for_dry_run"] is True
        text = harness.format_report(report)
        assert "create → approve → send → verify → overdue-reminder" in text

    def test_default_cli_is_dry_run(self, monkeypatch, capsys):
        _valid_env(monkeypatch)
        code = harness.main([])
        out = capsys.readouterr().out
        assert code == 0
        assert "mode: dry-run" in out
        assert "executed: False" in out
        payload = json.loads(out[out.index("{") :])
        assert payload["executed"] is False
        assert payload["provider_calls"] == []


class TestConfigValidation:
    def test_requires_tenant_uuid(self, monkeypatch):
        _valid_env(monkeypatch, {"BILLING_SMOKE_CLIENT_ID": "not-a-uuid"})
        report = harness.run_harness()
        assert report["ready_for_dry_run"] is False
        assert any("UUID" in item for item in report["blockers"])

    def test_refuses_non_staging_env(self, monkeypatch):
        _valid_env(
            monkeypatch,
            {"BILLING_SMOKE_ENV": "production", "BILLING_SMOKE_CONFIRM_ENV": "production"},
        )
        report = harness.run_harness()
        assert report["checks"]["env_staging"] is False
        assert report["ready_for_dry_run"] is False

    def test_reports_invoice_feature_flag(self, monkeypatch):
        _valid_env(monkeypatch, {"INVOICE_ACTIONS_ENABLED": "0"})
        report = harness.run_harness()
        assert report["checks"]["feature_flag"] == "INVOICE_ACTIONS_ENABLED"
        assert report["checks"]["feature_flag_on"] is False
        assert any("INVOICE_ACTIONS_ENABLED" in item for item in report["blockers"])

    def test_rejects_non_test_customer_email(self, monkeypatch):
        _valid_env(
            monkeypatch,
            {
                "BILLING_SMOKE_INVOICE_ID": None,
                "BILLING_SMOKE_CUSTOMER_EMAIL": "owner@sunsetauto.com",
            },
        )
        report = harness.run_harness()
        assert report["checks"]["test_invoice_target"] is False
        assert any("test inbox" in item for item in report["blockers"])

    def test_requires_a_test_invoice_target(self, monkeypatch):
        _valid_env(
            monkeypatch,
            {"BILLING_SMOKE_INVOICE_ID": None, "BILLING_SMOKE_CUSTOMER_EMAIL": None},
        )
        report = harness.run_harness()
        assert any("test invoice target" in item for item in report["blockers"])


class TestExecuteFlagStaysUnexecuted:
    def test_cli_execute_does_not_send(self, monkeypatch, capsys):
        _valid_env(monkeypatch)
        code = harness.main(["--execute"])
        out = capsys.readouterr().out
        assert code == 3
        assert "executed: False" in out
        assert "unexecuted" in out
        payload = json.loads(out[out.index("{") :])
        assert payload["execute_requested"] is True
        assert payload["executed"] is False
        assert payload["provider_calls"] == []

    def test_env_execute_flag_does_not_send(self, monkeypatch):
        _valid_env(monkeypatch, {"BILLING_SMOKE_EXECUTE": "1"})
        report = harness.run_harness()
        assert report["execute_requested"] is True
        assert report["executed"] is False
        assert report["provider_calls"] == []
        assert report["ready_for_dry_run"] is False


class TestNoSecretsInOutput:
    def test_redacts_secret_patterns_and_never_prints_service_key(self, monkeypatch, capsys):
        _valid_env(monkeypatch)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa")
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_1234567890secret")
        code = harness.main([])
        out = capsys.readouterr().out
        assert code == 0
        assert "sk_test_" not in out
        assert "eyJhbGci" not in out
        assert "sk-ant-" not in out
        assert "sk_live_" not in out
        assert "whsec_" not in out
        assert "sb_secret_" not in out
        assert re.search(r"\bre_[A-Za-z0-9]{8,}", out) is None

    def test_public_report_raises_if_secret_leaks_into_payload(self, monkeypatch):
        _valid_env(monkeypatch)
        dirty = harness.run_harness()
        dirty["blockers"].append("sk_live_should_never_print")
        with pytest.raises(AssertionError):
            harness._public_report(dirty)
