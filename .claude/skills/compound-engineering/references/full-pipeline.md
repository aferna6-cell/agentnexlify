# Compound Engineering — Full Pipeline Reference

## The 5 Agents Detail

### Agent 1: Brainstormer
Goal: deeply understand the problem before anyone writes code.
Dispatch as: Agent (subagent_type: "architect") or Codex rescue for exploration.

Prompt template:
```
You are the BRAINSTORMER in a 5-agent compound engineering pipeline.

Your ONLY job: explore the problem space and document your findings. You do NOT plan implementation. You do NOT write code.

## Task
{task description}

## Your Deliverables
Write to: .claude/agent-comms/compound/{task-slug}/brainstorm.md

Include these sections:
1. Problem Statement
2. Constraints (from CLAUDE.md, schema, etc.)
3. Edge Cases
4. Dependencies
5. Prior Art
6. Approaches (2-3 options with trade-offs)
7. Recommendation
8. Open Questions

## Codebase Context
- Backend: FastAPI, routers in backend/routers/
- Frontend: React/Vite, pages in frontend/src/pages/
- Database: Supabase PostgreSQL with RLS
- Widget: Embeddable chat in widget/ + frontend/public/widget/
- ALWAYS use client_id (not tenant_id) for leads table
- NEVER use from __future__ import annotations in FastAPI files
```

Completion criteria: brainstorm.md exists with all 8 sections filled. No TBDs.

### Agent 2: Planner
Goal: turn the brainstorm into an exact, step-by-step implementation plan.

Reads: brainstorm.md

Prompt template:
```
You are the PLANNER in a 5-agent compound engineering pipeline.

Your ONLY job: create a precise implementation plan. You do NOT write production code.

## Brainstorm Output
{paste contents of brainstorm.md}

## Your Deliverables
Write to: .claude/agent-comms/compound/{task-slug}/plan.md

The plan MUST include:
1. Architecture Summary (2-3 sentences)
2. File Map (every file to create/modify with exact paths)
3. Tasks (numbered, ordered, TDD steps, exact code blocks)
4. Dependency Order
5. Risk Points

## Rules
- Every step must have actual code, not descriptions
- Every feature gets a test BEFORE implementation
- Commits after every passing test
- No task touches more than 3 files
- Use client_id for leads, status for lead status
- No from __future__ import annotations in backend/routers/
```

Completion criteria: plan.md exists with numbered tasks, exact file paths, actual code blocks. Zero placeholders.

### Agent 3: Executor
Goal: implement the plan exactly. Tests first.

Reads: plan.md

Prompt template:
```
You are the EXECUTOR in a 5-agent compound engineering pipeline.

Your ONLY job: implement the plan step-by-step. Follow it exactly. Do NOT deviate.

## Rules
1. Follow TDD: write test → verify it fails → implement → verify it passes
2. Commit after each task with descriptive message
3. If a step is unclear, write to executor-questions.md and STOP
4. Log every action to execution-log.md
5. Do NOT refactor code not in the plan
6. Do NOT add error handling not in the plan
```

Failure handling: if executor writes to executor-questions.md, STOP the pipeline. Read questions, answer them, re-dispatch.

### Agent 4: Reviewer
Reads: execution-log.md + git diff

Verdicts:
- PASS — no CRITICAL/HIGH; advance to Agent 5
- FIX — HIGH found; re-dispatch Executor with review.md fixes, then re-run Reviewer
- BLOCK — CRITICAL found; stop pipeline, alert user

See references for full reviewer prompt.

### Agent 5: Vertical Checker
Reads: all prior outputs + codebase state

Verticals checked: schema integrity, security surface, performance, widget sync, frontend build, integration, multi-tenant isolation.

Verdicts:
- ALL CLEAR — pipeline complete
- WARNINGS — complete; note for follow-up
- BLOCKED — route failures to Executor, re-run Vertical Checker

## Phase 7: Completion Report

Write coordination report to `.claude/agent-comms/compound/{task-slug}/coordination-report.md`:
```markdown
# Compound Pipeline Report: {task name}
## Completed: {timestamp}

## Pipeline Summary
| Agent | Status | Key Findings |
|-------|--------|-------------|
| Brainstormer | DONE | {1-line summary} |
| Planner | DONE | {N tasks planned} |
| Executor | DONE | {N commits, N tests} |
| Reviewer | PASS | {verdict summary} |
| Vertical Checker | {verdict} | {summary} |

## Files Changed
{list from execution-log.md}

## Commits
{list from execution-log.md}

## Lessons Learned
{anything surprising or worth remembering}
```

## Worktree Parallelism

Run 4-8 compound pipelines in parallel across git worktrees. See `.claude/skills/worktree-orchestrator/SKILL.md` for the full parallel execution workflow.

```bash
git worktree add .worktrees/task-auth -b compound/auth
git worktree add .worktrees/task-billing -b compound/billing
git worktree add .worktrees/task-widget -b compound/widget
git worktree add .worktrees/task-analytics -b compound/analytics
```

Each worktree = 1 Claude Code session = 1 compound pipeline. Sessions don't share state.

## Anti-Patterns

1. Do NOT skip agents.
2. Do NOT run agents in parallel — they are sequential by design.
3. Do NOT let the Executor deviate from the plan.
4. Do NOT ignore Reviewer BLOCK verdicts.
5. Do NOT skip the Vertical Checker.
6. Do NOT combine agents.

## Integration Map

| Existing Skill/Agent | Maps To |
|---------------------|---------|
| code-reviewer agent | Agent 4 |
| schema-guardian + qa-tester + security-reviewer | Agent 5 |
| worktree-orchestrator | Parallelism layer |
| coordinator | Replaced by this |
