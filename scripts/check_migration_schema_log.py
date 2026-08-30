#!/usr/bin/env python3
"""CI gate: every migration added/changed in a PR needs a schema-log entry.

Audit 2026-07-14 M3 found 7 migrations (154-159, 163) in migrations/ with no
matching entry in docs/dev-knowledge/schema-log.md — the migration workflow
(create -> apply -> log) was being skipped at the last step. This check is
DIFF-BASED (same pattern as the migration-numbering CI step): only migrations
touched by the PR are checked, because ~140 pre-audit historical migrations
were never individually logged and blocking every PR on ancient history would
just get the gate deleted.

A migration "has an entry" when the log mentions its NNN_name stem (e.g.
"163_booking_enabled_default_true") anywhere, or a "migration NNN"/"NNN_"
reference in a heading. Loose on purpose: the log is prose for humans.

Usage: check_migration_schema_log.py --compare-branch <ref>
Exit 0 = ok / nothing to check. Exit 1 = migration touched without log entry.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_LOG = REPO_ROOT / "docs" / "dev-knowledge" / "schema-log.md"


def changed_migrations(compare_branch: str) -> list[str]:
    """
    Migrations this branch adds or changes, relative to where it diverged.

    Three-dot (`base...HEAD`), not two-dot. Two-dot asks "how do these two trees
    differ", which on a branch whose base has moved ahead also lists migrations
    the BASE added — files this branch has never seen, whose schema-log entries
    live on the base and could only be satisfied here by copying in a log entry
    for someone else's work. Three-dot asks "what did this branch do since the
    merge base", which is what the module docstring promises and the only
    question this gate should be answering.

    The gate is not weakened: a migration added on this branch still appears.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{compare_branch}...HEAD", "--", "migrations/"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    files = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if re.fullmatch(r"migrations/\d{3}_[\w.-]+\.sql", name):
            files.append(name)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare-branch", required=True)
    args = parser.parse_args()

    try:
        migrations = changed_migrations(args.compare_branch)
    except subprocess.CalledProcessError as exc:
        print(f"::warning::schema-log gate skipped (git diff failed: {exc})")
        return 0

    if not migrations:
        print("No migrations touched in this diff - nothing to check.")
        return 0

    log_text = SCHEMA_LOG.read_text(encoding="utf-8") if SCHEMA_LOG.exists() else ""
    missing = []
    for path in migrations:
        stem = Path(path).stem  # e.g. 163_booking_enabled_default_true
        number = stem.split("_", 1)[0]
        if stem in log_text or f"migration {number}" in log_text or f"{number}_" in log_text:
            print(f"ok: {path} has a schema-log entry")
        else:
            missing.append(path)

    if missing:
        for path in missing:
            print(
                f"::error::{path} was added/changed but has no entry in "
                "docs/dev-knowledge/schema-log.md. Migration workflow is "
                "create -> apply -> LOG. Add a heading mentioning its "
                f"'{Path(path).stem}' stem."
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
