# M9.2 completion — Persistent Planner persistence + correction pass

**Date:** 2026-09-03
**Status:** COMPLETE
**Head on main after merge:** `9f0dc889` (#754); current `main` also includes #756 morning digest → `697d7601` (docs-only; no M9 runtime change).

## Sequence

```text
M9.1 COMPLETE (#751) → M9.2 COMPLETE (#752 + #754) → READY FOR M9.3
```

## Delivered in M9.2

| Slice | PR | Notes |
|-------|----|-------|
| Persistence + deterministic engine | #752 (`a71a5838` → merge) | Migration 199, store, engine, CI import boundary |
| Correction pass (HOLD fixes) | #754 (`7e9ea5fa` → `9f0dc889`) | Retry/verify/unknown bounds + migration 200 |

## HOLD items closed by #754

1. Retryable step failure keeps workflow `running` until `max_retries` exhausted.
2. Execution success stops at `verifying` / `verification_state=pending` unless verification is explicitly `passed` or `not_required`.
3. L0/L1 `unknown` recovery shares the retry ceiling; L2/L3 remain cancel-only.
4. Migration 200 (199 untouched): composite `(workflow_id, client_id)` FK + transactional `create_os_workflow` RPC (`SECURITY DEFINER`, `PUBLIC` revoked, `service_role` only).

## Superseded

- Draft #753 (subconscious dead-guard recommendation) closed as superseded by #754.

## Still out of scope (M9.3+)

- LLM plan generation
- Connecting a model to workflow execution / Action Executor from planner modules

## Governance leftovers (non-blocking for M9.3)

- `main` branch protection still blocked on GitHub Pro (private-repo rulesets).
- #669 still formally open though central middleware/audit landed.

## Next

M9.3 frozen planner evaluation harness — dependency graphs + deterministic validator + absolute safety gates — **before** any LLM bakeoff.
