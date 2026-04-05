#!/usr/bin/env python3
"""
KAIROS autodream — Memory consolidation and contradiction detection.

Reads memory files, dev-knowledge, and recent git history.
Checks for contradictions and stale references.
Generates a dream report (read-only — never modifies memory files).
"""

import os
import sys
import subprocess
import datetime
import json
import re
import pathlib

# --- Configuration ---

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
MEMORY_DIR = pathlib.Path.home() / ".claude" / "projects" / "-home-aidan-agentnexlify" / "memory"
DEV_KNOWLEDGE_DIR = REPO_ROOT / "docs" / "dev-knowledge"
OUTPUT_DIR = REPO_ROOT / "docs" / "kairos"
DREAM_LOG = OUTPUT_DIR / "dream-log.md"

TODAY = datetime.date.today().isoformat()


def read_file_safe(path):
    """Read a file, return empty string on failure."""
    try:
        return pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  [warn] Could not read {path}: {e}")
        return ""


def read_all_memory_files():
    """Read all .md files from the memory directory."""
    memories = {}
    if not MEMORY_DIR.exists():
        print(f"  [warn] Memory directory not found: {MEMORY_DIR}")
        return memories

    for f in sorted(MEMORY_DIR.glob("*.md")):
        content = read_file_safe(f)
        if content.strip():
            memories[f.name] = content
    return memories


def read_dev_knowledge():
    """Read key dev-knowledge files."""
    knowledge = {}
    targets = ["bug-patterns.md", "schema-log.md", "architecture-decisions.md"]
    for name in targets:
        path = DEV_KNOWLEDGE_DIR / name
        content = read_file_safe(path)
        if content.strip():
            knowledge[name] = content
    return knowledge


def get_recent_git_log(hours=24):
    """Get git commits from the last N hours."""
    since = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--oneline", "--stat", "--no-color"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as e:
        print(f"  [warn] git log failed: {e}")
        return ""


def get_recent_changed_files(hours=24):
    """Get list of files changed in recent commits."""
    since = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--name-only", "--pretty=format:", "--no-color"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=30,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().splitlines() if f.strip()]
        return []
    except Exception as e:
        print(f"  [warn] git changed files failed: {e}")
        return []


def check_contradictions(memories, knowledge):
    """Check for contradictions between memory files and dev-knowledge."""
    issues = []

    all_text = {}
    all_text.update(memories)
    all_text.update(knowledge)

    # Check for conflicting column name references
    column_conflicts = {
        "tenant_id.*leads": "leads table uses client_id, not tenant_id",
        "lead_stage": "leads table uses status, not lead_stage",
        "service_interest": "leads table uses areas_of_interest, not service_interest",
    }

    # Files that document known issues or warnings about these patterns
    # should not be flagged as contradictions
    skip_files = {
        "bug-patterns.md", "architecture-decisions.md", "schema-log.md",
        "MEMORY.md", "brain_gotchas.md", "brain_patterns.md",
        "brain_critical_rules.md", "brain_schema.md",
    }

    for filename, content in all_text.items():
        if filename in skip_files:
            continue
        content_lower = content.lower()
        for pattern, message in column_conflicts.items():
            # Skip lines that are warnings/rules about the pattern
            # (e.g., "NEVER use tenant_id" or "not tenant_id")
            matches = re.finditer(pattern, content_lower)
            for m in matches:
                # Get surrounding context (40 chars before match)
                start = max(0, m.start() - 40)
                context = content_lower[start:m.end()]
                # Skip if context indicates this is a warning, not actual usage
                if any(w in context for w in ("never", "not ", "don't", "do not", "wrong", "incorrect", "avoid", "instead of")):
                    continue
                issues.append({
                    "type": "column_conflict",
                    "file": filename,
                    "message": message,
                    "pattern": pattern,
                })
                break  # One finding per file per pattern

    # Check for references to old plan names
    old_plan_names = ["foundation", "operations"]
    for filename, content in all_text.items():
        if filename in ("architecture-decisions.md", "bug-patterns.md"):
            continue
        content_lower = content.lower()
        for name in old_plan_names:
            # Only flag if used as a plan name, not in general prose
            if re.search(rf'\bplan[:\s]*["\']?{name}', content_lower):
                issues.append({
                    "type": "stale_plan_name",
                    "file": filename,
                    "message": f"References old plan name '{name}' (renamed to growth/professional)",
                })

    # Check for conflicting statements about the same topic across files
    # Look for files that mention different values for the same config
    cache_ttl_mentions = []
    for filename, content in all_text.items():
        ttl_matches = re.findall(r'(\d+)[- ]?min(?:ute)?s?\s*(?:ttl|cache|expir)', content.lower())
        for m in ttl_matches:
            cache_ttl_mentions.append((filename, int(m)))

    if len(cache_ttl_mentions) > 1:
        values = set(v for _, v in cache_ttl_mentions)
        if len(values) > 1:
            issues.append({
                "type": "value_conflict",
                "file": ", ".join(f for f, _ in cache_ttl_mentions),
                "message": f"Conflicting cache TTL values: {cache_ttl_mentions}",
            })

    return issues


def check_stale_references(memories):
    """Check if memory files reference files/paths that no longer exist."""
    stale = []

    # Extract file paths mentioned in memory files
    path_pattern = re.compile(r'(?:backend|frontend|scripts|migrations|docs)/[\w./-]+\.\w+')

    for filename, content in memories.items():
        matches = path_pattern.findall(content)
        for match in matches:
            full_path = REPO_ROOT / match
            if not full_path.exists():
                stale.append({
                    "file": filename,
                    "referenced_path": match,
                    "message": f"References {match} which does not exist",
                })

    return stale


def check_memory_freshness(memories):
    """Check if any memory files seem outdated based on their content."""
    observations = []

    for filename, content in memories.items():
        # Check for date references that are more than 30 days old
        date_matches = re.findall(r'20\d{2}-\d{2}-\d{2}', content)
        if date_matches:
            try:
                dates = [datetime.date.fromisoformat(d) for d in date_matches]
                newest = max(dates)
                age_days = (datetime.date.today() - newest).days
                if age_days > 30:
                    observations.append({
                        "file": filename,
                        "newest_date": newest.isoformat(),
                        "age_days": age_days,
                        "message": f"Newest date reference is {age_days} days old — may be stale",
                    })
            except ValueError:
                pass

    return observations


def check_duplicate_info(memories, knowledge):
    """Check for information duplicated across files."""
    duplicates = []

    # Check for the same URL or path mentioned in multiple memory files
    url_pattern = re.compile(r'https?://\S+')
    url_sources = {}

    all_files = {}
    all_files.update(memories)
    all_files.update(knowledge)

    for filename, content in all_files.items():
        urls = url_pattern.findall(content)
        for url in urls:
            clean_url = url.rstrip(")")
            if clean_url not in url_sources:
                url_sources[clean_url] = []
            url_sources[clean_url].append(filename)

    for url, sources in url_sources.items():
        if len(sources) > 2:
            duplicates.append({
                "type": "url_duplication",
                "url": url,
                "files": sources,
                "message": f"URL {url[:60]}... mentioned in {len(sources)} files",
            })

    return duplicates


def generate_dream_report(
    memories,
    knowledge,
    git_log,
    changed_files,
    contradictions,
    stale_refs,
    freshness,
    duplicates,
):
    """Generate the dream report markdown."""
    lines = []
    lines.append(f"# KAIROS Dream Report -- {TODAY}")
    lines.append("")
    lines.append(f"Generated: {datetime.datetime.now().isoformat()}")
    lines.append("")

    # Summary stats
    total_issues = len(contradictions) + len(stale_refs) + len(freshness) + len(duplicates)
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Memory files scanned: {len(memories)}")
    lines.append(f"- Dev-knowledge files scanned: {len(knowledge)}")
    lines.append(f"- Recent commits (24h): {len(git_log.splitlines()) if git_log else 0} lines")
    lines.append(f"- Changed files (24h): {len(changed_files)}")
    lines.append(f"- Total findings: {total_issues}")
    lines.append("")

    # Contradictions
    lines.append("## Contradictions")
    lines.append("")
    if contradictions:
        for item in contradictions:
            lines.append(f"- **{item['file']}**: {item['message']}")
    else:
        lines.append("No contradictions detected.")
    lines.append("")

    # Stale references
    lines.append("## Stale References")
    lines.append("")
    if stale_refs:
        for item in stale_refs:
            lines.append(f"- **{item['file']}**: {item['message']}")
    else:
        lines.append("No stale file references detected.")
    lines.append("")

    # Memory freshness
    lines.append("## Memory Freshness")
    lines.append("")
    if freshness:
        for item in freshness:
            lines.append(
                f"- **{item['file']}**: newest date is {item['newest_date']} "
                f"({item['age_days']} days ago)"
            )
    else:
        lines.append("All memory files appear current.")
    lines.append("")

    # Duplicates
    lines.append("## Duplicate Information")
    lines.append("")
    if duplicates:
        for item in duplicates:
            lines.append(f"- {item['message']} ({', '.join(item['files'])})")
    else:
        lines.append("No significant duplication detected.")
    lines.append("")

    # Recent git activity
    lines.append("## Recent Git Activity (24h)")
    lines.append("")
    if git_log:
        # Show just the oneline summaries, not full stats
        commit_lines = [
            line for line in git_log.splitlines()
            if line.strip() and not line.startswith(" ") and not line.strip().startswith("|")
        ]
        for line in commit_lines[:20]:
            lines.append(f"- {line}")
        if len(commit_lines) > 20:
            lines.append(f"- ... and {len(commit_lines) - 20} more")
    else:
        lines.append("No commits in the last 24 hours.")
    lines.append("")

    # Changed files
    if changed_files:
        lines.append("## Files Changed (24h)")
        lines.append("")
        # Group by directory
        dirs = {}
        for f in changed_files:
            d = f.split("/")[0] if "/" in f else "root"
            if d not in dirs:
                dirs[d] = 0
            dirs[d] += 1
        for d, count in sorted(dirs.items(), key=lambda x: -x[1]):
            lines.append(f"- `{d}/`: {count} files")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    recommendations = []

    if contradictions:
        recommendations.append(
            "Review and fix contradictions listed above. "
            "These could cause incorrect behavior if agents read stale info."
        )
    if stale_refs:
        recommendations.append(
            "Update or remove memory entries that reference non-existent files."
        )
    if freshness:
        stale_files = [item["file"] for item in freshness]
        recommendations.append(
            f"Consider refreshing stale memory files: {', '.join(stale_files)}"
        )
    if not recommendations:
        recommendations.append("No action needed. Memory and knowledge appear consistent.")

    for i, rec in enumerate(recommendations, 1):
        lines.append(f"{i}. {rec}")
    lines.append("")

    return "\n".join(lines)


def generate_summary_line(contradictions, stale_refs, freshness, duplicates, git_log):
    """Generate a one-line summary for the dream log."""
    total = len(contradictions) + len(stale_refs) + len(freshness) + len(duplicates)
    commits = len([l for l in git_log.splitlines() if l.strip() and not l.startswith(" ")]) if git_log else 0

    parts = []
    if contradictions:
        parts.append(f"{len(contradictions)} contradictions")
    if stale_refs:
        parts.append(f"{len(stale_refs)} stale refs")
    if freshness:
        parts.append(f"{len(freshness)} stale memories")
    if duplicates:
        parts.append(f"{len(duplicates)} duplicates")

    finding_str = ", ".join(parts) if parts else "clean"
    return f"| {TODAY} | {total} | {commits} commits | {finding_str} |"


def main():
    print(f"KAIROS autodream starting ({TODAY})")

    # Gather inputs
    print("  Reading memory files...")
    memories = read_all_memory_files()
    print(f"  Found {len(memories)} memory files")

    print("  Reading dev-knowledge...")
    knowledge = read_dev_knowledge()
    print(f"  Found {len(knowledge)} knowledge files")

    print("  Reading git history (24h)...")
    git_log = get_recent_git_log(hours=24)
    changed_files = get_recent_changed_files(hours=24)
    print(f"  Found {len(changed_files)} changed files")

    # Run checks
    print("  Checking for contradictions...")
    contradictions = check_contradictions(memories, knowledge)
    print(f"  Found {len(contradictions)} contradictions")

    print("  Checking for stale references...")
    stale_refs = check_stale_references(memories)
    print(f"  Found {len(stale_refs)} stale references")

    print("  Checking memory freshness...")
    freshness = check_memory_freshness(memories)
    print(f"  Found {len(freshness)} potentially stale memories")

    print("  Checking for duplicates...")
    duplicates = check_duplicate_info(memories, knowledge)
    print(f"  Found {len(duplicates)} duplicates")

    # Generate report
    print("  Writing dream report...")
    report = generate_dream_report(
        memories, knowledge, git_log, changed_files,
        contradictions, stale_refs, freshness, duplicates,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / f"dream-{TODAY}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Dream report: {report_path}")

    # Append to dream log
    summary_line = generate_summary_line(contradictions, stale_refs, freshness, duplicates, git_log)

    if not DREAM_LOG.exists():
        DREAM_LOG.write_text(
            "# KAIROS Dream Log\n\n"
            "| Date | Findings | Activity | Details |\n"
            "|------|----------|----------|----------|\n"
            f"{summary_line}\n",
            encoding="utf-8",
        )
    else:
        with open(DREAM_LOG, "a", encoding="utf-8") as f:
            f.write(f"{summary_line}\n")
    print(f"  Dream log updated: {DREAM_LOG}")

    total = len(contradictions) + len(stale_refs) + len(freshness) + len(duplicates)
    print(f"KAIROS autodream complete. {total} findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
