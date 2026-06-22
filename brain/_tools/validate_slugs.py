#!/usr/bin/env python3
"""Slug / path validation.

Detects: empty filenames, invalid paths (e.g. People/.md), duplicate canonical slugs,
unsafe filename characters. Exit 0 = clean, 1 = problems.
"""
import sys
from collections import defaultdict
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
UNSAFE = set('<>:"\\|?*')
CANONICAL_DIRS = {
    "People", "Companies", "Projects", "Products", "Topics", "Decisions",
    "Commitments", "Procedures", "Preferences", "Context Packs", "Sources", "Maps",
}


def main():
    problems = []
    slugs = defaultdict(list)
    for p in VAULT.rglob("*.md"):
        if "_tools" in p.parts:
            continue
        rel = p.relative_to(VAULT)
        stem = p.stem
        if stem == "" or stem.strip() == "":
            problems.append(f"EMPTY filename: {rel}")
        if p.name == ".md":
            problems.append(f"INVALID path (empty slug): {rel}")
        bad = UNSAFE & set(p.name)
        if bad:
            problems.append(f"UNSAFE chars {sorted(bad)} in: {rel}")
        top = rel.parts[0]
        if top in CANONICAL_DIRS:
            slugs[stem.lower()].append(str(rel))

    for slug, paths in slugs.items():
        if len(paths) > 1:
            problems.append(f"DUPLICATE slug '{slug}': {paths}")

    if problems:
        print(f"FAIL ({len(problems)} issue(s)):")
        for x in problems:
            print(f"  {x}")
        return 1
    print(f"PASS: slugs/paths clean across canonical folders.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
