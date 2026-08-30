#!/usr/bin/env python3
"""Fail when the Slack agent-team pack drifts out of sync."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".ai" / "slack-agent-team.json"
ERRORS: list[str] = []

REQUIRED_AGENT_IDS = ("grok", "fable5", "codex", "kimi3")
REQUIRED_CHANNELS = ("agent-grok", "agent-product", "agent-code", "agent-review")
REQUIRED_INVARIANT_NEEDLES = (
    "GitHub Issues remain the durable task hub",
    "scripts/teamctl.py",
    "[skip ci]",
    "aferna6-cell/agentnexlify",
    "Agent-Nexlify-OS",
)
REQUIRED_PROMPT_NEEDLES = (
    "aferna6-cell/agentnexlify",
    "teamctl",
    "[skip ci]",
    "Send to Slack",
    "Never use `Agent-Nexlify-OS`",
)


def error(message: str) -> None:
    ERRORS.append(message)


def require_file(path: Path) -> str:
    if not path.is_file():
        error(f"missing required file: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def require_text(path: Path, needles: tuple[str, ...]) -> None:
    content = require_file(path)
    if not content:
        return
    for needle in needles:
        if needle not in content:
            error(f"{path.relative_to(ROOT)} must contain {needle!r}")


def load_config() -> dict:
    raw = require_file(CONFIG_PATH)
    if not raw:
        return {}
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        error(f".ai/slack-agent-team.json is not valid JSON: {exc}")
        return {}
    if not isinstance(config, dict):
        error(".ai/slack-agent-team.json must be an object")
        return {}
    return config


def check_config(config: dict) -> None:
    if not config:
        return
    for key in (
        "schema_version",
        "durable_hub",
        "canonical_repo",
        "workspace",
        "existing_channels",
        "specialist_channels",
        "agents",
        "invariants",
        "install",
    ):
        if key not in config:
            error(f".ai/slack-agent-team.json missing {key}")

    if config.get("durable_hub") != "github_issue":
        error("durable_hub must be github_issue")
    if config.get("canonical_repo") != "aferna6-cell/agentnexlify":
        error("canonical_repo must be aferna6-cell/agentnexlify")
    if config.get("not_the_repo") != "aferna6-cell/Agent-Nexlify-OS":
        error("not_the_repo must name Agent-Nexlify-OS")

    workspace = config.get("workspace") or {}
    if workspace.get("slack_team_id") != "T0AU024EH38":
        error("workspace.slack_team_id must stay the live Agent Nexlify team")
    if workspace.get("cursor_user_id") != "U0BTH748Z3P":
        error("workspace.cursor_user_id must stay the live @cursor bot")

    channels = {row.get("name") for row in config.get("specialist_channels") or [] if isinstance(row, dict)}
    for name in REQUIRED_CHANNELS:
        if name not in channels:
            error(f"specialist channel missing: {name}")

    agents = config.get("agents") or []
    agent_ids = [row.get("id") for row in agents if isinstance(row, dict)]
    if tuple(agent_ids) != REQUIRED_AGENT_IDS:
        error(f"agents must be exactly {REQUIRED_AGENT_IDS} in that order, got {tuple(agent_ids)}")

    for agent in agents:
        if not isinstance(agent, dict):
            error("each agent must be an object")
            continue
        prompt = ROOT / str(agent.get("prompt_file", ""))
        require_text(prompt, REQUIRED_PROMPT_NEEDLES)
        prefixes = agent.get("hq_prefixes") or []
        if len(prefixes) < 2:
            error(f"agent {agent.get('id')} must declare at least two HQ prefixes")

    invariants = "\n".join(config.get("invariants") or [])
    for needle in REQUIRED_INVARIANT_NEEDLES:
        if needle not in invariants:
            error(f"invariants must mention {needle!r}")


def main() -> int:
    config = load_config()
    check_config(config)
    require_text(
        ROOT / "docs" / "ops" / "slack-agent-team.md",
        (
            "#agent-grok",
            "cursor.com/automations",
            "Anyone in the channel",
            "scripts/teamctl.py",
        ),
    )
    require_text(
        ROOT / "specs" / "slack-agent-team_spec.md",
        ("#agent-grok", "Anyone in the channel", "teamctl"),
    )
    require_text(
        ROOT / "docs" / "TEAM_OPERATING_CONTRACT.md",
        ("Slack is an optional invocation surface", ".ai/slack-agent-team.json"),
    )
    require_text(
        ROOT / "package.json",
        ('"slack-team:check"', "scripts/check_slack_agent_team.py"),
    )

    if ERRORS:
        print("Slack agent-team check failed:", file=sys.stderr)
        for item in ERRORS:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("Slack agent-team check passed (config, prompts, and GitHub-hub invariants).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
