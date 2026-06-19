# Winning Concept — 2026-06-19-pm (Run 62)

**Title:** Fix GH #292/#293 — Wire chatbot/agent_os into Plan-Name Dicts (run 62 mandate)
**Category:** code_health
**Confidence:** HIGH
**Effort:** S (~20 min, 3 files, ~12 lines)
**Autonomous-executable:** NO — product decisions on billing_reconciliation cap values needed
**Moratorium override:** YES — active product breakage for all new paid tenants since 2026-06-16
**RUN 62 MANDATE:** GH #308 unimplemented 4th cycle → mandate fires → switch to GH #292/#293

---

## Recommendation

Add `chatbot` and `agent_os` to all plan-name dicts in `sms_rate_limiter.py`,
`api_key_auth.py`, and `billing_reconciliation.py` so new paid tenants get correct
SMS limits, Zapier access, and reconciliation caps.

## Why This, Why Now

Billing was repriced 2026-06-16 to a 2-plan model ($19.99 chatbot / $99.99 agent_os)
via PRs #285-291. Three service files still carry old plan-name sets
(growth/autopilot/professional/enterprise) without the new plan IDs. Result: every new
paid tenant since 2026-06-16 gets wrong SMS rate limits, cannot use Zapier API keys, and
hits incorrect reconciliation caps. Run 62 mandate fires (GH #308 unimplemented 4 consecutive
cycles; governance pivot to lower-activation-energy fix, same pattern as run 35 pivot from
GH #181). Direct grep confirms all 3 files affected.

## Implementation Sketch

### File 1: `backend/services/sms_rate_limiter.py` (line 10)
```python
# Before:
_UNLIMITED_PLANS = {"growth", "professional", "autopilot", "enterprise"}

# After:
_UNLIMITED_PLANS = {"chatbot", "agent_os", "growth", "professional", "autopilot", "enterprise"}
```

### File 2: `backend/services/api_key_auth.py` (line 29)
```python
# Before:
_ALLOWED_PLANS = {"growth", "autopilot", "professional", "enterprise"}

# After:
_ALLOWED_PLANS = {"chatbot", "agent_os", "growth", "autopilot", "professional", "enterprise"}
```

### File 3: `backend/services/billing_reconciliation.py` (lines 33-48)
Add chatbot and agent_os entries to both cap tables. Suggested values:
```python
_PLAN_AGENT_RUN_CAPS: dict[str, int] = {
    "free": 25,
    "chatbot": 200,        # parity with growth (conservative default)
    "growth": 200,
    "autopilot": 500,
    "agent_os": 1500,      # parity with professional (agent-heavy plan)
    "professional": 1500,
    "enterprise": 10000,
}

_PLAN_BASELINE_AI_TOKENS: dict[str, int] = {
    "free": 150_000,
    "chatbot": 1_000_000,   # parity with growth
    "growth": 1_000_000,
    "autopilot": 1_200_000,
    "agent_os": 2_000_000,  # parity with professional
    "professional": 2_000_000,
    "enterprise": 5_000_000,
}
```
**Note:** Cap values are conservative defaults. Confirm with product before merging if
specific limits for chatbot/agent_os differ from parity-tier logic above.

### Regression Tests
Add to `backend/tests/test_sms_rate_limiter.py` (or create):
```python
@pytest.mark.parametrize("plan", ["chatbot", "agent_os"])
def test_new_plans_have_unlimited_sms(plan):
    assert is_unlimited_plan(plan)

@pytest.mark.parametrize("plan", ["chatbot", "agent_os"])
def test_new_plans_allowed_for_api_keys(plan):
    assert is_allowed_plan(plan)
```

## What This Replaces

GH #308 (webhook idempotency) was the winner for runs 59/60/61. Run 62 mandate pivots
to GH #292/#293 per 4-consecutive-run governance threshold.

## Confidence

**HIGH** — direct grep confirms all 3 files affected. Fix is additive (adding plan names
to sets/dicts, no removals). Only uncertainty is cap values for billing_reconciliation,
addressed by parity-tier defaults with product-review note.

---

## Bonus A — Fix GH #308 (do this next, ~20 min)

GH #308 still a revenue bug. Full sketch in `subconscious/runs/2026-06-19/winning-concept.md`.
After fixing GH #292/#293, implement GH #308 (delete_key in idempotency.py + callsite in
stripe_webhooks.py + regression test). Both fixes together close the 2 highest-priority
open issues.

## Bonus B — Add Plan-Name Guard Check 7 (AUTONOMOUS-EXECUTABLE, after Bonus A)

After Idea 1 lands: add check 7 to `scripts/check_project_invariants.py` — scan
sms_rate_limiter.py, api_key_auth.py, billing_reconciliation.py for "chatbot" and "agent_os".
FAIL if absent. ~15 lines Python. AUTONOMOUS-EXECUTABLE by nightly review.
Prevents future plan-name drift at commit time — self-healing loop.

## RUN 63 MANDATE

If GH #292/#293 still unimplemented by next run:
- Winner switches to Bonus A (GH #308, full sketch exists, ~20 min)
- Reasoning: GH #308 has 4-run history without mandate switch — both bugs need unlocking.
  Alternating between them applies continued pressure on both fronts.
