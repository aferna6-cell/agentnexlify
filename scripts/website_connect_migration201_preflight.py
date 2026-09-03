#!/usr/bin/env python3
"""Migration 201 check-only preflight + Website Connect staging checklist.

Never applies the migration. Never deploys. Refuses --apply / APPLY flags.
Prints rollback, preconditions, and the connect → fetch → tenant widget key
→ connected sequence, including bot-blocked-site behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MIGRATION = ROOT / "migrations" / "201_website_connections.sql"
SCHEMA_LOG = ROOT / "docs" / "dev-knowledge" / "schema-log.md"

SEQUENCE = (
    "connect",
    "fetch",
    "tenant-widget-key",
    "connected",
)

REQUIRED_SQL = (
    "CREATE TABLE IF NOT EXISTS website_connections",
    "tenant_id",
    "REFERENCES tenants(id) ON DELETE CASCADE",
    "UNIQUE (tenant_id)",
    "ENABLE ROW LEVEL SECURITY",
    "website_connections_deny_public",
    "TO public",
    "USING (false)",
    "website_connections_service_role",
    "TO service_role",
)

ROLLBACK_MARKERS = (
    "Rollback",
    "drop table if exists website_connections",
)

PRECONDITIONS = (
    "Migration 201 is present in the repo and logged as NOT applied",
    "Do not apply schema or deploy from this harness",
    "Tenant JWT scope + widget_configs.api_key for this tenant only",
    "Public http(s) URL; no CMS passwords accepted or stored",
    "connected requires a live <script> tag for agentnexlify-widget.js with this tenant data-api-key",
    "Bot-blocked / fetch-fail sites stay failed or needs_action, never connected",
)


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def apply_requested(args_apply: bool = False) -> bool:
    return bool(args_apply) or _truthy("WEBSITE_CONNECT_APPLY") or _truthy("APPLY_MIGRATION_201")


def inspect_migration() -> dict:
    blockers: list[str] = []
    if not MIGRATION.is_file():
        return {
            "ok": False,
            "blockers": ["migrations/201_website_connections.sql is missing"],
            "sql_markers": [],
            "rollback_documented": False,
            "schema_log_not_applied": False,
        }

    sql = MIGRATION.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_SQL if marker not in sql]
    if missing:
        blockers.append("migration 201 missing required markers: " + ", ".join(missing))

    rollback_documented = all(marker.lower() in sql.lower() for marker in ROLLBACK_MARKERS)
    if not rollback_documented:
        blockers.append("migration 201 must document rollback: drop table if exists website_connections")

    log_text = SCHEMA_LOG.read_text(encoding="utf-8") if SCHEMA_LOG.is_file() else ""
    logged = "201_website_connections" in log_text
    not_applied = "NOT applied" in log_text and "201_website_connections" in log_text
    if not logged:
        blockers.append("docs/dev-knowledge/schema-log.md must mention 201_website_connections")
    if not not_applied:
        blockers.append("schema-log must record migration 201 as NOT applied")

    present = [marker for marker in REQUIRED_SQL if marker in sql]
    return {
        "ok": not blockers,
        "blockers": blockers,
        "sql_markers": present,
        "rollback_documented": rollback_documented,
        "schema_log_not_applied": not_applied,
        "applied": False,
    }


def planned_sequence() -> list[dict[str, str]]:
    notes = {
        "connect": "POST /api/v1/website-connect with a public URL (no CMS password)",
        "fetch": "Pinned-IP public GET; Host + SNI stay on the original hostname",
        "tenant-widget-key": "widget_configs.api_key for this tenant on the widget <script> tag",
        "connected": "status=connected only after live HTML has this tenant key; never from self-report",
    }
    return [{"step": step, "detail": notes[step]} for step in SEQUENCE]


def bot_blocked_behavior() -> dict[str, str]:
    return {
        "trigger": "fetch fail / http_403 / bot challenge / timeout",
        "upsert_status": "needs_action",
        "verify_status": "failed",
        "never": "connected",
        "detail": "Could not reach the website to verify. Install still required.",
    }


def run_preflight(*, apply: bool = False) -> dict:
    wanted_apply = apply_requested(apply)
    inspection = inspect_migration()
    report = {
        "mode": "check-only",
        "sequence": [step["step"] for step in planned_sequence()],
        "steps": planned_sequence(),
        "preconditions": list(PRECONDITIONS),
        "rollback": {
            "sql": "drop table if exists website_connections;",
            "documented": inspection["rollback_documented"],
            "executed": False,
        },
        "migration": {
            "file": "migrations/201_website_connections.sql",
            "ok": inspection["ok"],
            "applied": False,
            "schema_log_not_applied": inspection["schema_log_not_applied"],
            "sql_markers": inspection["sql_markers"],
        },
        "bot_blocked": bot_blocked_behavior(),
        "apply_requested": wanted_apply,
        "applied": False,
        "deployed": False,
        "blockers": list(inspection["blockers"]),
    }
    if wanted_apply:
        report["blockers"].append(
            "apply/deploy is refused: this harness is check-only and does not apply migration 201"
        )
    report["ready"] = inspection["ok"] and not wanted_apply
    return report


def format_report(report: dict) -> str:
    lines = [
        "WEBSITE CONNECT STAGING READINESS",
        f"mode: {report['mode']}",
        "sequence: " + " → ".join(report["sequence"]),
        "",
        "preconditions:",
    ]
    lines.extend(f"  - {item}" for item in report["preconditions"])
    lines.extend(
        [
            "",
            "rollback:",
            f"  sql: {report['rollback']['sql']}",
            f"  documented: {report['rollback']['documented']}",
            f"  executed: {report['rollback']['executed']}",
            "",
            "steps:",
        ]
    )
    for item in report["steps"]:
        lines.append(f"  {item['step']}: {item['detail']}")
    blocked = report["bot_blocked"]
    lines.extend(
        [
            "",
            "bot-blocked site:",
            f"  trigger: {blocked['trigger']}",
            f"  upsert: {blocked['upsert_status']} / verify: {blocked['verify_status']}",
            f"  never: {blocked['never']}",
            f"migration_applied: {report['migration']['applied']}",
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
    parser = argparse.ArgumentParser(
        description="Migration 201 check-only preflight (never applies)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="refused: this harness never applies schema",
    )
    args = parser.parse_args(argv)
    report = run_preflight(apply=args.apply)
    print(format_report(report))
    print(json.dumps(report, indent=2))
    if report["apply_requested"] or report["applied"]:
        return 3
    if not report["ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
