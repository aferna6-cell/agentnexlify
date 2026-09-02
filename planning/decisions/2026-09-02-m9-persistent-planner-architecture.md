# M9 — Persistent Planner / Workflow State Machine

**Date:** 2026-09-02  
**Status:** Accepted — M9.1 contract in progress  
**Preceded by:** M8 COMPLETE · governance #750 · demo-role middleware #749

## Context

M1–M8 proved Action Executor, risk levels (0–3), approval gates, provider
ports, and independent verification. M9 adds a durable multi-step workflow
layer so the owner can state a goal and the system can plan, pause, resume,
and complete without the planner gaining tool authority.

## Decision

### 1. Planner never executes

**Decision:** The planner may only write/transition `Workflow` /
`WorkflowStep` records. All side effects go through the existing Tool/Action
contract → risk classification → approval → Action Executor → provider →
verification → workflow state transition.

### 2. Typed contract before persistence engine

**Decision:** M9.1 ships Pydantic + TypeScript types, explicit transition
allow-lists, and a schema sketch. M9.2 adds tables + deterministic engine.
M9.3 freezes an eval harness before any LLM plan generation.

### 3. Step states are explicit

```text
planned | ready | pending_approval | running | verifying
succeeded | failed | unknown | blocked | cancelled
```

`unknown` is sticky for L2/L3: cancel only — no automatic replay.

### 4. Tenant column naming

**Decision:** API / agent-service use `tenantId`. Postgres uses `client_id`
(same value). Never introduce `tenant_id` on workflow tables.

### 5. Risk levels reuse Action Executor integers

**Decision:** `riskLevel` is `0 | 1 | 2 | 3` — identical semantics to
`os_tool_executions.risk_level`. L2+ steps enter `pending_approval` before
`running`.

### 6. Precursor `os_projects` stays separate

**Decision:** `specs/os-projects_spec.md` / migration 183 remain a
dashboard-facing precursor. M9 workflows are the planner state machine and
do not merge into `os_projects` in M9.1–M9.3.

## Consequences

- No new tool ports in M9.1–M9.2.
- No LLM planning until M9.3 eval is solid.
- Schema sketch may land as migration 199+ at M9.2 apply time.

## References

- `planning/milestone-9-persistent-planner-kickoff.md`
- `specs/m9-persistent-planner_spec.md`
- `backend/services/os_workflows/contract.py`
- `agent-service/src/agent-os/workflows/types.ts`
- `agent-service/src/agent-os/actions/types.ts`
