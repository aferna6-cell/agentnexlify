# Coordinator — Decomposition Patterns Reference

## Phase 2: Agent Registry

| Task Type | Agent | Agent File | Tools | Notes |
|-----------|-------|------------|-------|-------|
| Schema validation, migration design | schema-guardian | `.claude/agents/schema-guardian.md` | Read-only | Always runs first if DB is touched. |
| API endpoints, backend logic, Pydantic models | backend-dev | `.claude/agents/backend-dev.md` | Read/Write/Edit/Bash | Reads schema-guardian output before starting |
| React pages, components, UI | frontend-dev | `.claude/agents/frontend-dev.md` | Read/Write/Edit/Bash | Needs API contract from backend-dev |
| Widget behavior, embedding, chat flow | widget-specialist | `.claude/agents/widget-specialist.md` | Read/Write/Edit/Bash | Must sync both widget file copies |
| Testing, validation, regression checks | qa-tester | `.claude/agents/qa-tester.md` | Read/Bash/Grep | Always runs last. Gate for completion. |
| Deploy prep, CI/CD, infra | devops | `.claude/agents/devops.md` | Read/Write/Edit/Bash | Runs parallel with qa-tester in deploy flows |

## Phase 4: Task Templates

### Template: New Feature (Full Stack)

```
Wave 1:
  1. [schema-guardian] Validate schema for new tables/columns
     Output: .claude/agent-comms/schema-guardian-output.md

Wave 2 (parallel):
  2. [backend-dev] Build API endpoints and Pydantic models
     Blocked by: 1
  3. [frontend-dev] Build dashboard page/component
     Blocked by: 1 OR 2

Wave 3:
  4. [qa-tester] Validate end-to-end
     Blocked by: 2, 3
```

### Template: Bug Fix

```
Wave 1:
  1. [coordinator] Diagnose the bug — read bug-patterns.md, trace request path

Wave 2:
  2. [responsible-agent] Implement the fix
     Blocked by: 1

Wave 3:
  3. [qa-tester] Verify fix, check for regressions
     Blocked by: 2
```

### Template: Refactor

```
Wave 1:
  1. [coordinator] Analyze scope — which files, what pattern, what risk

Wave 2 (batched, max 10 files per batch):
  2. [backend-dev] Refactor backend files (batch 1)
  3. [frontend-dev] Refactor frontend files (batch 1)

Wave N (final):
  N. [qa-tester] Full validation — build check, import scan, regression check
```

### Template: Deploy

```
Wave 1 (parallel):
  1. [qa-tester] Full pre-deploy validation
  2. [devops] Deploy checklist and environment verification

Wave 2:
  3. [coordinator] Compile results, identify blockers
     If blockers: route fixes, re-run wave 1.
     If clear: declare deploy-ready.
```

### Template: Widget Change

```
Wave 1:
  1. [widget-specialist] Implement the widget change (both copies)

Wave 2 (parallel):
  2. [schema-guardian] Validate if data flow changed (if widget touches DB)
  3. [qa-tester] Widget testing checklist (CORS, session, file sync)
```

### Template: Database Migration

```
Wave 1:
  1. [schema-guardian] Audit current schema, design migration SQL

Wave 2:
  2. [backend-dev] Update Pydantic models, queries, router logic
     Blocked by: 1

Wave 3 (parallel):
  3. [frontend-dev] Update affected UI (if data shape changed)
  4. [widget-specialist] Update widget if it uses affected data

Wave 4:
  5. [qa-tester] Validate entire data path end-to-end
```

## Worked Example: Invoice PDF

### Step 1: Analyze
Touches DB (schema-guardian), backend (2 endpoints), frontend (buttons), QA.

### Step 2: DAG
```
1. [schema-guardian] Verify invoices table schema — no blockers
2. [backend-dev] POST /invoices/{id}/pdf — blocked by 1
3. [backend-dev] POST /invoices/{id}/send-email — blocked by 1
4. [frontend-dev] Add buttons to InvoicesPage — blocked by 2
5. [qa-tester] End-to-end validation — blocked by 2, 3, 4
```

### Step 3: Execute waves
Wave 1: dispatch schema-guardian.
Wave 2: read schema-guardian output, dispatch backend-dev (2 tasks in parallel).
Wave 3: read backend-dev output, dispatch frontend-dev.
Wave 4: dispatch qa-tester.

## Phase 5: Coordination Report

File: `.claude/agent-comms/coordination-{timestamp}.md`

```markdown
# Coordination Report: {task name}
## Completed: {timestamp}

## Summary
{2-3 sentences}

## Agents Used
| Agent | Task | Status | Duration |
|-------|------|--------|----------|

## Files Changed
{list}

## Migrations
{any new migration files — flag for manual application}

## Issues Encountered
{problems hit and how resolved}

## QA Result
{qa-tester final verdict}
```

## Communication Protocol

Every agent dispatch MUST include:
1. Clear task description
2. Context from prior agents (paste relevant sections)
3. File paths (where to find existing code, where to write new code)
4. Output path (`.claude/agent-comms/{agent-name}-output.md`)
5. Constraints from CLAUDE.md

After task complete: keep coordination report, delete individual agent output files.

## Anti-Patterns

1. Do not dispatch all agents at once. Respect the DAG.
2. Do not skip schema-guardian. If task touches any DB table, schema-guardian goes first.
3. Do not skip qa-tester. Every coordinated task ends with QA.
4. Do not send vague prompts. Include table names, column names, endpoint paths, response shapes.
5. Do not ignore agent failures. Stop and fix before continuing.
6. Do not exceed 4 parallel agents.
7. Do not re-invent delegation prompts — use agent's standard format from their .md file.
