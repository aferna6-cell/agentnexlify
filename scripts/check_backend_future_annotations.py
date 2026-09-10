#!/usr/bin/env python3
"""Block new backend ``from __future__ import annotations`` violations.

Issue #823 tracks the known test-file violations that predate this guard.
The allowlist is intentionally exact and self-pruning: if a known violation is
removed, this check fails until that path is removed from ``KNOWN_VIOLATIONS``.
That prevents the baseline from silently becoming permanent while ensuring no
new backend violation can land in the meantime.
"""

from pathlib import Path
import re
import sys

BACKEND = Path("backend")
PATTERN = re.compile(
    r"^[ \t]*from __future__ import annotations(?:[ \t]*(?:#.*)?)?$",
    re.MULTILINE,
)

KNOWN_VIOLATIONS = {
    Path("backend/tests/test_website_connect.py"),
    Path("backend/tests/test_local_seo_handlers.py"),
}


def find_violations() -> set[Path]:
    violations: set[Path] = set()
    for path in BACKEND.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"ERROR: could not decode {path} as UTF-8", file=sys.stderr)
            raise
        if PATTERN.search(text):
            violations.add(path)
    return violations


def main() -> int:
    actual = find_violations()
    unexpected = actual - KNOWN_VIOLATIONS
    cleaned = KNOWN_VIOLATIONS - actual

    if unexpected:
        print("FAIL: new backend future-annotations violations found:")
        for path in sorted(unexpected):
            print(f"  - {path}")

    if cleaned:
        print("FAIL: known violations were cleaned but remain allowlisted:")
        for path in sorted(cleaned):
            print(f"  - {path}")
        print("Remove cleaned paths from KNOWN_VIOLATIONS in this script.")

    if unexpected or cleaned:
        return 1

    print(
        "OK: backend future-annotations baseline unchanged "
        f"({len(actual)} known violation(s)); no new violations."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
