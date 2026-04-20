#!/usr/bin/env python3
"""
backfill_frontmatter.py — idempotent frontmatter backfill for memory files.

Adds missing fields to ~/.claude/projects/.../memory/*.md:
  confidence: 0.0-1.0  (default 0.8)
  last_verified: ISO8601 (default file mtime)
  access_count: int     (default 0)

Skips MEMORY.md index. Re-run is a no-op if fields already present.

Usage:
    python scripts/memory/backfill_frontmatter.py [--dry-run] [--memory-dir PATH]
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MEMORY_DIR = (
    Path.home() / ".claude/projects/-home-aidan-agentnexlify/memory"
)

NEW_FIELDS = ["confidence", "last_verified", "access_count"]
DEFAULTS = {
    "confidence": "0.8",
    "last_verified": None,  # computed per-file from mtime
    "access_count": "0",
}

# ── Frontmatter parsing ───────────────────────────────────────────────────────

_FM_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
_KV_RE = re.compile(r"^([A-Za-z_]\w*):\s*(.*)$")


def _parse(content: str) -> tuple[dict, list, str]:
    """Return (fields, ordered_keys, body). Empty dict if no frontmatter."""
    m = _FM_RE.match(content)
    if not m:
        return {}, [], content

    fields: dict = {}
    ordered: list = []
    for line in m.group(1).splitlines():
        kv = _KV_RE.match(line)
        if kv:
            key, val = kv.group(1), kv.group(2).strip()
            fields[key] = val
            ordered.append(key)

    body = content[m.end():]
    return fields, ordered, body


def _build_frontmatter(fields: dict, ordered: list) -> str:
    seen: set = set()
    lines = ["---"]
    for key in ordered:
        lines.append(f"{key}: {fields[key]}")
        seen.add(key)
    # Append any keys added outside of ordered (shouldn't happen, but safe)
    for key in fields:
        if key not in seen:
            lines.append(f"{key}: {fields[key]}")
    lines.append("---")
    return "\n".join(lines) + "\n"


# ── Per-file processing ───────────────────────────────────────────────────────

def _mtime_iso(path: Path) -> str:
    ts = path.stat().st_mtime
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def process_file(path: Path, dry_run: bool) -> dict:
    """
    Process one memory file.

    Returns:
        {
            "path": str,
            "changed": bool,
            "added": list[str],        # fields added
            "skipped": bool,
            "skip_reason": str | None,
        }
    """
    result = {
        "path": str(path),
        "changed": False,
        "added": [],
        "skipped": False,
        "skip_reason": None,
    }

    content = path.read_text(encoding="utf-8")
    fields, ordered, body = _parse(content)

    if not fields:
        result["skipped"] = True
        result["skip_reason"] = "no YAML frontmatter found"
        return result

    defaults_with_mtime = {**DEFAULTS, "last_verified": _mtime_iso(path)}

    added = []
    for field in NEW_FIELDS:
        if field not in fields:
            fields[field] = defaults_with_mtime[field]
            ordered.append(field)
            added.append(field)

    if not added:
        return result  # nothing to do — idempotent

    result["changed"] = True
    result["added"] = added

    if not dry_run:
        new_content = _build_frontmatter(fields, ordered) + body
        path.write_text(new_content, encoding="utf-8")

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill memory frontmatter fields (confidence, last_verified, access_count)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report diffs without writing any files.",
    )
    parser.add_argument(
        "--memory-dir",
        type=Path,
        default=DEFAULT_MEMORY_DIR,
        help=f"Path to memory directory (default: {DEFAULT_MEMORY_DIR})",
    )
    args = parser.parse_args(argv)

    memory_dir: Path = args.memory_dir
    if not memory_dir.is_dir():
        print(f"ERROR: memory dir not found: {memory_dir}", file=sys.stderr)
        return 1

    files = sorted(f for f in memory_dir.glob("*.md") if f.name != "MEMORY.md")
    if not files:
        print(f"No .md files found in {memory_dir}")
        return 0

    changed_count = 0
    skipped_count = 0

    for path in files:
        result = process_file(path, dry_run=args.dry_run)

        if result["skipped"]:
            print(f"  SKIP  {path.name} ({result['skip_reason']})")
            skipped_count += 1
        elif result["changed"]:
            mode = "DRY-RUN" if args.dry_run else "UPDATED"
            print(f"  {mode}  {path.name}  +{', '.join(result['added'])}")
            changed_count += 1
        else:
            print(f"  OK    {path.name}")

    print()
    if args.dry_run:
        print(f"Dry run: {changed_count} file(s) would be updated, {skipped_count} skipped.")
    else:
        print(f"Done: {changed_count} file(s) updated, {skipped_count} skipped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
