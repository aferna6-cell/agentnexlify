---
paths:
  - "**/*"
---

# Workflow & Decision Rules

## Decision Engine
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions)
- If something goes wrong, STOP and re-plan immediately — don't keep pushing
- When evidence contradicts instinct, trust the evidence
- Simplicity first — make every change as simple as possible, minimize code impact
- Deterministic-first: don't use an LLM for something a deterministic program can do

## Error Handling (Anti-Desperation)
When you hit an error: (1) Read what it actually says, (2) Identify the smallest fix, (3) Do NOT escalate complexity, (4) Do NOT abandon your approach after one failure, (5) One calm step at a time. Composure produces better solutions than urgency.

## Quality Gates
- Never mark a task complete without proving it works
- Ask: "Would a staff engineer approve this?"
- After any correction from the user, update `docs/dev-knowledge/bug-patterns.md`
- Every bug fixed becomes a permanent rule

## Compound Engineering
Default workflow for non-trivial tasks. 5 agents sequentially: Brainstormer → Planner → Executor → Reviewer → Vertical Checker. Trigger: `/compound` or any task touching 2+ files. Full details: `.claude/skills/compound-engineering/SKILL.md`

## Subagent Strategy
- Use subagents to keep main context clean
- One task per subagent for focused execution
- Delegation order: schema-guardian → backend-dev + frontend-dev (parallel) → qa-tester

## Token Optimization (3 layers, installed 2026-04-24)

### RTK (Rust Token Killer) — Bash hook
- Binary: `/c/Users/aidan/bin/rtk.exe` (v0.37.2, Apache-2.0)
- Dep: `/c/Users/aidan/bin/jq.exe` (v1.8.1)
- Wired: `.claude/settings.json` PreToolUse → `bash scripts/claude-hooks/rtk-rewrite.sh`
- Meta: `rtk gain`, `rtk gain --history`, `rtk discover`
- Fails silently if binary or jq missing — check `which rtk && which jq`

### Token Savior — MCP server
- Binary: `C:/Users/aidan/AppData/Roaming/Python/Python314/Scripts/token-savior.exe` (v2.6.0, MIT)
- Wired: `.mcp.json` entry `token-savior` with `WORKSPACE_ROOTS` env
- Exposes 106 MCP tools (tree-sitter symbol navigation, semantic chunks)
- Context cost: non-trivial. Disable if session feels slow.

### Context Mode — Claude Code plugin
- Source: `mksglu/context-mode` marketplace (ELv2 license)
- Install scope: user (installed via `npm run claude:2.1.98 -- plugin install context-mode@context-mode`)
- 4 PreToolUse hooks + SQLite FTS5 sandboxing
- Verify after restart: `/context-mode:ctx-doctor`

Version pin: all three verified against Claude Code 2.1.98 per `.claude/rules/claude-version-pin.md`.
