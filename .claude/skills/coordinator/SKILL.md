---
name: coordinator
description: Orchestrate multi-domain tasks by decomposing into a dependency DAG and dispatching specialized agents in waves. Load when user says 'coordinate this', 'orchestrate', /new-feature, /refactor, or task touches 3+ domains (schema, backend, frontend, widget, infra).
version: 1.0.0
origin: agentnexlify
user-invocable: true
triggers:
  - coordinate this
  - orchestrate
  - /new-feature
  - /refactor
  - multi-part task
  - complex task
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
effort: medium
---

# Coordinator — Multi-Agent Orchestrator

Auto-decomposes complex tasks into a dependency DAG and dispatches specialized agents in parallel waves. For Codex/Fable 5/Kimi 3 work, `docs/TEAM_OPERATING_CONTRACT.md` is authoritative: one GitHub issue is the durable task hub and `scripts/teamctl.py` owns claims, handoffs, reviews, and proof. Schema-guardian always goes first if DB is touched. qa-tester always goes last.

## When to Use

- User says "coordinate this", "orchestrate", or similar
- `/new-feature` command (full-stack feature build)
- `/refactor` command (multi-file restructuring)
- Any task touching 3+ domains (schema, backend, frontend, widget, infra)
- Any task where ordering matters (schema before backend, backend before frontend)

## When NOT to Use

- Single-file edits with no cross-cutting concerns
- Simple questions about the codebase
- Tasks clearly within one domain (delegate directly to that agent)
- User explicitly says to do it directly
- Exploratory tasks where scope is still unclear

## Phase 1: Task Decomposition

### 1.1 Analyze the Task

Identify:
- What database tables are touched? → schema-guardian goes first
- What backend endpoints are needed? → backend-dev
- What UI pages/components are needed? → frontend-dev
- Does the widget change? → widget-specialist
- Is there infra/deploy work? → devops
- What needs validation? → qa-tester (always last)

### 1.2 Build the Dependency DAG

```
1. [schema-guardian] Validate/create schema -- no blockers
2. [backend-dev] Build API endpoints -- blocked by 1
3. [frontend-dev] Build UI components -- blocked by 2
4. [backend-dev] Build background service -- blocked by 1
5. [qa-tester] Validate everything -- blocked by 2, 3, 4
```

### 1.3 Create the Coordination Plan

Write the plan to the shared GitHub issue before dispatching anything:
- Task summary
- DAG (numbered with blockers)
- Execution waves
- Status tracking

Each cross-provider agent must run `python3 scripts/teamctl.py preflight --issue <number> --agent <name>` and claim a non-overlapping lane before editing. Use `.claude/agent-comms/` only for ephemeral same-session specialist scratch; it is not durable team state.

## Phase 3: DAG Execution Rules

- Dispatch all tasks in the same wave simultaneously using the Agent tool
- Maximum 4 parallel agents at once
- Tasks with unmet dependencies wait — never dispatch a task whose blockers have not completed
- If an agent returns FAIL: pause all dependents, diagnose, re-dispatch, resume
- After each wave: read all handoffs, update the GitHub issue plan, and check next-wave blockers

## Completion Gate

After all waves: ALWAYS run qa-tester on the combined result. Only declare complete when qa-tester returns PASS or WARNINGS-only.

## Full Templates

For all 6 DAG templates (New Feature, Bug Fix, Refactor, Deploy, Widget Change, Database Migration), full agent prompt patterns, communication protocol, and worked example — see:
`references/decomposition-patterns.md`

## Gotchas

- Schema-guardian wins on schema questions. `architecture-decisions.md` wins on architecture.
- `widget/` and `frontend/public/widget/` must be byte-identical — widget-specialist always updates both.
- Passing context to cross-provider agents: record it with `teamctl handoff`; same-session specialists may use ephemeral output files.
- All team verification runs locally. Team branches and integration commits contain `[skip ci]`; never dispatch GitHub Actions for team work.

## Cross-refs

- `.claude/agents/schema-guardian.md`, `backend-dev.md`, `frontend-dev.md`, `widget-specialist.md`, `qa-tester.md`, `devops.md`
- `.claude/skills/compound-engineering/SKILL.md` — for tasks needing the 5-agent quality pipeline
- `references/decomposition-patterns.md` — full DAG templates and worked examples
