# Milestone 9 START — Persistent Planner / Workflow State Machine

**Date:** 2026-09-02  
**Status:** START — M9.1 contract in flight (`cursor/m9-workflow-contract-a2c9`)  
**Preceded by:** M8 COMPLETE · #747 CI restore · #749/#669 demo-role middleware · #750 governance

## Governance gate (this kickoff)

| Item | Status |
|------|--------|
| M8 live proof | COMPLETE |
| #747 PR Validation green + merged | COMPLETE |
| #749 central demo-role middleware merged + Validation SUCCESS | COMPLETE |
| #669 allowlist audit | PASS — see `audits/artifacts/gh-669-allowlist-audit-2026-09-02.md` (issue close needs owner; API 403) |
| Branch protection on `main` | **BLOCKED** — private-repo rulesets require GitHub Pro (do not make repo public). Desired rule recorded below. |
| Direct-to-main auto-log bot | **FIXING** in companion PR — must open docs PRs, not push `main` |

### Desired `main` protection (enable after GitHub Pro)

```text
main
├─ PR required
├─ PR Validation required
├─ branch must be up to date
├─ no direct pushes
├─ no force pushes
├─ no deletion
└─ narrow owner break-glass bypass only
```

## Non-negotiable architecture

> **The planner may decide what should happen next. It may never independently perform the action.**

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

Unknown external outcomes stay **unknown**. No automatic replay of L2/L3 unknown outcomes.

## Phased delivery

### M9.1 — Workflow contract (first PR; no real tools)

Typed concepts:

- `Workflow` — id, tenantId (`client_id` at DB boundary), ownerGoal, status, createdAt, updatedAt
- `WorkflowStep` — id, workflowId, ordinal, description, dependencies[], department, toolIntent, state, riskLevel, executionId?, verificationState?, error?

Step states:

```text
planned | ready | pending_approval | running | verifying
succeeded | failed | unknown | blocked | cancelled
```

Deliverable: Pydantic/TS types + schema sketch + ADR. **No LLM. No executor calls.**

Artifacts:
- `backend/services/os_workflows/contract.py`
- `agent-service/src/agent-os/workflows/types.ts`
- `specs/m9-persistent-planner_spec.md`
- `specs/m9-workflow-schema-sketch.sql`
- `planning/decisions/2026-09-02-m9-persistent-planner-architecture.md`

### M9.2 — Persistence + deterministic engine

Workflow/step persistence, dependency resolution, resume after restart, pause/resume on approval, terminal detection, bounded retry, unknown stays unknown. Still no LLM planning.

### M9.3 — Frozen evaluation harness

Before any model generates plans, score dependency graphs on frozen cases (sequential, parallel, approvals, failed prerequisites, unknown outcomes, partial completion, cross-tenant, prompt injection, destructive requests, resume, duplicate/replay).

Only after M9.3 is solid: LLM-generated plans.

## Out of scope for M9.1

- Calling Gmail/Calendar/CRM/SMS tools
- Autonomous approval bypass
- Independent tool authority for the planner
- Changing M1–M8 Action Executor contracts

## References

- `audits/artifacts/m8-to-m9-transition-2026-09-02.md`
- `audits/artifacts/m8-formal-completion-2026-09-02.md`
- `audits/artifacts/gh-669-allowlist-audit-2026-09-02.md`
- Precursor (not M9): `specs/os-projects_spec.md`
