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

## Token Optimization (RTK)
RTK is installed as a PreToolUse hook. Meta commands: `rtk gain`, `rtk gain --history`, `rtk discover`. Requires `jq`. If hook fails silently, check `which jq && which rtk`.
