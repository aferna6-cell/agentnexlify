#!/usr/bin/env python3
"""Fail locally when the cross-provider team protocol drifts or can spend CI minutes."""

from __future__ import annotations

import sys
from pathlib import Path

from teamctl import TeamError, load_contract


ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def require_file(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        ERRORS.append(f"missing required file: {path}")
        return ""
    return target.read_text(encoding="utf-8")


def require_text(path: str, needles: list[str]) -> None:
    content = require_file(path)
    for needle in needles:
        if needle not in content:
            ERRORS.append(f"{path} must contain {needle!r}")


def main() -> int:
    try:
        contract = load_contract()
    except TeamError as exc:
        ERRORS.append(str(exc))
        contract = None

    required_files = [
        "docs/TEAM_OPERATING_CONTRACT.md",
        ".ai/team-contract.json",
        "scripts/teamctl.py",
        "tests/test_teamctl.py",
        "KIMI.md",
        ".github/ISSUE_TEMPLATE/cross-agent-task.yml",
        ".github/pull_request_template.md",
        "scripts/hooks/prepare-commit-msg",
    ]
    for path in required_files:
        require_file(path)

    if contract:
        for path in contract["required_reads"]:
            require_file(path)
        for path in contract.get("provider_adapters", {}).values():
            require_file(path)
        if not contract["coordination"].get("trusted_github_actors"):
            ERRORS.append("team contract must name at least one trusted GitHub event actor")

    require_text(
        "AGENTS.md",
        ["docs/TEAM_OPERATING_CONTRACT.md", "scripts/teamctl.py preflight", "[skip ci]"],
    )
    require_text(
        "CLAUDE.md",
        ["docs/TEAM_OPERATING_CONTRACT.md", "scripts/teamctl.py preflight", "[skip ci]"],
    )
    require_text(
        "KIMI.md",
        ["docs/TEAM_OPERATING_CONTRACT.md", "scripts/teamctl.py preflight", "[skip ci]"],
    )
    require_text(
        ".claude/skills/coordinator/SKILL.md",
        ["scripts/teamctl.py", "GitHub issue"],
    )
    require_text(
        ".claude/skills/team-orchestration/SKILL.md",
        ["scripts/teamctl.py", "GitHub issue"],
    )

    for workflow in (
        ".github/workflows/pr-check.yml",
        ".github/workflows/agent-config-security.yml",
        ".github/workflows/lead-qualifier-eval.yml",
    ):
        require_text(workflow, ["startsWith(github.head_ref, 'team/')"])

    require_text(
        ".github/workflows/autopilot-pr-review.yml",
        ["startsWith(github.event.pull_request.head.ref, 'team/')"],
    )
    require_text("scripts/hooks/prepare-commit-msg", ["team/*", "[skip ci]"])
    require_text("scripts/install-hooks.sh", ["prepare-commit-msg"])
    require_text("package.json", ["team:check", "scripts/check_team_protocol.py"])

    if ERRORS:
        print("Team protocol check failed:", file=sys.stderr)
        for error in ERRORS:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Team protocol check passed (cross-provider coordination, local proof, zero Actions minutes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
