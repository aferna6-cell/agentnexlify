# M9 — Persistent Planner / Workflow State Machine

**Date:** 2026-09-02
**Status:** Accepted — M9.1 contract · M9.2 COMPLETE · M9.3 frozen eval  
**Preceded by:** M8 COMPLETE · governance #750 · demo-role middleware #749  
**Updated:** 2026-09-03 — M9.2 merged (#752/#754); M9.3 harness starts.

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

Step terminal states: `succeeded | cancelled`.
`failed` is retryable under explicit M9.2 bounded-retry policy.

### 4. Risk-aware approval is enforced (not advisory)

**Decision:** Transition helpers take `risk_level` / `riskLevel`.

- L0/L1: `ready → running` allowed
- L2/L3: `ready → pending_approval → running` required;
  `ready → running` is rejected
- Missing risk on gated edges fails closed (treated as L3)

### 5. Unknown outcomes are risk-tiered

**Decision:**

- L0/L1 `unknown`: controlled recovery to `planned` / `ready` / `blocked`
  / `cancelled` (bounded policy in M9.2)
- L2/L3 `unknown`: `cancelled` only — never automatically replayed

The risk gate — not a globally closed allowlist — enforces the L2/L3 rule.

### 6. Workflow failure is terminal

**Decision:** Workflow status `failed` has no outbound transitions
(including no `failed → cancelled`). Terminal workflow statuses:
`succeeded | failed | cancelled`.

### 7. Tenant column naming

**Decision:** API / agent-service use `tenantId`. Postgres uses `client_id`
(same value). Never introduce `tenant_id` on workflow tables.

### 8. Risk levels reuse Action Executor integers

**Decision:** `riskLevel` is `0 | 1 | 2 | 3` — identical semantics to
`os_tool_executions.risk_level`.

### 9. Precursor `os_projects` stays separate

**Decision:** `specs/os-projects_spec.md` / migration 183 remain a
dashboard-facing precursor. M9 workflows are the planner state machine and
do not merge into `os_projects` in M9.1–M9.3.

## Consequences

- No new tool ports in M9.1–M9.3.
- No LLM planning until M9.3 frozen eval + absolute gates are green.
- Schema applied as migrations 199–200 in M9.2.
- M9.2 CI invariant forbids planner/workflow modules from importing
  Action Executor / provider implementations directly.
- M9.3 ships a deterministic plan validator + ~200 frozen cases with
  absolute gates: unsafe/unauthorized = 0, cross-tenant = 0.

## References

- `planning/milestone-9-persistent-planner-kickoff.md`
- `specs/m9-persistent-planner_spec.md`
- `backend/services/os_workflows/contract.py`
- `agent-service/src/agent-os/workflows/types.ts`
- `agent-service/src/agent-os/actions/types.ts`
