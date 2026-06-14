---
name: compound-engineering
description: Run 5-agent sequential pipeline (Brainstorm→Plan→Execute→Review→VerticalCheck) for any task touching 2+ files or domains. Load when user says /compound, 'full pipeline', '5-agent', or 'compound this'. Skip for single-file fixes or trivial renames.
version: 1.0.0
origin: agentnexlify
user-invocable: true
triggers:
  - /compound
  - compound this
  - full pipeline
  - 5-agent
  - compound pipeline
  - compound engineering
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
effort: high
---

# Compound Engineering — 5-Agent Quality Pipeline

**ultrathink** — this pipeline demands extended thinking at every stage. Brainstorm and Plan agents MUST reason deeply before any file touches.

5-agent sequential pipeline. Each agent is focused on exactly one job. Output quality is higher because no single agent tries to think about everything at once.

## When to Use

- Any feature, bug fix, refactor, or optimization touching 2+ files
- `/compound` command
- User says "compound this", "full pipeline", "5-agent"
- Any task where approach is unclear or risk is medium/high

## When NOT to Use

- Single-line fixes with obvious solutions
- Documentation-only changes
- Simple config changes
- User explicitly says "just do it" or "skip the pipeline"

## The 5 Agents

| # | Agent | Role | Output |
|---|-------|------|--------|
| 1 | Brainstormer | Problem Explorer | `brainstorm.md` |
| 2 | Planner | Technical Architect | `plan.md` |
| 3 | Executor | Code Writer (TDD) | commits + `execution-log.md` |
| 4 | Reviewer | Quality Gate | `review.md` |
| 5 | Vertical Checker | Cross-Cutting Auditor | `verticals.md` |

Each agent writes to `.claude/agent-comms/compound/{task-slug}/`. Next agent reads previous agent's output before starting.

## Pipeline Flow

```
Task In → Brainstormer → Planner → Executor → Reviewer → Vertical Checker → DONE
```

Reviewer verdict: PASS (advance), FIX (re-dispatch Executor), BLOCK (stop, alert user).
Vertical Checker verdict: ALL CLEAR (done), WARNINGS (note + done), BLOCKED (fix + re-run).

## Phase 1: Setup

```bash
mkdir -p .claude/agent-comms/compound/{task-slug}
```

Create manifest at `.claude/agent-comms/compound/{task-slug}/manifest.md` with status for all 5 agents.

## Phase 2–6: Run Agents in Order

For full prompt templates, agent rules, and completion criteria — see:
`references/full-pipeline.md`

**Opus 4.7 fan-out note:** Brainstormer and Planner phases often spawn sub-investigations (schema, prior art, edge cases). On 4.7, parallel spawning must be explicit. Use phrasings like "spawn subagents in the same turn to investigate X, Y, Z" or "dispatch schema-guardian + code-explorer + security-reviewer concurrently." Sequential phrasings like "investigate X, Y, Z" under-delegate. See `.claude/rules/parallel-approaches.md` and `.claude/rules/opus-4-7-prompting.md §4`.

Core constraints every agent must honor:
- `client_id` not `tenant_id` on leads/conversations tables
- No `from __future__ import annotations` in backend/routers/
- TDD: test first, verify fail, implement, verify pass, commit

## Phase 7: Completion

Write coordination-report.md. Update manifest. Clean up intermediate files.

## Gotchas

- 5 agents is heavy for small tasks. Under 5 min of work, skip compound — just do it.
- Brainstormer output can be too broad — Planner has to narrow it.
- Executor hitting test failures is normal — pass to Reviewer, do not loop Executor.
- Reviewer without diff context hallucinates issues — always feed actual git diff.
- Vertical Checker is the only agent that touches prod concerns — never skip it.
- Token cost: ~3-5x single-shot execution. Justify with complexity, not habit.

## Cross-refs

- `.claude/skills/worktree-orchestrator/SKILL.md` — parallel worktree execution
- `.claude/agents/schema-guardian.md`, `qa-tester.md`, `backend-dev.md`, `frontend-dev.md`
- `references/full-pipeline.md` — full prompt templates and phase details
