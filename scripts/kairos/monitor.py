#!/usr/bin/env python3
"""
KAIROS monitor — Project health monitoring.

Checks build health, uncommitted changes, code smells in recent commits,
and migration/schema-log consistency.

Read-only: never modifies source files.
"""

import os
import sys
import subprocess
import datetime
import re
import pathlib

# --- Configuration ---

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "docs" / "kairos"
FRONTEND_DIR = REPO_ROOT / "frontend"
MIGRATIONS_DIR = REPO_ROOT / "migrations"
SCHEMA_LOG = REPO_ROOT / "docs" / "dev-knowledge" / "schema-log.md"
BACKEND_DIR = REPO_ROOT / "backend"

TODAY = datetime.date.today().isoformat()
NOW = datetime.datetime.now()


def run_cmd(cmd, cwd=None, timeout=120):
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or str(REPO_ROOT),
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def check_frontend_syntax():
    """Check frontend for obvious syntax/build issues without a full build."""
    findings = []

    # Check if node_modules exists
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        findings.append({
            "severity": "warning",
            "message": "frontend/node_modules missing — npm install needed",
        })
        return findings

    # Try a quick typecheck / lint if available
    package_json = FRONTEND_DIR / "package.json"
    if package_json.exists():
        content = package_json.read_text(encoding="utf-8", errors="replace")

        # Check if there's a lint script
        if '"lint"' in content:
            code, stdout, stderr = run_cmd(
                ["npm", "run", "lint", "--", "--max-warnings=0"],
                cwd=str(FRONTEND_DIR),
                timeout=60,
            )
            if code != 0:
                error_lines = (stderr or stdout).splitlines()[:10]
                findings.append({
                    "severity": "warning",
                    "message": f"Frontend lint issues: {len(error_lines)} lines of output",
                    "details": "\n".join(error_lines),
                })

    # Quick check: scan for obvious JS syntax issues in recently modified files
    code, stdout, _ = run_cmd(
        ["git", "diff", "--name-only", "--diff-filter=M", "HEAD~5", "HEAD", "--", "frontend/src/"],
        timeout=15,
    )
    if code == 0 and stdout:
        recent_files = [f for f in stdout.splitlines() if f.endswith((".js", ".jsx"))]
        for rf in recent_files[:10]:
            full_path = REPO_ROOT / rf
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding="utf-8", errors="replace")
                    # Check for common issues
                    if "from __future__" in content:
                        findings.append({
                            "severity": "error",
                            "message": f"Python import in JS file: {rf}",
                        })
                    # Check for unclosed template literals or obvious syntax breaks
                    open_backticks = content.count("`")
                    if open_backticks % 2 != 0:
                        findings.append({
                            "severity": "warning",
                            "message": f"Odd number of backticks in {rf} (possible unclosed template literal)",
                        })
                except Exception:
                    pass

    if not findings:
        findings.append({
            "severity": "ok",
            "message": "No frontend syntax issues detected",
        })

    return findings


def check_uncommitted_changes():
    """Check for uncommitted changes and their age."""
    findings = []

    # Check git status
    code, stdout, _ = run_cmd(["git", "status", "--porcelain"])
    if code != 0:
        findings.append({
            "severity": "error",
            "message": "Could not run git status",
        })
        return findings

    if not stdout.strip():
        findings.append({
            "severity": "ok",
            "message": "Working tree is clean",
        })
        return findings

    changed_files = [line.strip() for line in stdout.splitlines() if line.strip()]
    findings.append({
        "severity": "info",
        "message": f"{len(changed_files)} uncommitted changes",
        "details": "\n".join(changed_files[:20]),
    })

    # Check how old the uncommitted changes are by looking at file modification times
    old_files = []
    cutoff = NOW - datetime.timedelta(hours=24)

    for line in changed_files:
        # Parse git status format: "XY filename" or "XY filename -> newname"
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            continue
        filepath = parts[1].split(" -> ")[-1].strip()
        full_path = REPO_ROOT / filepath
        if full_path.exists():
            try:
                mtime = datetime.datetime.fromtimestamp(full_path.stat().st_mtime)
                if mtime < cutoff:
                    age_hours = int((NOW - mtime).total_seconds() / 3600)
                    old_files.append((filepath, age_hours))
            except Exception:
                pass

    if old_files:
        findings.append({
            "severity": "warning",
            "message": f"{len(old_files)} uncommitted files older than 24h",
            "details": "\n".join(f"  {f} ({h}h old)" for f, h in old_files[:10]),
        })

    return findings


def check_code_smells_in_recent_commits():
    """Check for TODO/FIXME/HACK in recent commits."""
    findings = []

    # Get diff of recent commits
    code, stdout, _ = run_cmd(
        ["git", "log", "--since=24 hours ago", "-p", "--no-color", "--diff-filter=A", "--diff-filter=M"],
        timeout=30,
    )

    if code != 0 or not stdout:
        # Try simpler approach
        code, stdout, _ = run_cmd(
            ["git", "diff", "HEAD~3", "HEAD", "--no-color"],
            timeout=30,
        )

    if code != 0 or not stdout:
        findings.append({
            "severity": "info",
            "message": "No recent diff available to scan",
        })
        return findings

    # Scan added lines for code smells
    smell_patterns = {
        "TODO": re.compile(r'^\+.*\bTODO\b', re.IGNORECASE),
        "FIXME": re.compile(r'^\+.*\bFIXME\b', re.IGNORECASE),
        "HACK": re.compile(r'^\+.*\bHACK\b', re.IGNORECASE),
        "XXX": re.compile(r'^\+.*\bXXX\b'),
        "NOQA": re.compile(r'^\+.*\bnoqa\b'),
    }

    smell_counts = {k: [] for k in smell_patterns}
    current_file = ""

    for line in stdout.splitlines():
        if line.startswith("diff --git"):
            parts = line.split(" b/")
            current_file = parts[-1] if len(parts) > 1 else ""
        elif line.startswith("+") and not line.startswith("+++"):
            for name, pattern in smell_patterns.items():
                if pattern.search(line):
                    smell_counts[name].append((current_file, line[1:].strip()[:80]))

    for name, matches in smell_counts.items():
        if matches:
            findings.append({
                "severity": "info",
                "message": f"{len(matches)} {name} comment(s) in recent changes",
                "details": "\n".join(f"  {f}: {text}" for f, text in matches[:5]),
            })

    # Check for dangerous patterns in added lines — only in .py files
    dangerous_patterns = {
        "from __future__ import annotations": "Breaks FastAPI Pydantic resolution",
        "except BaseException": "Prevents graceful shutdown",
        "except:": "Bare except -- swallows all errors",
    }

    current_file_ext = ""
    for line in stdout.splitlines():
        if line.startswith("diff --git"):
            parts = line.split(" b/")
            cf = parts[-1] if len(parts) > 1 else ""
            current_file_ext = os.path.splitext(cf)[1]
        elif line.startswith("+") and not line.startswith("+++"):
            # Only flag dangerous patterns in Python source files
            if current_file_ext != ".py":
                continue
            for pattern_text, description in dangerous_patterns.items():
                if pattern_text in line:
                    findings.append({
                        "severity": "error",
                        "message": f"Dangerous pattern added: {pattern_text} ({description})",
                        "details": line[1:].strip()[:120],
                    })

    if not any(f["severity"] != "info" for f in findings) and not findings:
        findings.append({
            "severity": "ok",
            "message": "No code smells in recent commits",
        })

    return findings


def check_migration_consistency():
    """Check if migration files are referenced in schema-log.md."""
    findings = []

    if not MIGRATIONS_DIR.exists():
        findings.append({
            "severity": "warning",
            "message": "migrations/ directory not found",
        })
        return findings

    # Get all migration files
    migration_files = sorted([
        f.name for f in MIGRATIONS_DIR.iterdir()
        if f.is_file() and f.suffix == ".sql"
    ])

    if not migration_files:
        findings.append({
            "severity": "info",
            "message": "No migration files found",
        })
        return findings

    # Read schema-log
    schema_log_content = ""
    if SCHEMA_LOG.exists():
        schema_log_content = SCHEMA_LOG.read_text(encoding="utf-8", errors="replace").lower()
    else:
        findings.append({
            "severity": "warning",
            "message": "schema-log.md not found",
        })
        return findings

    # Check which migrations are NOT mentioned in schema-log
    unlogged = []
    for mf in migration_files:
        # Extract the migration number/name for matching
        # Files like "074_conversations_lead_captured.sql"
        name_without_ext = mf.replace(".sql", "").lower()
        # Check if the number or full name appears in schema-log
        number_match = re.match(r'^(\d+)', mf)
        number = number_match.group(1) if number_match else ""

        found = False
        if name_without_ext in schema_log_content:
            found = True
        elif number and re.search(rf'\b0*{number}\b', schema_log_content):
            found = True
        # Also try the descriptive part
        elif "_" in name_without_ext:
            desc_part = name_without_ext.split("_", 1)[1] if "_" in name_without_ext else ""
            if desc_part and desc_part in schema_log_content:
                found = True

        if not found:
            unlogged.append(mf)

    if unlogged:
        findings.append({
            "severity": "warning",
            "message": f"{len(unlogged)} migration(s) not referenced in schema-log.md",
            "details": "\n".join(f"  {f}" for f in unlogged[:15]),
        })
    else:
        findings.append({
            "severity": "ok",
            "message": f"All {len(migration_files)} migrations referenced in schema-log.md",
        })

    return findings


def check_backend_dangerous_imports():
    """Check for dangerous imports in backend router files."""
    findings = []
    routers_dir = BACKEND_DIR / "routers"

    if not routers_dir.exists():
        return findings

    for py_file in routers_dir.glob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if "from __future__ import annotations" in content:
                findings.append({
                    "severity": "error",
                    "message": f"DANGEROUS: from __future__ import annotations in {py_file.name}",
                })
        except Exception:
            pass

    if not findings:
        findings.append({
            "severity": "ok",
            "message": "No dangerous imports in backend routers",
        })

    return findings


def check_env_safety():
    """Check that .env files are gitignored."""
    findings = []

    code, stdout, _ = run_cmd(["git", "ls-files", "--cached", ".env", "*.env", ".env.*"])
    if code == 0 and stdout.strip():
        # Exclude .env.example which is intentionally tracked
        tracked_envs = [
            f for f in stdout.strip().splitlines()
            if not f.strip().endswith(".example") and not f.strip().endswith(".sample")
        ]
        if tracked_envs:
            findings.append({
                "severity": "error",
                "message": f"WARNING: {len(tracked_envs)} .env file(s) tracked by git",
                "details": "\n".join(tracked_envs),
            })
    else:
        findings.append({
            "severity": "ok",
            "message": ".env files are not tracked by git",
        })

    return findings


def generate_health_report(all_sections):
    """Generate the health report markdown."""
    lines = []
    lines.append(f"# KAIROS Health Report -- {TODAY}")
    lines.append("")
    lines.append(f"Generated: {datetime.datetime.now().isoformat()}")
    lines.append("")

    # Overall status
    error_count = sum(
        1 for section in all_sections.values()
        for f in section
        if f["severity"] == "error"
    )
    warning_count = sum(
        1 for section in all_sections.values()
        for f in section
        if f["severity"] == "warning"
    )

    if error_count > 0:
        status = "UNHEALTHY"
    elif warning_count > 0:
        status = "NEEDS ATTENTION"
    else:
        status = "HEALTHY"

    lines.append(f"## Overall: {status}")
    lines.append("")
    lines.append(f"- Errors: {error_count}")
    lines.append(f"- Warnings: {warning_count}")
    lines.append("")

    severity_icons = {
        "error": "[ERROR]",
        "warning": "[WARN]",
        "info": "[INFO]",
        "ok": "[OK]",
    }

    for section_name, findings in all_sections.items():
        lines.append(f"## {section_name}")
        lines.append("")
        for f in findings:
            icon = severity_icons.get(f["severity"], "[?]")
            lines.append(f"- {icon} {f['message']}")
            if "details" in f and f["details"]:
                for detail_line in f["details"].splitlines()[:10]:
                    lines.append(f"  {detail_line}")
        lines.append("")

    return "\n".join(lines)


def main():
    print(f"KAIROS monitor starting ({TODAY})")

    all_sections = {}

    print("  Checking frontend syntax...")
    all_sections["Frontend Syntax"] = check_frontend_syntax()

    print("  Checking uncommitted changes...")
    all_sections["Uncommitted Changes"] = check_uncommitted_changes()

    print("  Checking code smells in recent commits...")
    all_sections["Code Smells (Recent)"] = check_code_smells_in_recent_commits()

    print("  Checking migration consistency...")
    all_sections["Migration Consistency"] = check_migration_consistency()

    print("  Checking backend imports...")
    all_sections["Backend Import Safety"] = check_backend_dangerous_imports()

    print("  Checking .env safety...")
    all_sections["Environment File Safety"] = check_env_safety()

    # Generate report
    print("  Writing health report...")
    report = generate_health_report(all_sections)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / f"health-{TODAY}.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Health report: {report_path}")

    # Count issues
    error_count = sum(
        1 for section in all_sections.values()
        for f in section
        if f["severity"] == "error"
    )
    warning_count = sum(
        1 for section in all_sections.values()
        for f in section
        if f["severity"] == "warning"
    )

    print(f"KAIROS monitor complete. {error_count} errors, {warning_count} warnings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
