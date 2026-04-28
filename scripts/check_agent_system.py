"""Verify the AgentNexLiFy coding-agent control plane.

This check is intentionally stdlib-only so CI can run it before dependency
installation. It validates the guardrails that make the autonomous loop safe:
the repo brain, Everything Claude Code agents, Claude Code pin, and issue-to-PR workflows.
"""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

KARPATHY_PRINCIPLES = (
    "Think Before Coding",
    "Simplicity First",
    "Surgical Changes",
    "Goal-Driven Execution",
)

PROJECT_AGENTS = (
    "architect",
    "backend-dev",
    "code-reviewer",
    "devops",
    "frontend-dev",
    "performance-optimizer",
    "qa-tester",
    "refactor-cleaner",
    "schema-guardian",
    "security-reviewer",
    "tdd-guide",
    "vertical-checker",
    "widget-specialist",
)

ECC_AGENTS = (
    "a11y-architect",
    "build-error-resolver",
    "chief-of-staff",
    "code-architect",
    "code-explorer",
    "code-simplifier",
    "comment-analyzer",
    "conversation-analyzer",
    "cpp-build-resolver",
    "cpp-reviewer",
    "csharp-reviewer",
    "dart-build-resolver",
    "database-reviewer",
    "docs-lookup",
    "doc-updater",
    "e2e-runner",
    "flutter-reviewer",
    "go-build-resolver",
    "go-reviewer",
    "harness-optimizer",
    "healthcare-reviewer",
    "java-build-resolver",
    "java-reviewer",
    "kotlin-build-resolver",
    "kotlin-reviewer",
    "loop-operator",
    "opensource-forker",
    "opensource-packager",
    "opensource-sanitizer",
    "planner",
    "pr-test-analyzer",
    "python-reviewer",
    "pytorch-build-resolver",
    "rust-build-resolver",
    "rust-reviewer",
    "seo-specialist",
    "silent-failure-hunter",
    "type-design-analyzer",
    "typescript-reviewer",
)

EXPECTED_ECC_COMMIT = "7eb7c598fba384a5e5829928945d59868c6eb075"
CLAUDE_CODE_PIN = "@anthropic-ai/claude-code@2.1.98"


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def read_json(path: str) -> dict:
    return json.loads(read_text(path))


def check(condition: bool, label: str, failures: list[str]) -> None:
    if condition:
        print(f"PASS {label}")
        return
    print(f"FAIL {label}")
    failures.append(label)


def file_exists(path: str) -> bool:
    return (ROOT / path).is_file()


def main() -> int:
    failures: list[str] = []

    claude_md = read_text("CLAUDE.md")
    check(file_exists("CLAUDE.md"), "CLAUDE.md exists", failures)
    for principle in KARPATHY_PRINCIPLES:
        check(principle in claude_md, f"CLAUDE.md includes {principle}", failures)

    check(
        file_exists(".claude/skills/karpathy-guidelines/SKILL.md"),
        "Karpathy guidelines skill exists",
        failures,
    )
    check(
        file_exists(".codex/skills/agentnexlify-task-loader/SKILL.md"),
        "AgentNexLiFy task loader skill exists",
        failures,
    )

    agent_dir = ROOT / ".claude" / "agents"
    agent_count = len(list(agent_dir.glob("*.md")))
    check(agent_count >= 57, f"at least 57 Claude agents installed ({agent_count})", failures)

    for agent in PROJECT_AGENTS + ECC_AGENTS:
        check(file_exists(f".claude/agents/{agent}.md"), f"agent exists: {agent}", failures)

    lock = read_json(".claude/everything-claude-code.lock.json")
    check(
        lock.get("source_commit") == EXPECTED_ECC_COMMIT,
        "Everything Claude Code source commit is pinned",
        failures,
    )
    check(
        sorted(lock.get("agents", [])) == sorted(ECC_AGENTS),
        "Everything Claude Code agent list matches policy",
        failures,
    )
    check(
        file_exists(lock.get("license_file", "")),
        "Everything Claude Code license is vendored",
        failures,
    )

    package = read_json("package.json")
    scripts = package.get("scripts", {})
    check(
        scripts.get("check") == "npm run check:quick",
        "package check script points to quick checks",
        failures,
    )
    check(
        scripts.get("check:quick")
        == "npm run agent-system:check && npm run check:skills && npm run sync-skills:check && npm run skills:eval && npm run eval:agent-routing && npm run check:project && npm run sync-widget:check && npm run check:codex-orchestration",
        "package quick check script wires the expected checks",
        failures,
    )
    check(
        scripts.get("check:full") == "npm run check:quick && npm run build && npm run test",
        "package full check script builds on quick checks",
        failures,
    )
    check(
        scripts.get("check:local-release")
        == "npm run check:quick && npm run build && npm run test:backend:focused && npm run test:frontend",
        "package local release check script uses available local gates",
        failures,
    )
    python_runner = "python scripts/run_python.py"
    check(
        file_exists("scripts/run_python.py"),
        "preferred Python runner exists",
        failures,
    )
    check(
        file_exists("docs/AGENT_ROUTING.md"),
        "agent routing policy exists",
        failures,
    )
    check(
        file_exists("config/agent-routing-eval.json"),
        "agent routing eval catalog exists",
        failures,
    )
    check(
        file_exists("scripts/evaluate_agent_routing.py"),
        "agent routing eval harness exists",
        failures,
    )
    check(
        scripts.get("check:project") == f"{python_runner} scripts/check_project_invariants.py",
        "package project check script points at project invariants",
        failures,
    )
    check(
        scripts.get("check:skills") == f"{python_runner} scripts/check_skills.py",
        "package skill metadata check script is registered",
        failures,
    )
    check(
        scripts.get("skills:eval") == f"{python_runner} scripts/run_skill_evals.py",
        "package skill trigger eval script is registered",
        failures,
    )
    check(
        scripts.get("eval:agent-routing")
        == f"{python_runner} scripts/evaluate_agent_routing.py --check",
        "package agent routing eval script is registered",
        failures,
    )
    check(
        scripts.get("sync-skills") == f"{python_runner} scripts/sync_skills.py --write",
        "package canonical skill sync write script is registered",
        failures,
    )
    check(
        scripts.get("sync-skills:check") == f"{python_runner} scripts/sync_skills.py",
        "package canonical skill sync dry-run script is registered",
        failures,
    )
    check(
        scripts.get("sync-widget:check")
        == f"{python_runner} scripts/sync_widget_assets.py --check",
        "package widget sync check script points at widget asset verification",
        failures,
    )
    check(
        scripts.get("check:codex-orchestration")
        == f"{python_runner} scripts/check_codex_orchestration_adoption.py",
        "package codex orchestration check script points at orchestration adoption verification",
        failures,
    )
    check(
        scripts.get("build") == "npm run build:frontend",
        "package build script points to the frontend build",
        failures,
    )
    check(
        CLAUDE_CODE_PIN in scripts.get("claude:2.1.98", ""),
        "Claude Code 2.1.98 npm script is pinned",
        failures,
    )
    check(
        scripts.get("agent-system:check") == f"{python_runner} scripts/check_agent_system.py",
        "agent-system check script is registered",
        failures,
    )
    check(
        scripts.get("test:backend") == f"{python_runner} -m pytest tests/ -q",
        "backend tests run through preferred local Python",
        failures,
    )
    check(
        scripts.get("test:backend:focused")
        == f"{python_runner} -m pytest tests/test_autopilot_orchestration.py tests/test_local_seo_parsers.py -q",
        "focused backend tests run through preferred local Python",
        failures,
    )
    check(
        scripts.get("autopilot:dry-run")
        == f"{python_runner} scripts/autopilot/classify_and_dispatch.py --dry-run",
        "autopilot local dry-run script is registered",
        failures,
    )
    check(
        scripts.get("autopilot:dry-run:issue")
        == f"{python_runner} scripts/autopilot/classify_and_dispatch.py --dry-run --issue",
        "autopilot single-issue dry-run script is registered",
        failures,
    )

    manifest = read_json(".ai/manifest.json")
    codex_skills = manifest.get("skills", {}).get("codex", {}).get("skills", [])
    check(
        "agentnexlify-task-loader" in codex_skills,
        ".ai manifest lists the task loader codex skill",
        failures,
    )

    settings = read_json(".claude/settings.json")
    env = settings.get("env", {})
    check(
        env.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1",
        "Claude agent teams are enabled",
        failures,
    )
    settings_text = read_text(".claude/settings.json")
    check("WebFetch|WebSearch" in settings_text, "WebFetch/WebSearch block is configured", failures)
    check("git push" in settings_text, "pre-push review hook is configured", failures)

    issue_to_pr_skill = read_text(".claude/skills/issue-to-pr-loop/SKILL.md")
    issue_to_pr = read_text("scripts/automation/issue-to-pr.sh")
    pr_feedback = read_text("scripts/automation/pr-feedback.sh")
    agent_routing = read_text("docs/AGENT_ROUTING.md")
    routing_eval = read_text("config/agent-routing-eval.json")
    check("every 15min" in issue_to_pr_skill, "issue-to-PR skill documents 15 minute polling", failures)
    check(CLAUDE_CODE_PIN in issue_to_pr, "issue-to-PR loop uses pinned Claude Code", failures)
    check(CLAUDE_CODE_PIN in pr_feedback, "PR feedback loop uses pinned Claude Code", failures)
    check("run_claude" in issue_to_pr, "issue-to-PR loop routes Claude calls through wrapper", failures)
    check("run_claude" in pr_feedback, "PR feedback loop routes Claude calls through wrapper", failures)
    check("git worktree add" in issue_to_pr, "issue-to-PR loop uses worktree isolation", failures)
    check("gh pr create" in issue_to_pr, "issue-to-PR loop creates pull requests", failures)
    for routing_label in ("ai-routine", "ai-docs", "ai-tests", "ai-risky"):
        check(
            routing_label in agent_routing and routing_label in routing_eval,
            f"agent routing policy covers {routing_label}",
            failures,
        )
    check("--yolo" in agent_routing, "agent routing policy forbids yolo mode", failures)
    check(
        "premium-codex-claude" in routing_eval and "low-cost-routine" in routing_eval,
        "agent routing eval covers premium and low-cost routes",
        failures,
    )

    issue_loop = read_text(".github/workflows/autopilot-issue-loop.yml")
    check('"*/15 * * * *"' in issue_loop, "autopilot issue loop runs every 15 minutes", failures)
    check("workflow_dispatch" in issue_loop, "autopilot issue loop can run manually", failures)
    check("classify_and_dispatch.py" in issue_loop, "issue loop dispatch script is wired", failures)
    check("AUTOPILOT_MAX_TOKENS_PER_RUN" in issue_loop, "issue loop token budget is wired", failures)
    check("AUTOPILOT_MAX_ACTIVE_RUNS" in issue_loop, "issue loop active-run cap is wired", failures)

    pr_loop = read_text(".github/workflows/autopilot-pr-review.yml")
    check("pull_request_review_comment" in pr_loop, "PR review handler listens for comments", failures)
    check("implement_review_comment.py" in pr_loop, "PR review implementation script is wired", failures)
    check("AUTOPILOT_MAX_TOKENS_PER_RUN" in pr_loop, "PR review token budget is wired", failures)

    dispatcher = read_text("scripts/autopilot/classify_and_dispatch.py")
    review_handler = read_text("scripts/autopilot/implement_review_comment.py")
    workflow_contract = read_text("docs/AUTOPILOT_WORKFLOW.md")
    check("Autopilot Workflow" in workflow_contract, "autopilot workflow contract exists", failures)
    check("WORKFLOW_CONTRACT_PATH" in dispatcher, "issue loop loads workflow contract", failures)
    check("ROUTING_POLICY_PATH" in dispatcher, "issue loop loads agent routing policy", failures)
    check("ai-risky" in workflow_contract, "autopilot workflow documents risky routing label", failures)
    check("Autopilot Proof Of Work" in dispatcher, "issue loop writes PR proof of work", failures)
    check("AUTOPILOT_MAX_ACTIVE_RUNS" in dispatcher, "issue loop enforces active-run cap", failures)
    check("WORKFLOW_CONTRACT_PATH" in review_handler, "PR review handler loads workflow contract", failures)
    check("ROUTING_POLICY_PATH" in review_handler, "PR review handler loads agent routing policy", failures)
    check('"codex", "exec", "--write"' in dispatcher, "issue loop dispatches to Codex", failures)
    check('"codex", "exec", "--write"' in review_handler, "PR review handler dispatches to Codex", failures)
    check('"worktree", "add"' in dispatcher, "issue loop uses worktree isolation", failures)
    check(
        all(token in dispatcher for token in ('"gh"', '"pr"', '"create"', "labels.AUTOPILOT_PR")),
        "issue loop creates pull requests",
        failures,
    )

    if failures:
        print("")
        print(f"{len(failures)} agent-system check(s) failed.")
        return 1

    print("")
    print("Agent system check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
