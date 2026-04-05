---
name: coordinator
description: Multi-agent orchestrator. Auto-decomposes complex tasks into parallel workstreams with dependency resolution. Use when user says "coordinate this", "orchestrate", or gives a complex multi-part task. Also activates for /new-feature and /refactor commands.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, TaskCreate, TaskUpdate, TaskList
---

# Coordinator Mode

Multi-agent orchestrator that auto-decomposes complex tasks into a dependency DAG and dispatches them to specialized agents in parallel.

## When to Activate

- User says "coordinate this", "orchestrate", or similar
- `/new-feature` command (full-stack feature build)
- `/refactor` command (multi-file restructuring)
- Any task that touches 3+ domains (schema, backend, frontend, widget, infra)
- Any task where ordering matters (schema before backend, backend before frontend)

## When NOT to Activate

- Single-file edits with no cross-cutting concerns
- Simple questions about the codebase
- Tasks clearly within one domain (just delegate directly to that agent)
- The user explicitly says to do it directly

---

## Phase 1: Task Decomposition Protocol

When given a complex task, follow this sequence exactly:

### 1.1 Analyze the Task

Read the task description and identify:
- **What database tables are touched?** (If any, schema-guardian goes first)
- **What backend endpoints are needed?** (backend-dev)
- **What UI pages/components are needed?** (frontend-dev)
- **Does the widget change?** (widget-specialist)
- **Is there infra/deploy work?** (devops)
- **What needs to be validated?** (qa-tester, always last)

### 1.2 Build the Dependency DAG

For each workstream, determine:
- **Can it start immediately?** (no dependencies) -- these are root nodes
- **What must complete before it can start?** (blockedBy relationships)
- **Can it run in parallel with other tasks?** (same depth in DAG)

Write the DAG as a numbered list with explicit blockers:

```
1. [schema-guardian] Validate/create schema -- no blockers
2. [backend-dev] Build API endpoints -- blocked by 1
3. [frontend-dev] Build UI components -- blocked by 2 (needs API contract)
4. [backend-dev] Build background service -- blocked by 1
5. [qa-tester] Validate everything -- blocked by 2, 3, 4
```

### 1.3 Create the Coordination Plan

Write the plan to `.claude/agent-comms/coordination-plan.md` before dispatching anything:

```markdown
# Coordination Plan: {task name}
## Created: {timestamp}

## Task Summary
{one-paragraph description}

## DAG
{numbered list with blockers}

## Execution Waves
Wave 1 (parallel): tasks 1
Wave 2 (parallel): tasks 2, 4 (after wave 1 completes)
Wave 3 (parallel): tasks 3 (after task 2 completes)
Wave 4 (parallel): tasks 5 (after wave 2+3 complete)

## Status
- [ ] Task 1: pending
- [ ] Task 2: pending
...
```

---

## Phase 2: Agent Registry

Map task types to the correct agent. These reference the existing agent definitions in `.claude/agents/`.

| Task Type | Agent | Agent File | Tools | Notes |
|-----------|-------|------------|-------|-------|
| Schema validation, migration design | schema-guardian | `.claude/agents/schema-guardian.md` | Read-only | Always runs first if DB is touched. Output: PASS/FAIL/WARNING |
| API endpoints, backend logic, Pydantic models | backend-dev | `.claude/agents/backend-dev.md` | Read/Write/Edit/Bash | Reads schema-guardian output before starting |
| React pages, components, UI | frontend-dev | `.claude/agents/frontend-dev.md` | Read/Write/Edit/Bash | Needs API contract from backend-dev |
| Widget behavior, embedding, chat flow | widget-specialist | `.claude/agents/widget-specialist.md` | Read/Write/Edit/Bash | Must sync both widget file copies |
| Testing, validation, regression checks | qa-tester | `.claude/agents/qa-tester.md` | Read/Bash/Grep | Always runs last. Gate for completion |
| Deploy prep, CI/CD, infra | devops | `.claude/agents/devops.md` | Read/Write/Edit/Bash | Runs parallel with qa-tester in deploy flows |
| General research, exploration | (self -- coordinator) | N/A | Read/Grep/Glob | Don't delegate; do it inline |

### Agent Dispatch Rules

- **Always include full context** in the delegation prompt: file paths, error messages, prior agent output, specific instructions, and the output file path.
- **Always tell the agent where to write output**: `.claude/agent-comms/{agent-name}-output.md`
- **Always read prior agent output** before dispatching a dependent agent. Pass relevant sections into the next agent's prompt.
- **Conflict resolution**: schema-guardian wins on schema questions; `docs/dev-knowledge/architecture-decisions.md` wins on architecture questions.

---

## Phase 3: DAG Execution Rules

### Parallel Execution

- Dispatch all tasks in the same wave simultaneously using the Agent tool.
- **Maximum 4 parallel agents at once.** If a wave has more than 4 tasks, split into sub-waves.
- Independent tasks at the same DAG depth run in parallel.
- Tasks with unmet dependencies wait -- never dispatch a task whose blockers have not completed.

### Failure Handling

- If an agent returns FAIL status or reports critical issues:
  1. **Pause all dependents** of the failed task.
  2. **Read the failure output** carefully.
  3. **Diagnose**: Is this a fixable issue? Can the coordinator fix it directly?
  4. **Re-dispatch** the agent with corrected instructions, or fix the issue directly and mark complete.
  5. **Resume dependents** once the blocker is resolved.
- Never cascade failures blindly. One agent failing does not mean the whole plan fails.

### Progress Tracking

After each wave completes:
1. Read all agent output files from `.claude/agent-comms/`.
2. Update the coordination plan status (mark tasks complete/failed).
3. Check if the next wave's blockers are all met.
4. Dispatch the next wave.

### Completion Gate

After all waves complete:
1. **Always run qa-tester** on the combined result, even if individual agents reported success.
2. If qa-tester finds issues, route fixes back to the responsible agent.
3. Only declare the task complete when qa-tester returns PASS or WARNINGS-only.

---

## Phase 4: Task Templates

Pre-built DAG patterns for common multi-task scenarios. Use these as starting points -- adjust based on the specific task.

### Template: New Feature (Full Stack)

```
Wave 1:
  1. [schema-guardian] Validate schema for new tables/columns
     Output: .claude/agent-comms/schema-guardian-output.md

Wave 2 (parallel):
  2. [backend-dev] Build API endpoints and Pydantic models
     Blocked by: 1
     Input: schema-guardian output
     Output: .claude/agent-comms/backend-dev-output.md

  3. [frontend-dev] Build dashboard page/component
     Blocked by: 1 (if no new endpoints needed) OR 2 (if needs API contract)
     Input: API contract from backend-dev (endpoint paths, request/response shapes)
     Output: .claude/agent-comms/frontend-dev-output.md

Wave 3:
  4. [qa-tester] Validate end-to-end
     Blocked by: 2, 3
     Input: all agent outputs
     Output: .claude/agent-comms/qa-tester-output.md
```

### Template: Bug Fix

```
Wave 1:
  1. [coordinator] Diagnose the bug
     Read bug-patterns.md, trace the request path, identify root cause and responsible domain.

Wave 2:
  2. [responsible-agent] Implement the fix
     Blocked by: 1
     Input: diagnosis with file paths, line numbers, expected vs actual behavior

Wave 3:
  3. [qa-tester] Verify fix, check for regressions
     Blocked by: 2
     Input: fix description, files changed, known regression patterns
```

### Template: Refactor

```
Wave 1:
  1. [coordinator] Analyze scope -- which files, what pattern, what risk
     Read the codebase, identify all instances, plan the change.

Wave 2 (batched, max 10 files per batch):
  2. [backend-dev] Refactor backend files (batch 1)
     Blocked by: 1
  3. [frontend-dev] Refactor frontend files (batch 1)
     Blocked by: 1

Wave 3 (if more batches):
  4. [backend-dev] Refactor backend files (batch 2)
     Blocked by: 2
  5. [frontend-dev] Refactor frontend files (batch 2)
     Blocked by: 3

Wave N (final):
  N. [qa-tester] Full validation -- build check, import scan, regression check
     Blocked by: all previous waves
```

### Template: Deploy

```
Wave 1 (parallel):
  1. [qa-tester] Full pre-deploy validation
     Output: .claude/agent-comms/qa-tester-output.md
  2. [devops] Deploy checklist and environment verification
     Output: .claude/agent-comms/devops-output.md

Wave 2:
  3. [coordinator] Compile results, identify blockers
     Blocked by: 1, 2
     If blockers found: route fixes to responsible agents, then re-run wave 1.
     If clear: declare deploy-ready.
```

### Template: Widget Change

```
Wave 1:
  1. [widget-specialist] Implement the widget change (both copies)
     Output: .claude/agent-comms/widget-specialist-output.md

Wave 2 (parallel):
  2. [schema-guardian] Validate if data flow changed
     Blocked by: 1 (only if widget touches DB)
  3. [qa-tester] Widget testing checklist (CORS, session, file sync)
     Blocked by: 1
```

### Template: Database Migration

```
Wave 1:
  1. [schema-guardian] Audit current schema, design migration SQL, check for conflicts
     Output: .claude/agent-comms/schema-guardian-output.md

Wave 2:
  2. [backend-dev] Update Pydantic models, queries, and router logic
     Blocked by: 1
     Input: migration SQL, new column names, type info from schema-guardian

Wave 3 (parallel):
  3. [frontend-dev] Update any affected UI (if data shape changed)
     Blocked by: 2
  4. [widget-specialist] Update widget if it uses affected data
     Blocked by: 2

Wave 4:
  5. [qa-tester] Validate entire data path end-to-end
     Blocked by: 2, 3, 4
```

---

## Phase 5: Coordination Report

After the entire task completes (qa-tester passes), write a coordination report:

**File**: `.claude/agent-comms/coordination-{timestamp}.md`

```markdown
# Coordination Report: {task name}
## Completed: {timestamp}

## Summary
{What was accomplished in 2-3 sentences}

## Agents Used
| Agent | Task | Status | Duration |
|-------|------|--------|----------|
| schema-guardian | Validate invoices schema | PASS | wave 1 |
| backend-dev | Build PDF endpoint | PASS | wave 2 |
| ...

## Files Changed
{List all files created or modified across all agents}

## Migrations
{Any new migration files -- flag for manual application}

## Issues Encountered
{Problems hit during execution and how they were resolved}

## QA Result
{qa-tester final verdict}

## Follow-up Items
{Anything that needs attention later}
```

---

## Worked Example: "Add invoice PDF generation with email delivery"

Here is a complete decomposition of a real-world task.

### Step 1: Analyze

The task touches:
- **Database**: Need to check if `invoices` table has all required columns (schema-guardian)
- **Backend**: PDF generation endpoint + email delivery service (backend-dev, 2 tasks)
- **Frontend**: PDF download button + preview modal (frontend-dev)
- **QA**: End-to-end validation (qa-tester)

### Step 2: Build DAG

```
1. [schema-guardian] Verify invoices table schema has template_html, rendered_html or equivalent
   Blockers: none

2. [backend-dev] POST /invoices/{id}/pdf -- generate PDF from invoice data
   Blockers: 1

3. [backend-dev] POST /invoices/{id}/send-email -- email invoice PDF to customer
   Blockers: 1

4. [frontend-dev] Add "Download PDF" button and "Email Invoice" button to InvoicesPage
   Blockers: 2 (needs the endpoint path and response format)

5. [qa-tester] End-to-end validation
   Blockers: 2, 3, 4
```

### Step 3: Execute

**Wave 1** -- Dispatch schema-guardian:
```
Prompt: "Check the invoices table schema. Verify these columns exist:
items_json, subtotal, tax, total, status, lead_id, tenant_id.
Check if there's a column for rendered HTML or if we need a migration.
Write output to .claude/agent-comms/schema-guardian-output.md"
```

**Wave 2** -- Read schema-guardian output. If PASS, dispatch backend-dev (2 tasks in parallel):
```
Task A prompt: "Build POST /api/v1/invoices/{tenant_id}/{invoice_id}/pdf endpoint.
Schema-guardian confirmed these columns: [paste relevant output].
Generate styled HTML from invoice data, return with content-disposition: attachment.
Follow the HTML invoice pattern from architecture-decisions.md (no weasyprint).
Write output to .claude/agent-comms/backend-dev-output.md"

Task B prompt: "Build POST /api/v1/invoices/{tenant_id}/{invoice_id}/send-email endpoint.
Use the existing send_email service (Resend). Attach the generated PDF HTML.
Include tenant business name in the email subject.
Write output to .claude/agent-comms/backend-dev-email-output.md"
```

**Wave 3** -- Read backend-dev output. Dispatch frontend-dev:
```
Prompt: "Add 'Download PDF' and 'Email Invoice' buttons to the InvoicesPage.
Backend endpoints: [paste paths and response shapes from backend-dev output].
Match existing dark theme. Show loading state while PDF generates.
Write output to .claude/agent-comms/frontend-dev-output.md"
```

**Wave 4** -- Dispatch qa-tester:
```
Prompt: "Validate the invoice PDF and email features.
Changes made by: [paste summary of all agent outputs].
Check: router registration, Pydantic models match schema, no dangerous imports,
frontend build succeeds, error handling present.
Write output to .claude/agent-comms/qa-tester-output.md"
```

### Step 4: Completion

Read qa-tester output. If PASS, write coordination report. If FAIL, route fixes back to responsible agent and re-run qa-tester.

---

## Communication Protocol

### Input to Agents

Every agent dispatch MUST include:
1. **Clear task description** -- what to build/check/fix
2. **Context from prior agents** -- paste relevant sections from their output files
3. **File paths** -- where to find existing code, where to write new code
4. **Output path** -- where the agent should write its results
5. **Constraints** -- any rules from CLAUDE.md or architecture-decisions.md that apply

### Output from Agents

Each agent writes to `.claude/agent-comms/{agent-name}-output.md` in their standard format (defined in their agent file). The coordinator reads these to:
- Extract information for dependent agents
- Track pass/fail status
- Compile the final coordination report

### Cleanup

After the task is fully complete and the coordination report is written:
- Keep the coordination report (it serves as a record)
- Delete individual agent output files (they are ephemeral)
- Keep README.md in agent-comms/

---

## Anti-Patterns (Do NOT Do These)

1. **Do not dispatch all agents at once.** Respect the DAG. Schema must validate before backend builds. Backend must define the API before frontend consumes it.

2. **Do not skip schema-guardian.** If the task touches any database table, schema-guardian goes first. The most common bugs in this codebase are schema mismatches.

3. **Do not skip qa-tester.** Every coordinated task ends with QA. No exceptions.

4. **Do not send vague prompts to agents.** "Build the backend" is not enough. Include table names, column names, endpoint paths, request/response shapes, and which files to read/modify.

5. **Do not ignore agent failures.** If an agent reports a problem, stop and fix it before continuing. Cascading on top of a broken foundation wastes everyone's context.

6. **Do not exceed 4 parallel agents.** Each agent uses a separate context window. More than 4 in parallel risks degraded quality and exceeds practical coordination overhead.

7. **Do not re-invent the delegation prompt.** Each agent has a standard format defined in `.claude/agents/{name}.md`. Match it. They know their own workflow -- just give them the task-specific context.
