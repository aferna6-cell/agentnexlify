#!/usr/bin/env python3
"""
KB Lint — validate every wiki article against Karpathy template.

Usage:
  python3 scripts/kb/kb-lint.py                # lint all, exit 1 on violations
  python3 scripts/kb/kb-lint.py --fix-index    # also check INDEX.md coverage
  python3 scripts/kb/kb-lint.py --json         # machine-readable output
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
WIKI = REPO / "knowledge-base" / "wiki"
INDEX = REPO / "knowledge-base" / "INDEX.md"

REQUIRED_FRONTMATTER = ["title", "category", "tags", "sources", "created", "updated", "summary"]
REQUIRED_SECTIONS = ["## Key Concepts", "## Related Articles", "## Relevance to AgentNexLiFy"]
BANNED_PHRASES = [
    "It's worth noting that",
    "Interestingly,",
    "It should be mentioned that",
    "As we can see,",
    "In conclusion,",
]

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([a-z0-9-]+)\]\]")


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            fields[k.strip()] = v.strip()
    return fields


def lint_article(path):
    violations = []
    text = path.read_text()
    slug = path.stem

    fm = parse_frontmatter(text)
    if fm is None:
        violations.append("missing frontmatter (---...---)")
        return violations

    for key in REQUIRED_FRONTMATTER:
        if key not in fm:
            violations.append(f"frontmatter missing field: {key}")

    if "summary" in fm:
        s = fm["summary"].strip().strip('"')
        if len(s) < 20:
            violations.append(f"summary too short ({len(s)} chars)")
        if s.count(". ") > 1:
            violations.append("summary should be one sentence")

    for section in REQUIRED_SECTIONS:
        if section not in text:
            violations.append(f"missing section: {section}")

    wikilinks = WIKILINK_RE.findall(text)
    if not wikilinks:
        violations.append("no [[wikilinks]] — every article must link to ≥1 other")

    for phrase in BANNED_PHRASES:
        if phrase in text:
            violations.append(f"banned filler phrase: {phrase!r}")

    words = len(text.split())
    if words < 200:
        violations.append(f"article too short ({words} words, min 200)")
    if words > 3000:
        violations.append(f"article too long ({words} words, max 3000)")

    return violations


def check_index_coverage():
    if not INDEX.exists():
        return ["INDEX.md missing"]
    index_text = INDEX.read_text()
    missing = []
    for article in WIKI.rglob("*.md"):
        if "_outputs" in article.parts:
            continue
        rel = article.relative_to(REPO / "knowledge-base")
        if str(rel) not in index_text and article.stem not in index_text:
            missing.append(f"INDEX.md missing entry for {rel}")
    return missing


def main():
    args = sys.argv[1:]
    json_out = "--json" in args
    fix_index = "--fix-index" in args

    results = {}
    total_violations = 0

    for article in sorted(WIKI.rglob("*.md")):
        if "_outputs" in article.parts:
            continue
        rel = str(article.relative_to(REPO))
        violations = lint_article(article)
        if violations:
            results[rel] = violations
            total_violations += len(violations)

    index_issues = []
    if fix_index:
        index_issues = check_index_coverage()

    if json_out:
        print(json.dumps({
            "articles_checked": len(list(WIKI.rglob("*.md"))),
            "violations_by_file": results,
            "index_issues": index_issues,
            "total_violations": total_violations + len(index_issues),
        }, indent=2))
    else:
        if results:
            for path, issues in results.items():
                print(f"\n{path}")
                for v in issues:
                    print(f"  - {v}")
        if index_issues:
            print("\nINDEX.md coverage:")
            for i in index_issues:
                print(f"  - {i}")
        if not results and not index_issues:
            print(f"clean — {len(list(WIKI.rglob('*.md')))} articles, 0 violations")
        else:
            print(f"\n{total_violations + len(index_issues)} violations across {len(results)} files")

    return 1 if (total_violations + len(index_issues)) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
