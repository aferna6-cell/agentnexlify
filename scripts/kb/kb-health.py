#!/usr/bin/env python3
"""Generate a deterministic knowledge-base health report.

This is intentionally stdlib-only and read-only. It complements kb-lint by
checking the operational health signals from the Karpathy-style KB pattern:
stale articles, pending raw sources, category coverage, source attribution,
and orphaned wiki pages.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent
KB = REPO / "knowledge-base"
WIKI = KB / "wiki"
PENDING = KB / "PENDING.md"
EXPECTED_CATEGORIES = (
    "ai-llm",
    "competitors",
    "growth",
    "regulations",
    "small-biz-saas",
    "technical",
    "verticals",
)

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([a-z0-9-]+)\]\]")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}

    fields: dict[str, str] = {}
    current_key: str | None = None
    current_values: list[str] = []

    def flush_list() -> None:
        nonlocal current_key, current_values
        if current_key and current_values:
            fields[current_key] = ", ".join(current_values)
        current_key = None
        current_values = []

    for raw_line in match.group(1).splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") and current_key:
            current_values.append(stripped[2:].strip().strip("\"'"))
            continue
        flush_list()
        if ":" not in raw_line:
            continue
        key, _, value = raw_line.partition(":")
        key = key.strip()
        value = value.strip().strip("\"'")
        fields[key] = value
        if value == "":
            current_key = key
            current_values = []
    flush_list()
    return fields


def parse_date(value: str) -> date | None:
    value = value.strip().strip("\"'")
    if not DATE_RE.match(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def wiki_articles() -> list[Path]:
    if not WIKI.exists():
        return []
    return sorted(
        path
        for path in WIKI.rglob("*.md")
        if "_outputs" not in path.parts and path.name != ".gitkeep"
    )


def pending_entries() -> list[str]:
    if not PENDING.exists():
        return []
    entries: list[str] = []
    for line in read_text(PENDING).splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        if stripped.startswith("- ~~"):
            continue
        if "_No pending sources._" in stripped:
            continue
        if "raw/" not in stripped:
            continue
        entries.append(stripped[2:])
    return entries


def article_slug(path: Path) -> str:
    return path.stem


def analyze(max_stale_days: int) -> dict[str, object]:
    today = datetime.now(UTC).date()
    articles = wiki_articles()
    by_slug = {article_slug(path): path for path in articles}
    categories: Counter[str] = Counter()
    stale: list[dict[str, object]] = []
    missing_sources: list[str] = []
    missing_updated: list[str] = []
    inbound: defaultdict[str, int] = defaultdict(int)
    outbound_by_slug: dict[str, list[str]] = {}

    for path in articles:
        rel = path.relative_to(REPO).as_posix()
        text = read_text(path)
        fm = parse_frontmatter(text)
        category = fm.get("category") or path.parent.name
        categories[category] += 1

        sources = fm.get("sources", "").strip()
        if not sources or sources in {"[]", "null", "None"}:
            missing_sources.append(rel)

        updated = parse_date(fm.get("updated", ""))
        if not updated:
            missing_updated.append(rel)
        else:
            age_days = (today - updated).days
            if age_days > max_stale_days:
                stale.append({"path": rel, "updated": updated.isoformat(), "age_days": age_days})

        links = sorted(set(WIKILINK_RE.findall(text)))
        outbound_by_slug[article_slug(path)] = links
        for link in links:
            inbound[link] += 1

    orphaned = [
        path.relative_to(REPO).as_posix()
        for slug, path in sorted(by_slug.items())
        if inbound[slug] == 0
    ]
    thin_categories = [
        category
        for category in EXPECTED_CATEGORIES
        if categories.get(category, 0) < 3
    ]
    broken_links = []
    for slug, links in outbound_by_slug.items():
        for link in links:
            if link not in by_slug:
                broken_links.append({"from": slug, "to": link})

    pending = pending_entries()
    deductions = min(len(stale) * 2, 20)
    deductions += min(len(thin_categories) * 5, 20)
    deductions += min(len(missing_sources) * 2, 15)
    deductions += min(len(missing_updated) * 2, 10)
    deductions += min(len(orphaned), 15)
    deductions += min(len(broken_links), 20)
    score = max(0, 100 - deductions)

    return {
        "score": score,
        "articles": len(articles),
        "categories": dict(sorted(categories.items())),
        "pending_sources": pending,
        "stale": stale,
        "thin_categories": thin_categories,
        "missing_sources": missing_sources,
        "missing_updated": missing_updated,
        "orphaned": orphaned,
        "broken_links": broken_links,
        "max_stale_days": max_stale_days,
    }


def print_markdown(report: dict[str, object]) -> None:
    print(f"## Knowledge Base Health Report - {datetime.now(UTC).date().isoformat()}")
    print("")
    print(f"### Score: {report['score']}/100")
    print("")
    print("### Summary")
    print(f"- Total wiki articles: {report['articles']}")
    print(f"- Pending raw sources: {len(report['pending_sources'])}")
    print(f"- Stale articles >{report['max_stale_days']} days: {len(report['stale'])}")
    print(f"- Thin categories: {len(report['thin_categories'])}")
    print(f"- Missing source attribution: {len(report['missing_sources'])}")
    print(f"- Orphaned articles: {len(report['orphaned'])}")
    print(f"- Broken wikilinks: {len(report['broken_links'])}")
    print("")
    print("### Category Coverage")
    for category, count in report["categories"].items():
        print(f"- {category}: {count}")

    if report["pending_sources"]:
        print("")
        print("### Pending Sources")
        for entry in report["pending_sources"][:20]:
            print(f"- {entry}")

    if report["stale"]:
        print("")
        print("### Stale Articles")
        for item in report["stale"][:20]:
            print(f"- {item['path']} - updated {item['updated']} ({item['age_days']} days)")

    if report["thin_categories"]:
        print("")
        print("### Thin Categories")
        for category in report["thin_categories"]:
            print(f"- {category}")

    if report["missing_sources"]:
        print("")
        print("### Missing Source Attribution")
        for path in report["missing_sources"][:20]:
            print(f"- {path}")

    if report["orphaned"]:
        print("")
        print("### Orphaned Articles")
        for path in report["orphaned"][:20]:
            print(f"- {path}")

    if report["broken_links"]:
        print("")
        print("### Broken Wikilinks")
        for item in report["broken_links"][:20]:
            print(f"- {item['from']} -> [[{item['to']}]]")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument(
        "--max-stale-days",
        type=int,
        default=90,
        help="Article age threshold for stale warnings. Default: 90.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit nonzero when the health score is below --min-score.",
    )
    parser.add_argument("--min-score", type=int, default=70)
    args = parser.parse_args()

    report = analyze(args.max_stale_days)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_markdown(report)

    if args.check and int(report["score"]) < args.min_score:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
