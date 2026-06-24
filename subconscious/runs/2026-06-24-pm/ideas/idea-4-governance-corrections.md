# Idea 4: Governance Corrections + Moratorium Reassessment

**Category**: operational  
**Confidence**: HIGH (administrative)  
**Effort**: XS (~0 min — applied in Phase 6 regardless)  
**Autonomous**: YES — applies in Phase 6 of every run  
**Note**: Not competing for winner slot — applied unconditionally.

## Corrections to apply this run

### 1. Run 62 GH #292/#293 → implemented
Both active_directions entries for GH #292/#293 (plan-name dicts):
- Status: `pending_approval` → `implemented`
- Implemented date: 2026-06-23
- Implemented by: commits 57f2bb4d, 29ed1d43

Evidence: `backend/services/billing_reconciliation.py` contains `"chatbot": 800_000` and `"agent_os": 5_000_000`. `backend/tests/test_plan_gating_new_plans.py` created as runtime guard. `docs/dev-knowledge/bug-patterns.md` documents fix.

### 2. Run 59 GH #308 → implemented
Active_directions entry for GH #308 (webhook idempotency):
- Status: `pending_approval` → `implemented`
- Implemented date: 2026-06-23
- Implemented by: commit 3a958e5f

Evidence: `backend/services/idempotency.py` has `delete_key` method (lines 96-110). `backend/routers/stripe_webhooks.py:110` imports and calls `delete_key`.

### 3. Run 30 Billing Constants Contract Tests → moot
- Status: `pending_approval` → `moot`
- Reason: `test_plan_gating_new_plans.py` supersedes. Old billing model (5-plan AMOUNT_TO_PLAN) retired by 2-plan repricing 2026-06-16. The constants being tested no longer exist in the form that was tested.

### 4. Run 28 Invoke /moratorium-sprint → superseded
- Status: `pending_approval` → `superseded`
- Reason: Individual sprint items resolved via other paths. Items A (check_project_invariants Check 13, run 58), B (widget sync, run 57), C (SKILL.md escalation protocol, run 19), D (CI eval workflow, run 47) all implemented. Sprint no longer needed.

### 5. Run 35 email_sequences split (first framing) → superseded
- Status: `pending_approval` → `superseded`
- Reason: Run 41 is the canonical active_direction for email_sequences.py split. Run 35 first framing is stale (L effort, no new evidence). Run 41 entry remains active.

## Moratorium reassessment

Before corrections: true_pending_estimate ~9 (runs 4/20/21/28/29/35/38/41/59/62)
After corrections: true_pending_estimate ~5 (runs 4/20/21/29/38/41 + run 65 new winner)

Max_pending_approvals = 2. Even after corrections, true_pending (5-6) > threshold (2). **Moratorium remains active.**

However: both alternating mandate items (GH #308, GH #292/#293) are NOW IMPLEMENTED. The 6-cycle alternating mandate mechanism that dominated runs 59-64 is dissolved. Run 65 is the first free-choice run in 6 cycles.

Exit path cleaner now: runs 4/38 (AI-to-Human Handoff, ~1 day) + runs 20/21 (mostly superseded, need cleanup) + runs 29/41 (email split ~2h, moratorium sprint superseded) → true pending could drop to 2-3 if a sprint session is run.
