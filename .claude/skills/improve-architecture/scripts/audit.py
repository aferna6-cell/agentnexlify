#!/usr/bin/env python3
"""
improve-architecture/scripts/audit.py

Scan AgentNexLiFy repo for structural health issues.
Deterministic only — no LLM calls.

Usage:
    python audit.py   (run from any dir; resolves repo root via git)

Output (stdout):
    Markdown table with ranked sections: Critical / High / Medium
"""

import re
import subprocess
import sys
from pathlib import Path


# --- helpers ---

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


def count_lines(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", errors="replace"))
    except OSError:
        return 0


def find_code_files(root: Path, dirs: list[str], exts: tuple) -> list[Path]:
    found = []
    for d in dirs:
        target = root / d
        if not target.exists():
            continue
        for path in target.rglob("*"):
            if path.suffix in exts and "__pycache__" not in str(path):
                found.append(path)
    return found


# --- checks ---

def check_god_classes(root: Path) -> list[dict]:
    issues = []
    py_dirs = ["backend", "frontend/src", "widget"]
    py_exts = (".py", ".ts", ".tsx", ".js")

    for path in find_code_files(root, py_dirs, py_exts):
        lc = count_lines(path)
        if lc >= 600:
            rel = path.relative_to(root)
            severity = "CRITICAL" if lc > 1000 else "HIGH"
            issues.append({
                "severity": severity,
                "category": "god-class",
                "path": str(rel),
                "line": lc,
                "detail": f"{lc} lines — split into focused modules",
            })
    return issues


def check_layer_violations(root: Path) -> list[dict]:
    issues = []

    # services importing from routers (backwards dependency)
    services_dir = root / "backend" / "services"
    if services_dir.exists():
        for path in services_dir.rglob("*.py"):
            rel = path.relative_to(root)
            try:
                content = path.read_text(errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(content.splitlines(), 1):
                if re.search(r"from\s+backend\.routers\b", line):
                    issues.append({
                        "severity": "HIGH",
                        "category": "layer-violation",
                        "path": f"{rel}:{lineno}",
                        "line": lineno,
                        "detail": f"service imports from routers: {line.strip()[:80]}",
                    })

    # routers importing from frontend (should be impossible)
    routers_dir = root / "backend" / "routers"
    if routers_dir.exists():
        for path in routers_dir.rglob("*.py"):
            rel = path.relative_to(root)
            try:
                content = path.read_text(errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(content.splitlines(), 1):
                if re.search(r"from\s+frontend\b|import\s+frontend\b", line):
                    issues.append({
                        "severity": "CRITICAL",
                        "category": "layer-violation",
                        "path": f"{rel}:{lineno}",
                        "line": lineno,
                        "detail": f"router imports frontend: {line.strip()[:80]}",
                    })

    return issues


def check_dead_imports(root: Path) -> list[dict]:
    """Simple regex signal: `from X import Y` where Y never appears again in the file."""
    issues = []
    py_dirs = ["backend", "frontend/src"]

    for path in find_code_files(root, py_dirs, (".py",)):
        rel = path.relative_to(root)
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue

        full_text = "\n".join(lines)
        for lineno, line in enumerate(lines, 1):
            m = re.match(r"^\s*from\s+\S+\s+import\s+(\w+)", line)
            if not m:
                continue
            symbol = m.group(1)
            if symbol in ("TYPE_CHECKING", "annotations", "__all__"):
                continue
            # Count occurrences outside this import line
            occurrences = len(re.findall(r"\b" + re.escape(symbol) + r"\b", full_text))
            if occurrences == 1:
                issues.append({
                    "severity": "MEDIUM",
                    "category": "dead-import",
                    "path": f"{rel}:{lineno}",
                    "line": lineno,
                    "detail": f"imported symbol `{symbol}` never used in file",
                })

    return issues


def check_migration_gap(root: Path) -> list[dict]:
    issues = []
    migrations_dir = root / "migrations"
    schema_log = root / "docs" / "dev-knowledge" / "schema-log.md"

    if not migrations_dir.exists():
        return issues

    # Highest-numbered migration file
    migration_files = sorted(
        [f.name for f in migrations_dir.glob("*.sql")],
        reverse=True,
    )
    if not migration_files:
        return issues

    highest = migration_files[0]
    # Extract number prefix like "103_" or "103-"
    m = re.match(r"^(\d+)", highest)
    if not m:
        return issues
    highest_num = m.group(1)

    if not schema_log.exists():
        issues.append({
            "severity": "MEDIUM",
            "category": "migration-gap",
            "path": "docs/dev-knowledge/schema-log.md",
            "line": 0,
            "detail": "schema-log.md not found — cannot verify migration tracking",
        })
        return issues

    try:
        log_text = schema_log.read_text(errors="replace")
    except OSError:
        return issues

    if highest_num not in log_text:
        issues.append({
            "severity": "MEDIUM",
            "category": "migration-gap",
            "path": "docs/dev-knowledge/schema-log.md",
            "line": 0,
            "detail": f"highest migration {highest} not mentioned in schema-log.md",
        })

    return issues


# --- output ---

def render_markdown(issues: list[dict]) -> str:
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    grouped: dict[str, list[dict]] = {}
    for issue in issues:
        sev = issue["severity"]
        grouped.setdefault(sev, []).append(issue)

    lines = ["# Architecture Audit", ""]

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        bucket = grouped.get(sev, [])
        lines.append(f"## {sev} ({len(bucket)} issues)")
        lines.append("")
        if not bucket:
            lines.append("_None found._")
        else:
            lines.append("| Path | Category | Detail |")
            lines.append("|------|----------|--------|")
            for item in bucket:
                path = item["path"]
                cat = item["category"]
                detail = item["detail"].replace("|", "/")
                lines.append(f"| `{path}` | {cat} | {detail} |")
        lines.append("")

    total = len(issues)
    lines.append(f"**Total issues: {total}**")
    return "\n".join(lines)


def main() -> int:
    root = repo_root()

    all_issues: list[dict] = []
    all_issues.extend(check_god_classes(root))
    all_issues.extend(check_layer_violations(root))
    all_issues.extend(check_dead_imports(root))
    all_issues.extend(check_migration_gap(root))

    print(render_markdown(all_issues))
    return 0


if __name__ == "__main__":
    sys.exit(main())
