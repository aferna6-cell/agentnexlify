# Milestone 9 START — Persistent Planner / Workflow State Machine

**Date:** 2026-09-02
**Status:** M9.1–M9.3 COMPLETE · M9.4 #773 merge-ready, **frozen at owner boundary**
**Preceded by:** M8 COMPLETE · #747 CI restore · #749/#669 demo-role middleware · #750 governance · #751 M9.1 · #752/#754 M9.2 · #757/#758 M9.3 · #764 M9.4 integrity

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

### M9.2 — Persistence + deterministic engine ✅

Workflow/step persistence (`migrations/199_os_workflows.sql` + integrity
`200_os_workflows_integrity.sql`), dependency resolution, resume after restart,
pause/resume on approval, terminal detection, bounded retry, L2/L3 unknown
non-replayable, execution≠verification separation. Still no LLM planning.

Artifacts:
- `backend/services/os_workflows/store.py`
- `backend/services/os_workflows/engine.py`
- `backend/tests/test_os_workflows_engine.py`
- CI import-boundary invariant in `scripts/check_project_invariants.py`
- Completion: `audits/artifacts/m9-2-completion-2026-09-03.md`

### M9.3 — Frozen evaluation harness

Before any model generates plans, score dependency graphs on frozen cases
(sequential, parallel, approvals, failed prerequisites, unknown outcomes,
partial completion, cross-tenant, prompt injection, destructive requests,
resume, duplicate/replay). Deterministic plan validator rejects cycles,
missing deps, invalid risk/approval, excess steps, and direct provider
execution. Absolute gates: unsafe/unauthorized edges = 0, cross-tenant = 0.

Only after M9.3 is solid: LLM-generated plans.

### M9.4 — Offline LLM bakeoff (FROZEN at owner boundary)

[PR #773](https://github.com/aferna6-cell/agentnexlify/pull/773) is merge-ready
(non-draft, PR Validation run 33783280252 green). Independent check agrees
with the stratified-default / report-integrity fix.

**Hold:** do not merge without owner approval. Do not run the paid bakeoff.
Do not start M9.5 shadow.

**After owner merge:** bounded stratified live run under the documented
~$0.52 cap, then promotion decision. Details:
`audits/artifacts/m9-4-773-owner-boundary-hold-2026-09-03.md`.

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
