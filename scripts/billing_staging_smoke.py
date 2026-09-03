#!/usr/bin/env python3
"""Controlled billing staging smoke harness.

Default is dry-run: validate config/tenant/feature flag/test invoice target
and print the create → approve → send → verify → overdue-reminder sequence.
No provider I/O. No deploy.

A real send requires the separate ``--execute`` / ``BILLING_SMOKE_EXECUTE=1``
flag. This follow-up still leaves that path unexecuted.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.m8_action_flags import INVOICE_ACTIONS_FLAG

SEQUENCE = (
    "create",
    "approve",
    "send",
    "verify",
    "overdue-reminder",
)

SECRET_ENV_KEYS = (
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_ANON_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "ANTHROPIC_API_KEY",
    "RESEND_API_KEY",
    "TWILIO_AUTH_TOKEN",
    "BILLING_SMOKE_LOGIN_PASSWORD",
)

_SECRET_VALUE_RE = re.compile(
    r"(sk_live_[A-Za-z0-9]+|sk_test_[A-Za-z0-9]+|sk-ant-[A-Za-z0-9_-]+|"
    r"re_[A-Za-z0-9]{8,}|whsec_[A-Za-z0-9]+|sb_secret_[A-Za-z0-9]+|"
    r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)
_TEST_EMAIL_RE = re.compile(
    r"^[^\s@]+@(example\.com|example\.test|agentnexlify\.invalid)$",
    re.IGNORECASE,
)


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _redact(value: str | None) -> str:
    if not value:
        return ""
    if _SECRET_VALUE_RE.search(value):
        return "•••redacted•••"
    if len(value) > 8 and value.lower() in {
        os.environ.get(k, "").strip().lower() for k in SECRET_ENV_KEYS if os.environ.get(k)
    }:
        return "•••redacted•••"
    return value


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def validate_config(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Validate tenant, staging confirmation, invoice flag, and test target."""
    src = env if env is not None else os.environ
    blockers: list[str] = []

    client_id = (src.get("BILLING_SMOKE_CLIENT_ID") or "").strip()
    if not client_id:
        blockers.append("BILLING_SMOKE_CLIENT_ID required")
    elif not _is_uuid(client_id):
        blockers.append("BILLING_SMOKE_CLIENT_ID must be a UUID tenant id")

    env_name = (src.get("BILLING_SMOKE_ENV") or "").strip().lower()
    confirm = (src.get("BILLING_SMOKE_CONFIRM_ENV") or "").strip().lower()
    if env_name != "staging" or confirm != "staging":
        blockers.append(
            "BILLING_SMOKE_ENV=staging and BILLING_SMOKE_CONFIRM_ENV=staging required"
        )

    flag_raw = (src.get(INVOICE_ACTIONS_FLAG) or "").strip()
    flag_on = flag_raw.lower() in {"1", "true", "yes", "on"}
    if not flag_on:
        blockers.append(f"{INVOICE_ACTIONS_FLAG} must be on for a live send path")

    invoice_id = (src.get("BILLING_SMOKE_INVOICE_ID") or "").strip()
    customer_email = (src.get("BILLING_SMOKE_CUSTOMER_EMAIL") or "").strip()
    if invoice_id and not _is_uuid(invoice_id):
        blockers.append("BILLING_SMOKE_INVOICE_ID must be a UUID")
    if customer_email and not _TEST_EMAIL_RE.match(customer_email):
        blockers.append(
            "BILLING_SMOKE_CUSTOMER_EMAIL must be a test inbox "
            "(@example.com, @example.test, or @agentnexlify.invalid)"
        )
    if not invoice_id and not customer_email:
        blockers.append(
            "test invoice target required: BILLING_SMOKE_INVOICE_ID or "
            "BILLING_SMOKE_CUSTOMER_EMAIL"
        )

    return {
        "ok": not blockers,
        "blockers": blockers,
        "tenant_id": client_id if _is_uuid(client_id) else "",
        "env": env_name or "",
        "confirm_env": confirm or "",
        "feature_flag": INVOICE_ACTIONS_FLAG,
        "feature_flag_on": flag_on,
        "invoice_id": invoice_id if _is_uuid(invoice_id) else "",
        "customer_email": customer_email if _TEST_EMAIL_RE.match(customer_email) else "",
    }


def planned_sequence() -> list[dict[str, str]]:
    """Exact staging sequence. Send stays parked until owner approve."""
    notes = {
        "create": "create_invoice_draft (L1 persist; no provider)",
        "approve": "owner approve of parked send_invoice (no send before this)",
        "send": "execute send_invoice after approve (provider; requires --execute)",
        "verify": "verification_state=passed and invoice status=sent",
        "overdue-reminder": "send_invoice_reminder after overdue (provider; requires --execute)",
    }
    return [{"step": step, "detail": notes[step]} for step in SEQUENCE]


def execute_requested(args_execute: bool = False) -> bool:
    return bool(args_execute) or _truthy("BILLING_SMOKE_EXECUTE")


def run_harness(*, execute: bool = False, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Dry-run by default. Even with execute=True, send remains unexecuted."""
    checks = validate_config(env)
    wanted_execute = execute_requested(execute)
    report = {
        "mode": "execute" if wanted_execute else "dry-run",
        "sequence": [step["step"] for step in planned_sequence()],
        "steps": planned_sequence(),
        "checks": {
            "tenant": bool(checks["tenant_id"]),
            "env_staging": checks["env"] == "staging" and checks["confirm_env"] == "staging",
            "feature_flag": checks["feature_flag"],
            "feature_flag_on": checks["feature_flag_on"],
            "test_invoice_target": bool(checks["invoice_id"] or checks["customer_email"]),
        },
        "blockers": list(checks["blockers"]),
        "execute_requested": wanted_execute,
        "executed": False,
        "provider_calls": [],
        "deployed": False,
        "secrets_emitted": False,
    }
    if wanted_execute:
        report["blockers"].append(
            "execute flag set but live send remains unexecuted in this harness"
        )
    report["ready_for_dry_run"] = checks["ok"] and not wanted_execute
    return report


def _public_report(report: dict[str, Any]) -> dict[str, Any]:
    blob = json.dumps(report)
    if _SECRET_VALUE_RE.search(blob):
        raise AssertionError("refusing to print a report that contains a secret pattern")
    for key in SECRET_ENV_KEYS:
        raw = os.environ.get(key, "")
        if raw and raw in blob:
            raise AssertionError(f"refusing to print {key}")
    return report


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "BILLING STAGING SMOKE",
        f"mode: {report['mode']}",
        "sequence: " + " → ".join(report["sequence"]),
        "",
        "steps:",
    ]
    for item in report["steps"]:
        lines.append(f"  {item['step']}: {item['detail']}")
    lines.extend(
        [
            "",
            "checks:",
            f"  tenant: {report['checks']['tenant']}",
            f"  env_staging: {report['checks']['env_staging']}",
            f"  {report['checks']['feature_flag']}: {report['checks']['feature_flag_on']}",
            f"  test_invoice_target: {report['checks']['test_invoice_target']}",
            f"execute_requested: {report['execute_requested']}",
            f"executed: {report['executed']}",
            f"provider_calls: {report['provider_calls']}",
            f"deployed: {report['deployed']}",
        ]
    )
    if report["blockers"]:
        lines.append("blockers:")
        lines.extend(f"  - {item}" for item in report["blockers"])
    else:
        lines.append("blockers: none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Billing staging smoke (dry-run default)")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="request the live send path (still unexecuted in this follow-up)",
    )
    args = parser.parse_args(argv)
    report = _public_report(run_harness(execute=args.execute))
    print(format_report(report))
    print(json.dumps(report, indent=2))
    if report["execute_requested"]:
        return 3
    if not report["ready_for_dry_run"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
