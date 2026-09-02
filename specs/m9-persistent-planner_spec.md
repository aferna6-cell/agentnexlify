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
| Python tests | `backend/tests/test_os_workflows_contract.py` |
| TS tests | `agent-service/src/agent-os/workflows/types.test.ts` |
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

### Transition rules (allow-list + risk gates)

See `ALLOWED_STEP_TRANSITIONS` / `ALLOWED_WORKFLOW_TRANSITIONS` plus
risk-aware gates in the Python and TS contracts. Notable policies:

- L0/L1 may go `ready → running`.
- L2/L3 **must** go `ready → pending_approval → running`;
  `ready → running` is rejected.
- Step terminal = `succeeded | cancelled`. `failed` is retryable
  (`failed → planned|ready|cancelled`) under M9.2 bounded-retry policy.
- Workflow `failed` is genuinely terminal (no outbound edges).
- L0/L1 `unknown`: controlled recovery to `planned|ready|blocked|cancelled`.
- L2/L3 `unknown`: `cancelled` only — no automatic replay.
- Missing risk on gated edges fails closed (treated as L3).

## M9.2 (next)

- Apply schema sketch as numbered migration.
- Persist workflows/steps; dependency resolution; resume after restart;
  pause/resume on approval; terminal detection; bounded retry;
  L2/L3 unknown stays non-replayable.
- CI invariant: planner/workflow modules must not import Action Executor
  / provider implementations directly.

## M9.3 (after M9.2)

Frozen planner eval (dependency graphs only — no execution) before LLM
plan generation.

## Acceptance (M9.1)

- [x] Pydantic models for Workflow / WorkflowStep / ToolIntent
- [x] Explicit risk-aware transition helpers with Python + TS tests
- [x] `assert_planner_cannot_execute` / `assertPlannerCannotExecute` sentinel
- [x] TS type + transition mirror
- [x] Schema sketch (not applied)
- [x] ADR recorded
