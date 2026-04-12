---
name: compound-engineering
description: 5-agent compound pipeline for every task. Brainstorm → Plan → Execute → Review → Vertical Check. Each agent focused on one thing. Everything documented in markdown. Combined with worktree parallelism for 4-8x throughput. Use when user says 'compound this', 'full pipeline', '5-agent', 'compound pipeline', 'compound engineering', '/compound', or asks about compound engineering.
version: 1.0.0
origin: claude
user_invocable: true
allowed_tools:
- Read
- Write
- Edit
- Bash
- Glob
- Grep
- Agent
- TaskCreate
- TaskUpdate
- TaskList
triggers:
- /compound
- compound this
- full pipeline
- 5-agent
- compound pipeline
- compound engineering
effort: high
---

# Compound Engineering Pipeline

A 5-agent sequential pipeline that runs on every non-trivial task. Each agent is focused on exactly one job. The output quality is higher because no single agent is trying to think about everything at once.

Inspired by compound AI systems — the same principle that makes mixture-of-experts models powerful. One brainstorms, one plans, one executes, one reviews, one checks verticals. Slow and deliberate. But the output is production-grade.

## When to Activate

- Any feature, bug fix, refactor, or optimization task
- `/compound` command
- User says "compound this", "full pipeline", "5-agent"
- Any task touching 2+ files or domains

## When NOT to Activate

- Single-line fixes with obvious solutions
- Documentation-only changes
- Simple config changes
- User explicitly says "just do it" or "skip the pipeline"

---

## The 5 Agents

| # | Agent | Role | Focus | Output |
|---|-------|------|-------|--------|
| 1 | **Brainstormer** | Problem Explorer | What are we solving? Edge cases? Constraints? Prior art? | `brainstorm.md` |
| 2 | **Planner** | Technical Architect | Exact files, exact steps, exact dependencies, TDD | `plan.md` |
| 3 | **Executor** | Code Writer | Implements the plan step-by-step, tests first | commits + `execution-log.md` |
| 4 | **Reviewer** | Quality Gate | Code review: security, correctness, patterns, regressions | `review.md` |
| 5 | **Vertical Checker** | Cross-Cutting Auditor | Schema, security, perf, RLS, widget sync, accessibility | `verticals.md` |

Each agent writes its output to `.claude/agent-comms/compound/{task-slug}/`. The next agent reads the previous agent's output before starting.

---

## Pipeline Flow

```
Task In
  │
  ▼
┌─────────────────────────────────────┐
│  AGENT 1: BRAINSTORMER              │
│  • Explores problem space           │
│  • Identifies edge cases            │
│  • Maps constraints & dependencies  │
│  • Proposes 2-3 approaches          │
│  → writes brainstorm.md             │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  AGENT 2: PLANNER                   │
│  • Reads brainstorm.md              │
│  • Designs exact implementation     │
│  • File paths, line numbers, code   │
│  • TDD steps, commit points         │
│  → writes plan.md                   │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  AGENT 3: EXECUTOR                  │
│  • Reads plan.md                    │
│  • Implements step-by-step          │
│  • Tests first (TDD)               │
│  • Commits at each milestone        │
│  → writes execution-log.md          │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  AGENT 4: REVIEWER                  │
│  • Reads execution-log.md + diffs   │
│  • Code quality audit               │
│  • Security check                   │
│  • Pattern compliance               │
│  → writes review.md                 │
│  → BLOCK if CRITICAL issues         │
└─────────────┬───────────────────────┘
              │ (pass/fix loop)
              ▼
┌─────────────────────────────────────┐
│  AGENT 5: VERTICAL CHECKER          │
│  • Reads all prior outputs          │
│  • Schema integrity check           │
│  • RLS/tenant isolation audit       │
│  • Performance regression scan      │
│  • Widget file sync check           │
│  • Frontend build verification      │
│  • Security surface audit           │
│  → writes verticals.md              │
│  → BLOCK if any vertical fails      │
└─────────────┬───────────────────────┘
              │
              ▼
         TASK COMPLETE
    (coordination-report.md)
```

---

## Phase 1: Setup

Before running the pipeline:

1. **Create the task directory:**
   ```bash
   mkdir -p .claude/agent-comms/compound/{task-slug}
   ```

2. **Create the task manifest** at `.claude/agent-comms/compound/{task-slug}/manifest.md`:
   ```markdown
   # Compound Pipeline: {task name}
   ## Started: {timestamp}
   ## Task: {description}
   
   ## Status
   - [ ] Agent 1: Brainstormer — pending
   - [ ] Agent 2: Planner — pending
   - [ ] Agent 3: Executor — pending
   - [ ] Agent 4: Reviewer — pending
   - [ ] Agent 5: Vertical Checker — pending
   
   ## Blockers
   (none yet)
   ```

---

## Phase 2: Agent 1 — Brainstormer

**Goal:** Deeply understand the problem before anyone writes code.

**Dispatch as:** Agent (subagent_type: "architect") or Codex rescue for exploration.

**Prompt template:**
```
You are the BRAINSTORMER in a 5-agent compound engineering pipeline.

Your ONLY job: explore the problem space and document your findings. You do NOT plan implementation. You do NOT write code.

## Task
{task description}

## Your Deliverables
Write to: .claude/agent-comms/compound/{task-slug}/brainstorm.md

Include these sections:
1. **Problem Statement** — What are we actually solving? (1-2 paragraphs)
2. **Constraints** — What rules must we follow? (from CLAUDE.md, schema, etc.)
3. **Edge Cases** — What could go wrong? What's the weird input?
4. **Dependencies** — What existing code/tables/APIs does this touch?
5. **Prior Art** — Is there similar code in the codebase we can learn from?
6. **Approaches** — 2-3 different ways to solve this, with trade-offs
7. **Recommendation** — Which approach and why
8. **Open Questions** — Anything unclear that the Planner needs to resolve

## Codebase Context
- Backend: FastAPI, 62 routers in backend/routers/
- Frontend: React/Vite, 67 pages in frontend/src/pages/
- Database: Supabase PostgreSQL with RLS
- Widget: Embeddable chat in widget/ + frontend/public/widget/
- ALWAYS use client_id (not tenant_id) for leads table
- NEVER use from __future__ import annotations in FastAPI files
```

**Completion criteria:** `brainstorm.md` exists with all 8 sections filled. No TBDs.

**Update manifest:** Mark Agent 1 complete, proceed to Agent 2.

---

## Phase 3: Agent 2 — Planner

**Goal:** Turn the brainstorm into an exact, step-by-step implementation plan.

**Dispatch as:** Agent (subagent_type: "architect") — needs broad codebase understanding.

**Reads:** `brainstorm.md`

**Prompt template:**
```
You are the PLANNER in a 5-agent compound engineering pipeline.

Your ONLY job: create a precise implementation plan. You do NOT write production code. You do NOT review code.

## Brainstorm Output
{paste contents of brainstorm.md}

## Your Deliverables
Write to: .claude/agent-comms/compound/{task-slug}/plan.md

The plan MUST include:
1. **Architecture Summary** — 2-3 sentences on the approach (from brainstorm recommendation)
2. **File Map** — Every file to create/modify with exact paths
3. **Tasks** — Numbered, ordered tasks. Each task has:
   - Files touched (create/modify with line ranges)
   - Test file path
   - TDD steps: write failing test → verify fail → implement → verify pass → commit
   - Exact code blocks (no placeholders, no "implement X here")
   - Expected test output
4. **Dependency Order** — Which tasks must complete before others
5. **Risk Points** — Where things are most likely to break

## Rules
- Every step must have actual code, not descriptions of code
- Every feature gets a test BEFORE implementation
- Commits after every passing test
- No task touches more than 3 files
- Use client_id for leads, status for lead status
- No from __future__ import annotations in backend/routers/
```

**Completion criteria:** `plan.md` exists with numbered tasks, exact file paths, actual code blocks. Zero placeholders.

**Update manifest:** Mark Agent 2 complete, proceed to Agent 3.

---

## Phase 4: Agent 3 — Executor

**Goal:** Implement the plan exactly. Tests first.

**Dispatch as:** Agent (subagent_type: "general-purpose") with write access, or Codex rescue with `--write`.

**Reads:** `plan.md`

**Prompt template:**
```
You are the EXECUTOR in a 5-agent compound engineering pipeline.

Your ONLY job: implement the plan step-by-step. Follow it exactly. Do NOT deviate. Do NOT add features not in the plan. Do NOT skip tests.

## Implementation Plan
{paste contents of plan.md}

## Rules
1. Follow TDD: write test → verify it fails → implement → verify it passes
2. Commit after each task with descriptive message
3. If a step is unclear, write to .claude/agent-comms/compound/{task-slug}/executor-questions.md and STOP
4. Log every action to .claude/agent-comms/compound/{task-slug}/execution-log.md:
   - Task N started
   - Test written: {file}
   - Test result: FAIL (expected)
   - Implementation written: {file}
   - Test result: PASS
   - Committed: {sha} "{message}"
5. Do NOT refactor code not in the plan
6. Do NOT add error handling not in the plan
7. Do NOT add comments not in the plan

## Completion
When all tasks are done, write final status to execution-log.md:
- Total tasks completed
- Total tests written
- Total commits
- Any deviations from plan (should be zero)
- Files changed list
```

**Completion criteria:** All tasks in plan.md implemented. execution-log.md has complete audit trail. All tests pass.

**Failure handling:** If executor writes to `executor-questions.md`, STOP the pipeline. Read questions, answer them, re-dispatch executor with answers.

**Update manifest:** Mark Agent 3 complete, proceed to Agent 4.

---


## Phase 5: Agent 4 — Reviewer

**Goal:** Code quality gate. Catch bugs, security issues, pattern violations.

**Dispatch as:** Agent (subagent_type: "code-reviewer") — read-only, focused.

**Reads:** `execution-log.md` + git diff

**Prompt template:** see `references/agent-prompts.md` § Reviewer.

**Verdicts:**
- **PASS** — no CRITICAL/HIGH; advance to Agent 5
- **FIX** — HIGH found; re-dispatch Executor with review.md fixes, then re-run Reviewer
- **BLOCK** — CRITICAL found; stop pipeline, alert user

---

## Phase 6: Agent 5 — Vertical Checker

**Goal:** Cross-cutting audit across domains no single reviewer catches.

**Dispatch as:** Agent (subagent_type: "vertical-checker") — custom agent.

**Reads:** all prior outputs + codebase state

**Prompt template:** see `references/agent-prompts.md` § Vertical Checker.

**Verticals checked:** schema integrity, security surface, performance, widget sync, frontend build, integration, multi-tenant isolation.

**Verdicts:**
- **ALL CLEAR** — pipeline complete
- **WARNINGS** — complete; note for follow-up
- **BLOCKED** — route failures to Executor, re-run Vertical Checker

---

---

## Phase 7: Completion

After all 5 agents pass:

1. **Write coordination report** to `.claude/agent-comms/compound/{task-slug}/coordination-report.md`:
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
   
   ## Tests Added
   {list from execution-log.md}
   
   ## Commits
   {list from execution-log.md}
   
   ## Time in Pipeline
   {total duration}
   
   ## Lessons Learned
   {anything surprising or worth remembering}
   ```

2. **Update manifest** — all 5 agents marked complete.

3. **Clean up** — keep coordination-report.md, archive or delete intermediate files.

---

## Worktree Parallelism

The REAL multiplier. Run 4-8 compound pipelines in parallel across git worktrees.

See: `.claude/skills/worktree-orchestrator/SKILL.md` for the full parallel execution workflow.

**Quick version:**
```bash
# Create worktrees for parallel tasks
git worktree add .worktrees/task-auth -b compound/auth
git worktree add .worktrees/task-billing -b compound/billing
git worktree add .worktrees/task-widget -b compound/widget
git worktree add .worktrees/task-analytics -b compound/analytics

# Each worktree runs its own Claude Code session
# Each session runs the full 5-agent pipeline independently
# No conflicts because each worktree is isolated
```

**Managing parallel sessions:**
- Each worktree = 1 Claude Code session = 1 compound pipeline
- Sessions don't share state (that's the point)
- Merge worktrees back to main when pipelines complete
- The skill is managing the queue and resolving merge conflicts

---

## Anti-Patterns

1. **Do NOT skip agents.** The whole point is that each agent catches what others miss. "Just execute it" defeats the purpose.

2. **Do NOT run agents in parallel.** They are sequential by design — each reads the previous agent's output. Brainstorm before you plan. Plan before you execute. Execute before you review.

3. **Do NOT let the Executor deviate from the plan.** If the plan is wrong, stop and re-run the Planner. Don't improvise during execution.

4. **Do NOT ignore Reviewer BLOCK verdicts.** CRITICAL issues mean the code is dangerous. Fix before proceeding.

5. **Do NOT skip the Vertical Checker.** It catches the cross-cutting bugs that domain-specific agents miss. Schema mismatches, RLS gaps, widget desyncs — these are the bugs that hit production.

6. **Do NOT combine agents.** "I'll brainstorm and plan at the same time" produces shallow brainstorms and vague plans. Separation is the feature.

---

## Integration with Existing Skills

| Existing Skill/Agent | Maps To | How |
|---------------------|---------|-----|
| superpowers:brainstorming | Agent 1 concepts | Brainstormer uses same exploration patterns |
| superpowers:writing-plans | Agent 2 output | Planner produces same plan format |
| superpowers:subagent-driven-development | Agent 3 pattern | Executor follows same TDD dispatch |
| code-reviewer agent | Agent 4 | Reviewer uses same checklist |
| schema-guardian + qa-tester + security-reviewer | Agent 5 | Vertical Checker combines all three |
| superpowers:using-git-worktrees | Parallelism layer | Worktree orchestrator wraps this |
| coordinator | Replaced by this | Compound pipeline is the new coordinator |

---

## Quick Start

```
User: "Add invoice PDF generation"

Coordinator:
  1. mkdir .claude/agent-comms/compound/invoice-pdf
  2. Dispatch Brainstormer → brainstorm.md
  3. Read brainstorm.md → Dispatch Planner → plan.md
  4. Read plan.md → Dispatch Executor → commits + execution-log.md
  5. Read execution-log.md → Dispatch Reviewer → review.md (PASS)
  6. Read all → Dispatch Vertical Checker → verticals.md (ALL CLEAR)
  7. Write coordination-report.md
  8. "Done. 4 commits, 6 tests, all verticals clear."
```

For parallel tasks:
```
User: "Add invoice PDF, fix widget bug, and update analytics"

Coordinator:
  1. Create 3 worktrees
  2. Each runs compound pipeline independently
  3. Merge back when all complete
  4. Resolve any conflicts
  5. Final vertical check on merged result
```

## Gotchas

- **5 agents is heavy for small tasks.** Under 5 minutes of work, skip compound — just do it. Compound pays off on 30+ min tasks with unknowns.
- **Brainstormer output can be too broad.** Planner has to narrow it. If you skip Brainstormer on a well-scoped task, start with Planner directly.
- **Executor hitting test failures is normal** — the Reviewer gate catches them. Do not loop Executor on failing tests; pass to Reviewer.
- **Reviewer without diff context hallucinates issues.** Always feed the actual git diff, not a summary.
- **Vertical Checker is the only agent that touches prod concerns** (schema, RLS, widget sync). Do not skip even if the other 4 all pass.
- **Worktree merges can conflict.** When parallel worktrees touch the same file, merge conflicts surface at the merge step — not the compound step. Run `git worktree list` before declaring done.
- **Token cost.** Each compound run is ~3-5x the token cost of a single-shot execution. Justify with complexity, not habit.
