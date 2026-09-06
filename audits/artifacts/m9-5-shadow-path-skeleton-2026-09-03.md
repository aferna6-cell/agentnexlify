# M9.5 shadow-path skeleton — 2026-09-03

Offline design + test harness only. **No WorkflowStore. No Action Executor.
No provider calls.** No live bakeoff evidence in this slice.

## Why this exists

M9.4 is the last completed planner slice. The next product step is a
**shadow planner** on real owner requests: produce a `CandidatePlan`,
validate it, and keep the observation off the execution path.

This skeleton pins that boundary so a later slice can attach a planner
without accidentally persisting workflows or calling tools.

## Flow

```text
ShadowRequest (client_id, owner_goal, context)
        ↓
injected planner (or hard-fail)
        ↓
CandidatePlan JSON in memory
        ↓
M9.3 validate_plan
        ↓
ShadowObservation
  persisted=false
  executed=false
  provider_called=false
```

`store=` / `executor=` kwargs are accepted only so tests can prove they
are never invoked.

## Live / key policy

| Mode | Planner | `ANTHROPIC_API_KEY` | Result |
|------|---------|---------------------|--------|
| `fixture` | injected | any | in-memory observation |
| `live` | missing | absent | `RuntimeError` **before** any provider import/call |
| `live` | missing | present | `RuntimeError`: skeleton has no provider wiring |
| `live` | injected | any | in-memory observation, `provider_called=false` |

No live bakeoff was run. Do not treat this artifact as promotion evidence.

## Files

| Path | Role |
|------|------|
| `backend/services/os_workflows/shadow_planner.py` | request → observe, no I/O |
| `backend/tests/test_os_workflows_shadow_planner.py` | import + hard-fail + in-memory proofs |

## Not in this slice

- No `llm_runtime` import or Anthropic call
- No `os_workflows` / `os_workflow_steps` writes
- No Action Executor / Gmail / Calendar / CRM
- No router or Agent OS department wiring
- No promotion-bar claim
