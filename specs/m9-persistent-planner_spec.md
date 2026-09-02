# Spec — M9 Persistent Planner / Workflow State Machine

**Status:** M9.1 contract  
**Date:** 2026-09-02  
**ADR:** `planning/decisions/2026-09-02-m9-persistent-planner-architecture.md`

## Goal

Durable multi-step workflows for owner goals, without giving the planner
independent tool authority.

## Non-negotiable

> The planner may decide what should happen next. It may never independently
> perform the action.

```text
Planner
  → Workflow step
  → existing Tool/Action contract
  → risk classification
  → approval gate
  → existing Action Executor
  → provider
  → independent verification
  → workflow state transition
```

## M9.1 deliverables (this slice)

| Artifact | Path |
|----------|------|
| Python contract | `backend/services/os_workflows/contract.py` |
| TS mirror | `agent-service/src/agent-os/workflows/types.ts` |
| Tests | `backend/tests/test_os_workflows_contract.py` |
| Schema sketch | `specs/m9-workflow-schema-sketch.sql` |
| ADR | `planning/decisions/2026-09-02-m9-persistent-planner-architecture.md` |

**Out of scope:** persistence engine, LLM planning, tool calls, migrations applied to live DB.

## Types

### Workflow

| Field | Notes |
|-------|-------|
| id | UUID string |
| tenantId | API name; DB column `client_id` |
| ownerGoal | Owner's natural-language goal |
| status | `planned \| running \| paused \| succeeded \| failed \| cancelled` |
| createdAt / updatedAt | UTC timestamps |

### WorkflowStep

| Field | Notes |
|-------|-------|
| id | UUID string |
| workflowId | Parent workflow |
| ordinal | Non-negative order hint (parallel steps may share ordinal bands) |
| description | Human-readable step text |
| dependencies | List of step ids that must succeed first |
| department | Optional hint |
| toolIntent | `{ toolName, arguments }` — intent only |
| state | See step states below |
| riskLevel | `0 \| 1 \| 2 \| 3` |
| executionId | Optional FK to `os_tool_executions.id` (M9.2+) |
| verificationState | Separate axis from step state |
| error | Optional error text |

### Step states

```text
planned | ready | pending_approval | running | verifying
succeeded | failed | unknown | blocked | cancelled
```

### Transition rules (allow-list)

See `ALLOWED_STEP_TRANSITIONS` / `ALLOWED_WORKFLOW_TRANSITIONS` in the
Python and TS contracts. Notable policies:

- L0/L1 may go `ready → running`.
- L2/L3 should go `ready → pending_approval → running`.
- `unknown → running|ready` is forbidden (no auto-replay of L2/L3 unknowns).
- `succeeded` / `cancelled` are terminal for steps.

## M9.2 (next)

- Apply schema sketch as numbered migration.
- Persist workflows/steps; dependency resolution; resume after restart;
  pause/resume on approval; terminal detection; bounded retry;
  unknown stays unknown.

## M9.3 (after M9.2)

Frozen planner eval (dependency graphs only — no execution) before LLM
plan generation.

## Acceptance (M9.1)

- [x] Pydantic models for Workflow / WorkflowStep / ToolIntent
- [x] Explicit transition helpers with tests
- [x] `assert_planner_cannot_execute` hard forbid
- [x] TS type mirror
- [x] Schema sketch (not applied)
- [x] ADR recorded
