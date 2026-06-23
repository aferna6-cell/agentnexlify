# Winning Concept — 2026-06-23

## Recommendation
Add a ~10-line plan-name guard block to `check_project_invariants.py` that imports `CURRENT_PAID_PLANS` from `plan_catalog.py` and verifies sms_rate_limiter._UNLIMITED_PLANS, api_key_auth._ALLOWED_PLANS, and billing_reconciliation caps each contain every plan in `CURRENT_PAID_PLANS`, failing pre-commit with an actionable error if any plan is missing.

## Why This, Why Now
GH #292/#293 fixed on 2026-06-21 (`29ed1d4`/`57f2bb4`/`c461cef`) — the 4th repricing-triggered gate drift incident. `plan_catalog.py` was simultaneously created (`3d4c7db`) as the canonical single source of truth with `CURRENT_PAID_PLANS = frozenset({"chatbot","agent_os"})`. The guard was explicitly deferred as "Bonus B, AUTONOMOUS-EXECUTABLE" across runs 59–64, gated on GH #292/#293 landing. GH #308 also resolved (`3a958e5`), clearing both alternating-mandate items — this is the first free-choice run since run 58. Pre-commit Check 7 fires at commit time, which catches drift that post-push CI misses when pushing directly.

## Implementation Sketch
- File: `scripts/check_project_invariants.py` (confirm exact path — also invoked from `backend/` context)
- Add a new invariant block after existing checks, labeled `"Check 7: Plan-name gate coverage"`:
  1. `from backend.services.plan_catalog import CURRENT_PAID_PLANS`
  2. Import each gate container (dynamic import or direct attribute read via importlib):
     - `sms_rate_limiter._UNLIMITED_PLANS` (dict — use `.keys()`)
     - `api_key_auth._ALLOWED_PLANS` (set or frozenset)
     - `billing_reconciliation._PLAN_AGENT_RUN_CAPS` and `_PLAN_BASELINE_AI_TOKENS` (dicts — use `.keys()`)
  3. For each gate: `missing = CURRENT_PAID_PLANS - set(gate_plans)`
  4. If `missing`: `print(f"FAIL check_7: {file}::{var} missing plans: {missing}")`, increment errors
  5. Ensure script returns non-zero exit if `errors > 0` (consistent with existing checks)
- Error message format: `"FAIL check_7: sms_rate_limiter._UNLIMITED_PLANS missing plans: {'chatbot'}"`
- Verify by running `python3 scripts/check_project_invariants.py` — should exit 0 on clean codebase
- Tag in pre-commit output: `"Check 7: plan-name coverage"`
- Keep stdlib-only (consistent with existing invariant checks — no new deps)

## What This Replaces
Both alternating-mandate items (GH #292/#293 and GH #308) are implemented as of 2026-06-21. Runs 59–64 were all mandate-driven with no free choice. This is the first run where Check 7 is not blocked by a prior prerequisite — it was previously conditioned on GH #292/#293 landing, which it has. No active mandate fires for run 65.

## Confidence
HIGH — all prerequisites confirmed: `plan_catalog.py` exists with canonical CURRENT_PAID_PLANS, GH #292/#293 implemented (plan-name dicts patched), 4 prior incidents from the same gate-drift class, deferred as Bonus B across 6 consecutive runs, ~10 lines of stdlib Python, AUTONOMOUS-EXECUTABLE scope matches nightly-commit-review capability profile.
