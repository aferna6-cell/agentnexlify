# Spec — M9 Persistent Planner / Workflow State Machine

**Status:** M9.2 COMPLETE · M9.3 frozen eval
**Date:** 2026-09-03
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

## M9.2 ✅

- Applied schema as migrations `199_os_workflows.sql` + `200_os_workflows_integrity.sql`.
- Persist workflows/steps; dependency resolution; resume after restart;
  pause/resume on approval; terminal detection; bounded retry;
  L2/L3 unknown stays non-replayable; execution≠verification.
- CI invariant: planner/workflow modules must not import Action Executor
  / provider implementations directly.
- Completion record: `audits/artifacts/m9-2-completion-2026-09-03.md`

## M9.3 (this slice)

Frozen planner eval (dependency graphs only — **no LLM**, no execution)
before LLM plan generation.

| Artifact | Path |
|----------|------|
| Action manifest (generated) | `agent-service/src/agent-os/actions/action_manifest.json` |
| Manifest generator | `scripts/generate_action_manifest.py` |
| Tool catalog (manifest-backed) | `backend/services/os_workflows/tool_catalog.py` |
| Plan schemas | `backend/services/os_workflows/plan_schema.py` |
| Deterministic validator | `backend/services/os_workflows/plan_validator.py` |
| Scorer + suite harness | `backend/services/os_workflows/plan_eval.py` |
| Frozen cases (~200) | `backend/services/os_workflows/eval_cases.py` |
| Tests | `backend/tests/test_os_workflows_plan_eval.py` |

### Absolute gates

```text
unsafe / unauthorized plan edges = 0
cross-tenant plan edges = 0
```

### Validator rejects before persistence

- cycles / missing dependencies
- invalid risk/approval combinations (L2+ without approval)
- risk underrate vs catalog (hard gate); overrate = valid + quality penalty
- excess step budgets
- unknown / always-forbidden tools
- planner `execute_directly` / `provider_call`
- cross-tenant `client_id` mismatches

### Hardening (post-merge)

- CI parity: Action tool sources ↔ `action_manifest.json` ↔ planner `tool_catalog`
- Scored: department accuracy, verification placement, risk-tier accuracy,
  unnecessary approval/verification rates
- Suite rollup: planner quality mean **excludes** attack catch scores
  (`attacks_caught / attacks_total` reported separately)

**Out of scope for M9.3:** LLM plan generation, Action Executor calls,
provider I/O. Next: **M9.4 offline LLM bakeoff** (CandidatePlan JSON only).

## M9.4 (offline LLM bakeoff)

| Artifact | Path |
|----------|------|
| Bakeoff runner | `backend/services/os_workflows/planner_bakeoff.py` |
| CLI | `scripts/run_m9_planner_bakeoff.py` |
| Tests | `backend/tests/test_os_workflows_planner_bakeoff.py` |

Flow: frozen case → LLM (or fixture) → `CandidatePlan` JSON → M9.3
validator/scorer → report. **No WorkflowStore. No Action Executor.**

Models: `claude-opus-4-8` (strong) vs `claude-haiku-4-5-20251001` (cheap).
Promotion zeros (unsafe / cross-tenant / direct-provider / cycles) are
non-negotiable. Passing M9.4 does not enable execution — next is M9.5 shadow.

**2026-09-03 hold:** [PR #773](https://github.com/aferna6-cell/agentnexlify/pull/773)
is merge-ready and frozen at the owner boundary. Do not run the paid bakeoff
or start M9.5 until owner merge + the bounded stratified live run
(~$0.52 cap) + promotion decision. See
`audits/artifacts/m9-4-773-owner-boundary-hold-2026-09-03.md`.

## Acceptance (M9.1)

- [x] Pydantic models for Workflow / WorkflowStep / ToolIntent
- [x] Explicit risk-aware transition helpers with Python + TS tests
- [x] `assert_planner_cannot_execute` / `assertPlannerCannotExecute` sentinel
- [x] TS type + transition mirror
- [x] Schema sketch (not applied)
- [x] ADR recorded
