#!/usr/bin/env python3
"""
Claudeopedia viewer-data-generator.py

Reads all markdown files from knowledge-base/wiki/**/*.md, extracts frontmatter,
and writes knowledge-base/viewer-data.json for use by viewer.html.

Usage:
    python3 knowledge-base/viewer-data-generator.py
    python3 knowledge-base/viewer-data-generator.py --kb-path /custom/path/knowledge-base

The script must be run from the repo root, or pass --kb-path explicitly.
"""

import argparse
import json
import re
import sys
from datetime import datetime, date
from pathlib import Path


CATEGORY_COLORS = {
    "competitors":    "#ef4444",
    "ai-llm":         "#8b5cf6",
    "small-biz-saas": "#f59e0b",
    "verticals":      "#10b981",
    "technical":      "#06b6d4",
    "regulations":    "#ec4899",
    "growth":         "#f97316",
    "general":        "#6b7280",
}

SKIP_DIRS = {"_outputs"}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Parse YAML-style frontmatter from a markdown file.
    Returns (meta_dict, body_text). If no frontmatter found, returns ({}, full_text).
    Handles only the subset used in wiki articles: string scalars and YAML lists.
    """
    if not text.startswith("---"):
        return {}, text

    # Find closing ---
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    fm_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")

    meta = {}
    # Parse line by line — handles: key: value, key: "value", key: [a, b, c], multiline lists
    lines = fm_block.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith("#"):
            i += 1
            continue

        # key: value
        colon = line.find(":")
        if colon == -1:
            i += 1
            continue

        key = line[:colon].strip()
        raw_val = line[colon + 1:].strip()

        # Inline list: key: [a, b, c] or key: ["a", "b"]
        if raw_val.startswith("[") and raw_val.endswith("]"):
            inner = raw_val[1:-1]
            items = [v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()]
            meta[key] = items
            i += 1
            continue

        # Multiline list (YAML block sequence)
        if raw_val == "" and i + 1 < len(lines) and lines[i + 1].startswith("  - "):
            items = []
            i += 1
            while i < len(lines) and lines[i].startswith("  - "):
                items.append(lines[i][4:].strip().strip('"').strip("'"))
                i += 1
            meta[key] = items
            continue

        # Plain scalar or quoted string
        val = raw_val.strip('"').strip("'")
        meta[key] = val
        i += 1

    return meta, body


def extract_cross_refs(body: str) -> list[str]:
    """Extract [[slug]] cross-references from article body."""
    return list(set(re.findall(r"\[\[([^\]]+)\]\]", body)))


def count_words(text: str) -> int:
    """Count words in text, stripping markdown syntax."""
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove markdown links/images
    text = re.sub(r"!?\[([^\]]*)\]\([^\)]*\)", r"\1", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    return len(text.split())


def coerce_date(val) -> str:
    """Normalize a date value to YYYY-MM-DD string."""
    if not val:
        return ""
    if isinstance(val, (date, datetime)):
        return str(val)[:10]
    s = str(val).strip()
    # Accept YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    return s


def build_viewer_data(kb_path: Path) -> dict:
    wiki_root = kb_path / "wiki"
    if not wiki_root.exists():
        print(f"ERROR: wiki directory not found at {wiki_root}", file=sys.stderr)
        sys.exit(1)

    articles = []
    tag_freq: dict[str, int] = {}
    cat_counts: dict[str, int] = {}

    md_files = sorted(wiki_root.rglob("*.md"))
    skipped = 0

    for md_file in md_files:
        # Skip _outputs and any hidden dirs
        parts = md_file.relative_to(wiki_root).parts
        if any(p in SKIP_DIRS or p.startswith(".") for p in parts):
            skipped += 1
            continue

        text = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)

        # Category: prefer frontmatter, fall back to parent directory name
        cat_dir = md_file.parent.name
        category = meta.get("category", cat_dir)
        if category.startswith("_"):
            skipped += 1
            continue

        slug = f"{cat_dir}/{md_file.stem}"
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        created = coerce_date(meta.get("created", ""))
        updated = coerce_date(meta.get("updated", meta.get("date", "")))
        if not updated:
            updated = created

        word_count = count_words(body)
        cross_refs = extract_cross_refs(body)

        # Build summary: prefer frontmatter summary, else first non-empty non-header body line
        summary = meta.get("summary", "")
        if not summary:
            for line in body.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith(">") and not line.startswith("---"):
                    # Strip markdown formatting
                    summary = re.sub(r"[*_`\[\]]+", "", line)[:200]
                    break

        for t in tags:
            tag_freq[t] = tag_freq.get(t, 0) + 1
        cat_counts[category] = cat_counts.get(category, 0) + 1

        path_rel = str(md_file.relative_to(kb_path))

        articles.append({
            "slug":       slug,
            "title":      meta.get("title", md_file.stem.replace("-", " ").title()),
            "category":   category,
            "summary":    summary,
            "tags":       tags,
            "created":    created,
            "updated":    updated,
            "word_count": word_count,
            "path":       path_rel,
            "cross_refs": cross_refs,
        })

    # Sort articles newest first
    articles.sort(key=lambda a: a["created"] or "0000-00-00", reverse=True)

    # Build categories list — include all 8 canonical categories even if empty,
    # plus any extra categories found in articles
    canonical_order = ["competitors", "ai-llm", "small-biz-saas", "verticals",
                       "technical", "regulations", "growth", "general"]
    seen_cats = set(cat_counts.keys())
    all_cats = canonical_order + sorted(seen_cats - set(canonical_order))

    categories = []
    for c in all_cats:
        categories.append({
            "name":  c,
            "color": CATEGORY_COLORS.get(c, "#6b7280"),
            "count": cat_counts.get(c, 0),
        })

    total_words = sum(a["word_count"] for a in articles)
    last_updated = max((a["updated"] or a["created"] for a in articles), default=str(date.today()))

    data = {
        "generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": {
            "total_articles": len(articles),
            "total_words":    total_words,
            "categories":     len(cat_counts),
            "last_updated":   last_updated,
        },
        "articles":        articles,
        "categories":      categories,
        "tag_frequencies": dict(sorted(tag_freq.items(), key=lambda x: -x[1])),
    }

    if skipped:
        print(f"  Skipped {skipped} file(s) in _outputs or hidden dirs.")

    return data


def main():
    parser = argparse.ArgumentParser(description="Generate viewer-data.json for Claudeopedia viewer.html")
    parser.add_argument(
        "--kb-path",
        default=None,
        help="Path to knowledge-base directory (default: auto-detected from script location or cwd)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for viewer-data.json (default: <kb-path>/viewer-data.json)",
    )
    args = parser.parse_args()

    # Resolve kb_path: try --kb-path, then sibling of this script, then cwd/knowledge-base
    if args.kb_path:
        kb_path = Path(args.kb_path).resolve()
    else:
        script_dir = Path(__file__).resolve().parent
        if (script_dir / "wiki").exists():
            kb_path = script_dir
        elif (Path.cwd() / "knowledge-base" / "wiki").exists():
            kb_path = Path.cwd() / "knowledge-base"
        else:
            print("ERROR: Could not locate knowledge-base directory. Pass --kb-path explicitly.", file=sys.stderr)
            sys.exit(1)

    print(f"knowledge-base: {kb_path}")

    data = build_viewer_data(kb_path)

    out_path = Path(args.output).resolve() if args.output else kb_path / "viewer-data.json"
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    print(
        f"viewer-data.json: {data['stats']['total_articles']} articles, "
        f"{data['stats']['total_words']} words, "
        f"{data['stats']['categories']} categories, "
        f"{size_kb:.1f} KB"
    )
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
