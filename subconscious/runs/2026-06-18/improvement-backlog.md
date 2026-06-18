# Improvement Backlog — Run 2026-06-18

## Active

- Fix plan-name access dicts in sms_rate_limiter.py + api_key_auth.py — restores SMS and Zapier access for all new paid tenants (chatbot + agent_os). S-effort, ~15 min, human required.

## Parking Lot (survived debate but not chosen)

- **GH #308 idempotency row delete** (run 59 winner) — nightly review has complete sketch in `subconscious/runs/2026-06-17-pm/winning-concept.md`. Authorized nightly path. Promotes to winner if nightly doesn't implement within 2 days.
- **Bonus A: Fix billing_reconciliation.py + orchestrator.py** — complete GH #292/#293 scope. Requires product decision on agent-run caps and AI token baselines for new plans. Include in same PR as main winner.
- **email_sequences.py god-class split** (run 41, day 29+) — 1143L. Moratorium active, M-effort, parking lot until moratorium exits.
- **Cross-tenant isolation test for os_graph_memory** — parking lot since run 54.

## Rejected This Run

- **Idea 3 as winner** (Check 7 invariant guard) — WEAKENED: correct diagnosis but wrong sequence. Guard must follow the fix, not precede it. Promoted to Bonus B (AUTONOMOUS-EXECUTABLE after Bonus A lands).
- **Idea 2 as winner** (GH #308) — WEAKENED: nightly review already has the sketch. Lower breadth of impact than Idea 1 (subset of tenants vs 100%). Demoted to standing action.

## Questions for Next Run

1. Did nightly review implement GH #308 (idempotency fix) tonight? Confirm by checking for `delete()` method in `idempotency.py`.
2. Has the main winner (sms_rate_limiter + api_key_auth) been implemented? Confirm by grepping for `agent_os` in `_UNLIMITED_PLANS` and `_ALLOWED_PLANS`.
3. Did billing_reconciliation.py and orchestrator.py (Bonus A) land in the same PR?
4. Did Bonus B (Check 7 invariant guard) auto-execute via nightly review?
5. What is the true pending count after any implementations?
