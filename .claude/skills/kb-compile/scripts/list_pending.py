#!/usr/bin/env python3
"""
kb-compile/scripts/list_pending.py

List raw knowledge-base sources not yet compiled into the wiki.
Deterministic filesystem diff only — no embedding generation, no API calls.

Usage:
    python list_pending.py   (run from any dir; resolves repo root via git)

Output (stdout):
    JSON array of pending sources:
    [{"path": "raw/foo.md", "title": "Foo", "size_bytes": 1234}, ...]
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        print("ERROR: not inside a git repo", file=sys.stderr)
        sys.exit(1)


def extract_title(path: Path) -> str:
    """Return frontmatter title or first H1 heading, else stem."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return path.stem

    # frontmatter title: title: "Some Title"
    fm_match = re.search(r"^title:\s*['\"]?(.+?)['\"]?\s*$", text, re.MULTILINE)
    if fm_match:
        return fm_match.group(1).strip()

    # first H1
    h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    return path.stem.replace("-", " ").replace("_", " ").title()


def collect_raw_sources(kb_root: Path) -> list[dict]:
    """All .md files under knowledge-base/raw/."""
    raw_dir = kb_root / "raw"
    if not raw_dir.exists():
        return []

    sources = []
    for path in sorted(raw_dir.rglob("*.md")):
        rel = path.relative_to(kb_root)
        sources.append({
            "abs": path,
            "rel": str(rel),
            "title": extract_title(path),
            "size_bytes": path.stat().st_size,
        })
    return sources


def collect_compiled_titles(kb_root: Path) -> set[str]:
    """
    Parse INDEX.md for article titles already compiled.
    Falls back to scanning wiki/ filenames if INDEX.md absent.
    """
    compiled: set[str] = set()

    index_path = kb_root / "INDEX.md"
    if index_path.exists():
        try:
            text = index_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        # Markdown list entries: - [Title](path) — description
        for m in re.finditer(r"\[([^\]]+)\]\(", text):
            compiled.add(m.group(1).strip().lower())

    # Also collect wiki .md stems as a secondary signal
    wiki_dir = kb_root / "wiki"
    if wiki_dir.exists():
        for path in wiki_dir.rglob("*.md"):
            compiled.add(path.stem.lower())

    return compiled


def is_pending(source: dict, compiled_titles: set[str]) -> bool:
    """
    A raw source is pending if its title and stem are NOT in compiled_titles.
    Uses lower-case comparison to avoid case mismatches.
    """
    title_lower = source["title"].lower()
    stem_lower = Path(source["rel"]).stem.lower()
    return title_lower not in compiled_titles and stem_lower not in compiled_titles


def main() -> int:
    root = repo_root()
    kb_root = root / "knowledge-base"

    if not kb_root.exists():
        print(json.dumps([]))
        return 0

    raw_sources = collect_raw_sources(kb_root)
    compiled_titles = collect_compiled_titles(kb_root)

    pending = []
    for source in raw_sources:
        if is_pending(source, compiled_titles):
            pending.append({
                "path": source["rel"],
                "title": source["title"],
                "size_bytes": source["size_bytes"],
            })

    print(json.dumps(pending, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
