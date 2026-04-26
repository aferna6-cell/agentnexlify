"""Scan plans/ and audits/ for references to files that no longer exist.

Surfaces ghost references — paths that the plan claims but HEAD doesn't have.
Read-only. Run before starting work from a stale-looking plan.

Usage:
    python scripts/check_plan_drift.py
    python scripts/check_plan_drift.py --dirs plans audits docs/dev-knowledge
    python scripts/check_plan_drift.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXTS = {"py", "js", "jsx", "ts", "tsx", "md", "sql", "json", "yaml", "yml", "sh", "html", "css"}
EXT_GROUP = "|".join(EXTS)

# High-confidence path matches only:
#   1. Markdown link target: [text](path/to/file.ext) — must contain "/"
#   2. Backtick ref with "/": `path/to/file.ext`
# Bare filename mentions (e.g. "auth.py" as a concept) are skipped to cut noise.
_md_link_re = re.compile(r"\[[^\]]*\]\(([^)#\s]+\.(?:" + EXT_GROUP + r"))(?:[#:]L?\d+(?:-L?\d+)?)?\)")
_backtick_re = re.compile(r"`([^`\s]+/[^`\s]+\.(?:" + EXT_GROUP + r"))(?:[#:]L?\d+(?:-L?\d+)?)?`")


def is_external(token: str) -> bool:
    return token.startswith(("http://", "https://", "ftp://", "//"))


def is_ignorable(token: str) -> bool:
    if is_external(token):
        return True
    # Globs / wildcards / brace expansion — not literal paths
    if any(c in token for c in "*?{}"):
        return True
    # Out-of-repo absolute paths
    if token.startswith(("~/", "/c/", "/home/", "/usr/", "/etc/")):
        return True
    return False


def extract_refs(text: str) -> set[str]:
    refs: set[str] = set()
    for match in _md_link_re.finditer(text):
        token = match.group(1)
        if is_external(token) or is_ignorable(token):
            continue
        refs.add(token)
    for match in _backtick_re.finditer(text):
        token = match.group(1)
        if is_external(token) or is_ignorable(token):
            continue
        refs.add(token)
    return refs


def resolve(token: str, source: Path) -> Path:
    # Try repo-root-relative first, then source-file-relative
    candidate = (REPO_ROOT / token).resolve()
    if candidate.exists():
        return candidate
    return (source.parent / token).resolve()


def scan(dirs: list[Path]) -> dict[str, list[str]]:
    drift: dict[str, list[str]] = {}
    for d in dirs:
        if not d.exists():
            continue
        for md_path in sorted(d.rglob("*.md")):
            try:
                text = md_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            stale: list[str] = []
            for ref in sorted(extract_refs(text)):
                resolved = resolve(ref, md_path)
                if not resolved.exists():
                    stale.append(ref)
            if stale:
                drift[str(md_path.relative_to(REPO_ROOT))] = stale
    return drift


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=["plans", "audits"],
        help=(
            "Directories to scan (default: plans audits). "
            "Specs intentionally excluded — they reference proposed files."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    dirs = [REPO_ROOT / d for d in args.dirs]
    drift = scan(dirs)

    if args.json:
        print(json.dumps(drift, indent=2, sort_keys=True))
        return 1 if drift else 0

    if not drift:
        print("OK: no drift detected across", ", ".join(args.dirs))
        return 0

    print(f"DRIFT: {sum(len(v) for v in drift.values())} stale ref(s) across {len(drift)} file(s)\n")
    for src, refs in sorted(drift.items()):
        print(f"  {src}")
        for ref in refs:
            print(f"    - {ref}")
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
