#!/usr/bin/env python3
"""Detect dead path-scoped rules in .claude/rules/.

Walks .claude/rules/*.md, parses YAML frontmatter, and for any rule with
a `paths:` block reports globs that match zero files in the repo.

Exit code 0 if all globs match at least one file; 1 if any dead globs found
(or --strict and any warnings); 2 on parse error.
"""
import argparse
import glob
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / ".claude" / "rules"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    block = m.group(1)
    out: dict = {}
    current_key = None
    current_list: list | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.startswith(" ") or line.startswith("\t"):
            stripped = line.strip()
            if stripped.startswith("- ") and current_list is not None:
                val = stripped[2:].strip().strip('"').strip("'")
                current_list.append(val)
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val == "":
                current_list = []
                out[key] = current_list
                current_key = key
            else:
                out[key] = val
                current_list = None
                current_key = key
    return out


def check_glob(pattern: str) -> int:
    norm = pattern
    matches = glob.glob(str(REPO_ROOT / norm), recursive=True)
    return len(matches)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit 1 on any warning")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not RULES_DIR.is_dir():
        print(f"ERR: {RULES_DIR} not found", file=sys.stderr)
        return 2

    dead: list[tuple[str, str]] = []
    checked = 0
    rules_with_paths = 0

    for md in sorted(RULES_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        if not fm:
            continue
        paths = fm.get("paths")
        if not paths or not isinstance(paths, list):
            continue
        rules_with_paths += 1
        for pat in paths:
            checked += 1
            n = check_glob(pat)
            if n == 0:
                dead.append((md.name, pat))
            elif not args.quiet:
                print(f"OK   {md.name}: '{pat}' -> {n} files")

    print()
    print(f"Rules with paths: {rules_with_paths}")
    print(f"Globs checked:    {checked}")
    print(f"Dead globs:       {len(dead)}")

    if dead:
        print()
        print("Dead globs (no files match):")
        for fname, pat in dead:
            print(f"  {fname}: '{pat}'")
        if args.strict or True:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
