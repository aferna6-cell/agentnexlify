#!/usr/bin/env python3
"""Provenance validation.

Every promoted canonical note (declarative + procedural types) must have a
`## Provenance` section; context-packs must have `## Sources`. Every link inside that
section must resolve to a Sources/* note or to SOURCE-MANIFEST. No placeholder refs.

Exit 0 = all good, 1 = missing/placeholder/invalid provenance.
"""
import re
import sys
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\[\[([^\]\|#]+)")
CANON_DIRS = {"People", "Companies", "Projects", "Products", "Topics",
              "Decisions", "Commitments", "Procedures", "Preferences"}
PLACEHOLDER = re.compile(r"example-source-id|TODO|TBD|FIXME|placeholder", re.I)

source_stems = {p.stem.lower() for p in (VAULT / "Sources").glob("*.md")}


def section(text, header):
    m = re.search(rf"^##\s+{re.escape(header)}\s*$", text, re.M)
    if not m:
        return None
    start = m.end()
    nxt = re.search(r"^##\s+", text[start:], re.M)
    return text[start: start + (nxt.start() if nxt else len(text) - start)]


def main():
    problems = []
    checked = 0
    for p in VAULT.rglob("*.md"):
        if "_tools" in p.parts:
            continue
        top = p.relative_to(VAULT).parts[0]
        text = p.read_text(encoding="utf-8")
        if top in CANON_DIRS:
            checked += 1
            body = section(text, "Provenance")
            if body is None:
                problems.append(f"{p.relative_to(VAULT)}: missing ## Provenance")
                continue
            target_field = body
        elif top == "Context Packs":
            checked += 1
            body = section(text, "Sources")
            if body is None:
                problems.append(f"{p.relative_to(VAULT)}: missing ## Sources")
                continue
            target_field = body
        else:
            continue

        if PLACEHOLDER.search(target_field):
            problems.append(f"{p.relative_to(VAULT)}: placeholder source reference")
        links = [l.strip().lower() for l in LINK_RE.findall(target_field)]
        if not links:
            problems.append(f"{p.relative_to(VAULT)}: provenance has no source links")
        for l in links:
            if l == "source-manifest":
                continue
            if l in source_stems:
                continue
            problems.append(f"{p.relative_to(VAULT)}: provenance link [[{l}]] not in Sources/ or SOURCE-MANIFEST")

    if problems:
        print(f"FAIL ({len(problems)} issue(s)):")
        for x in problems:
            print(f"  {x}")
        return 1
    print(f"PASS: {checked} canonical notes have valid provenance.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
