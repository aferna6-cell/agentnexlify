---
description: 5-agent quality pipeline — brainstorm, plan, execute, review, vertical check. Use for tasks touching 2+ files.
argument-hint: [task description]
model: opus
---

Run the compound-engineering skill. Read `.claude/skills/compound-engineering/SKILL.md` first — it owns the pipeline rules, and `references/full-pipeline.md` holds the per-agent prompt templates.

Task: `$ARGUMENTS`

**ultrathink** — Brainstormer and Planner reason deeply before any file is touched.

## Steps

1. Setup: `mkdir -p .claude/agent-comms/compound/{task-slug}` and write the 5-agent manifest.
2. Run the agents in order, each reading the previous one's output:
   Brainstormer → `brainstorm.md`, Planner → `plan.md`, Executor (TDD) → commits + `execution-log.md`, Reviewer → `review.md`, Vertical Checker → `verticals.md`.
3. Reviewer verdict: PASS advances, FIX re-dispatches the Executor, BLOCK stops and alerts.
4. Vertical Checker verdict: ALL CLEAR done, WARNINGS note and done, BLOCKED fix and re-run.
5. Completion: write `coordination-report.md`, update the manifest, clean up intermediates.

Brainstorm and Plan phases spawn sub-investigations — say it explicitly ("spawn subagents in the same turn to investigate X, Y, Z"), or Opus runs them sequentially.

Constraints every agent honors: `client_id` not `tenant_id` on leads/conversations; no `from __future__ import annotations` in `backend/routers/`; TDD order — test first, verify fail, implement, verify pass, commit.

Under 5 minutes of work, or a single-file fix? Skip the pipeline and just do it — it costs 3-5x a single-shot run.
