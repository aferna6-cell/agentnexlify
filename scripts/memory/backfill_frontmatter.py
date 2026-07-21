#!/usr/bin/env python3
"""Backfill memory-hygiene frontmatter (issue #68).

Adds three managed fields to each memory ``*.md`` file's YAML frontmatter:

    confidence:     float 0.0-1.0   (default 0.8)
    last_verified:  ISO-8601 string (default the file's mtime)
    access_count:   int             (default 0)

Design:
  * Line-based, NOT a YAML round-trip — existing fields, their order, and the
    article body are preserved byte-for-byte; only the missing managed fields
    are appended to the frontmatter block.
  * Idempotent — a second run is a no-op (every managed field already present).
  * Never touches the ``MEMORY.md`` index (issue #68 constraint).
  * No new dependencies (stdlib only).

The memory directory is resolved (never hardcoded to a user-specific path, per
the issue #68 reimplementation note):
  1. ``--dir PATH`` argument, else
  2. ``CLAUDE_MEMORY_DIR`` environment variable, else
  3. the Claude Code per-project convention:
     ``~/.claude/projects/<cwd-with-slashes-as-dashes>/memory``.

Usage:
    python3 scripts/memory/backfill_frontmatter.py [--dir PATH] [--dry-run]
"""

import argparse
import difflib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

DEFAULT_CONFIDENCE = "0.8"
INDEX_FILENAME = "MEMORY.md"
MANAGED_FIELDS = ("confidence", "last_verified", "access_count")

# Frontmatter is a leading ``---`` fence, YAML body, and a closing ``---`` fence.
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


def default_memory_dir() -> Path:
    """Resolve the memory directory without hardcoding a user-specific slug."""
    env = os.environ.get("CLAUDE_MEMORY_DIR")
    if env:
        return Path(env).expanduser()
    cwd = Path.cwd().resolve()
    slug = str(cwd).replace(os.sep, "-")
    return Path.home() / ".claude" / "projects" / slug / "memory"


def _iso_mtime(path: Path) -> str:
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return ts.replace(microsecond=0).isoformat()


def _top_level_keys(frontmatter_block: str) -> set:
    """Top-level YAML keys (column-0, no indentation) in the frontmatter block."""
    keys = set()
    for line in frontmatter_block.split("\n"):
        if not line or line[0].isspace():
            continue  # blank line, list item, or nested/indented key
        if ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys


def build_updated(text: str, path: Path) -> str:
    """Return ``text`` with any missing managed fields appended to frontmatter.

    Returns ``text`` unchanged when every managed field is already present
    (idempotent) — including files that never had frontmatter on a re-run.
    """
    match = _FRONTMATTER_RE.match(text)
    if match:
        block = match.group(1)
        body = text[match.end():]
        had_frontmatter = True
    else:
        block = ""
        body = text
        had_frontmatter = False

    present = _top_level_keys(block)
    additions: List[str] = []
    for field in MANAGED_FIELDS:
        if field in present:
            continue
        if field == "confidence":
            additions.append(f"confidence: {DEFAULT_CONFIDENCE}")
        elif field == "last_verified":
            additions.append(f"last_verified: {_iso_mtime(path)}")
        elif field == "access_count":
            additions.append("access_count: 0")

    if not additions:
        return text  # nothing to do — idempotent no-op

    if had_frontmatter and block:
        new_block = block + "\n" + "\n".join(additions)
    else:
        new_block = "\n".join(additions)

    if had_frontmatter:
        return f"---\n{new_block}\n---\n{body}"
    # No prior frontmatter: prepend a block, keep the original body verbatim.
    if body:
        return f"---\n{new_block}\n---\n{body}"
    return f"---\n{new_block}\n---\n"


def _iter_memory_files(memory_dir: Path) -> List[Path]:
    return sorted(
        p
        for p in memory_dir.glob("**/*.md")
        if p.is_file() and p.name != INDEX_FILENAME
    )


def process(memory_dir: Path, dry_run: bool = False) -> Tuple[int, int, int]:
    """Backfill every memory file. Returns (scanned, updated, unchanged)."""
    if not memory_dir.exists():
        print(f"memory dir not found: {memory_dir} — nothing to backfill")
        return (0, 0, 0)

    files = _iter_memory_files(memory_dir)
    scanned = updated = unchanged = 0
    for path in files:
        scanned += 1
        original = path.read_text(encoding="utf-8")
        rebuilt = build_updated(original, path)
        if rebuilt == original:
            unchanged += 1
            continue
        updated += 1
        if dry_run:
            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                rebuilt.splitlines(keepends=True),
                fromfile=f"{path} (current)",
                tofile=f"{path} (backfilled)",
            )
            sys.stdout.writelines(diff)
        else:
            path.write_text(rebuilt, encoding="utf-8")

    verb = "would update" if dry_run else "updated"
    print(
        f"memory backfill: {scanned} scanned, {updated} {verb}, "
        f"{unchanged} unchanged (MEMORY.md skipped) in {memory_dir}"
    )
    return (scanned, updated, unchanged)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Backfill memory frontmatter (#68).")
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Memory directory (default: $CLAUDE_MEMORY_DIR or the per-project path).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a unified diff of pending changes without writing.",
    )
    args = parser.parse_args(argv)
    memory_dir = (args.dir or default_memory_dir()).expanduser()
    process(memory_dir, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
