"""Live schema drift guard (CI + manual).

Diffs the LIVE Supabase schema (via the service-role-only RPC
``hot_table_columns()``, migration 136) against the committed manifest
``ops/schema/expected-columns.json``.

Why this exists: 2026-06-10 incident — migrations/001 listed referral columns
the live schema never had; code trusted the migration file and production
/register 500'd. Migration files prove nothing about the live DB.
See docs/dev-knowledge/bug-patterns.md "Migration files ≠ live schema".

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python scripts/check_schema_drift.py
    python scripts/check_schema_drift.py --update   # refresh manifest from live
    python scripts/check_schema_drift.py --strict   # unexpected columns also fail

Exit codes:
    0 — no drift (or only unexpected-new columns without --strict)
    1 — MISSING columns: manifest expects them, live DB lacks them (the
        code-breaking direction — backend may be writing to them)
    2 — could not reach the live DB / credentials absent

Stdlib only so CI needs no pip install.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "ops" / "schema" / "expected-columns.json"


def fetch_live_columns(url: str, service_key: str) -> dict[str, list[str]]:
    """Call the hot_table_columns() RPC; return {table: sorted columns}."""
    endpoint = f"{url.rstrip('/')}/rest/v1/rpc/hot_table_columns"
    request = urllib.request.Request(
        endpoint,
        data=b"{}",
        method="POST",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as resp:  # noqa: S310 - operator-owned endpoint
        rows = json.loads(resp.read())
    tables: dict[str, list[str]] = {}
    for row in rows:
        tables.setdefault(row["table_name"], []).append(row["column_name"])
    return {t: sorted(cols) for t, cols in tables.items()}


def diff_schema(expected: dict, live: dict) -> dict:
    """Return {table: {"missing": [...], "unexpected": [...]}} for drifted tables."""
    drift: dict[str, dict[str, list[str]]] = {}
    for table, exp_cols in expected.items():
        if table.startswith("_"):
            continue
        live_cols = set(live.get(table, []))
        if not live_cols:
            drift[table] = {"missing": sorted(exp_cols), "unexpected": []}
            continue
        missing = sorted(set(exp_cols) - live_cols)
        unexpected = sorted(live_cols - set(exp_cols))
        if missing or unexpected:
            drift[table] = {"missing": missing, "unexpected": unexpected}
    return drift


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true",
                        help="unexpected live columns also fail (default: warn)")
    parser.add_argument("--update", action="store_true",
                        help="rewrite the manifest from the live schema")
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY", ""
    )
    if not url or not key:
        print("SKIP: SUPABASE_URL / SUPABASE_SERVICE_KEY not set — cannot check live schema.")
        return 2

    try:
        live = fetch_live_columns(url, key)
    except Exception as exc:
        print(f"ERROR: could not fetch live columns: {exc}")
        return 2

    manifest = json.loads(MANIFEST_PATH.read_text())

    if args.update:
        comment = manifest.get("_comment", "")
        new_manifest = {"_comment": comment, **live}
        MANIFEST_PATH.write_text(json.dumps(new_manifest, indent=2, sort_keys=True) + "\n")
        print(f"Manifest refreshed from live schema: {MANIFEST_PATH}")
        return 0

    drift = diff_schema(manifest, live)
    if not drift:
        print(f"OK: live schema matches manifest for {len(live)} hot tables.")
        return 0

    has_missing = False
    for table, d in sorted(drift.items()):
        if d["missing"]:
            has_missing = True
            print(f"MISSING on live {table}: {', '.join(d['missing'])}"
                  "  <- code may be writing to columns that DO NOT EXIST")
        if d["unexpected"]:
            print(f"unexpected (new) on live {table}: {', '.join(d['unexpected'])}"
                  "  <- run --update to refresh the manifest")

    if has_missing:
        return 1
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
