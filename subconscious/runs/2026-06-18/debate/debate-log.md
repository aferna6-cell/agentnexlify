# Debate Log — Run 2026-06-18

Top 3 ideas by impact: Idea 1 (plan-name dicts), Idea 2 (idempotency), Idea 3 (invariant guard).

---

## Idea 1: Fix plan-name access dicts (sms_rate_limiter + api_key_auth)

### Round 1 — Is the evidence strong enough?

**Challenge:** The repricing was 3 days ago. Maybe these files were updated in a commit not yet indexed by git log. The grep could be stale.

**Defend:** Direct grep on live filesystem confirms both files. `sms_rate_limiter.py:10` reads `_UNLIMITED_PLANS = {"growth", "professional", "autopilot", "enterprise"}` — no `agent_os` or `chatbot`. `api_key_auth.py:29` reads `_ALLOWED_PLANS = {"growth", "autopilot", "professional", "enterprise"}` — no new plan names. These are current file contents, not historical.

### Round 2 — Is this the highest-leverage thing right now?

**Challenge:** Run 59 already flagged GH #308 as the winner with moratorium override. Switching winners one run later signals instability in the recommendation system.

**Defend:** Run 59 designated GH #308 as winner because at the time GH #292/#293 was Bonus A — plan-name gaps were known but unconfirmed with specific file:line evidence. This run confirms 4 files with specific broken dict values and specific impact (SMS rate limiting, API key access, AI token caps, branded emails). The evidence threshold for promotion is met. Governance has precedent: run 59 itself superseded run 58's winner when better evidence emerged.

### Round 3 — What could go wrong?

**Challenge:** Changing `_UNLIMITED_PLANS` to include `agent_os` may give agent_os tenants unlimited SMS even if the product decision was to cap them. Over-granting could increase costs.

**Defend:** Under-granting is worse. A $99.99/mo tenant who can't send SMS is a churn risk. The safe conservative fix: add `agent_os` to unlimited (agent OS is the premium tier, should be unlimited), give `chatbot` a moderate limit (200/day — same as legacy growth). Product owner can tune down later if needed. Wrong direction to under-serve a paying customer.

**Verdict: SURVIVES** — strongest current evidence, broadest immediate impact, confirmed 2 specific file:line, direct customer-facing feature regression.

---

## Idea 2: Fix GH #308 — idempotency row delete on handler exception

### Round 1 — Is the evidence strong enough?

**Challenge:** billing.py already has try/except that raises 500 to Stripe. Isn't that sufficient for Stripe to retry?

**Defend:** No. The 500 triggers Stripe retry, but `check_and_record` already wrote the idempotency row on the first call. When Stripe retries, it finds the row with `response_body=None`, returns `(False, in_flight=True)`. billing.py then does `if not is_new: return {"status": "ok"}` — skips processing, returns 200. Stripe stops retrying. Event permanently dropped. The partial fix (raising 500) is worse than nothing because it gives false confidence while the bug persists.

### Round 2 — Is this higher priority than Idea 1?

**Challenge:** Idempotency failures only occur when (a) a handler throws AND (b) the tenant then fixes their card and Stripe retries. That's a low-probability path.

**Defend:** True. GH #292/#293 plan-name dict bug affects 100% of new paid tenants on every request. GH #308 affects a smaller subset. On breadth of impact, Idea 1 wins.

### Round 3 — Has run 59 already provided enough direction?

**Challenge:** Run 59 gave a complete implementation sketch. Nightly review has the sketch. Why re-recommend?

**Defend:** Run 59's Option A was "nightly review 2026-06-18 implements." This is run 60 on 2026-06-18. If nightly hasn't implemented it yet, it will tonight. Promoting to winner again would duplicate the recommendation. Better to demote to standing action and let nightly handle it.

**Verdict: WEAKENED** → Parking lot / standing action. Nightly review has the sketch from run 59 winning-concept.md. GH #308 remains in active_directions as pending_approval. Run 60 does not re-recommend as winner — Idea 1 is higher priority.

---

## Idea 3: Add Check 7 to check_project_invariants.py (plan-name guard)

### Round 1 — Is this premature?

**Challenge:** Adding Check 7 before fixing the underlying bugs (Idea 1/4) means the check will fail immediately in CI. That's backwards.

**Defend:** Correct — sequencing matters. Check 7 should be added AFTER Idea 1 and Idea 4 land. As Bonus B (AUTONOMOUS-EXECUTABLE after fixes), it's perfectly timed. As winner, it's wrong-ordered. Demote to Bonus B.

### Round 2 — Would this have prevented the current bugs?

**Challenge:** The existing Check 6 ("retired plan names do not appear") might already cover this.

**Defend:** Check 6 scans for RETIRED names (foundation, operations) appearing where they shouldn't. Check 7 would scan for CURRENT names NOT appearing where they must. These are complementary guards at opposite ends: Check 6 prevents stale → Check 7 prevents missing. Current situation proves Check 7 is needed: new plan names absent from 4 critical files.

### Round 3 — Is AUTONOMOUS-EXECUTABLE realistic?

**Challenge:** check_project_invariants.py is a Python script. Nightly review's autonomous scope covers bash pre-commit additions but may not cover Python script edits.

**Defend:** check_project_invariants.py is in scripts/ and has been edited autonomously before (run 58 winner wired it into pre-commit). The pattern is established. AUTONOMOUS-EXECUTABLE is appropriate here.

**Verdict: WEAKENED** → Bonus B (sequenced after Idea 1+4 land, AUTONOMOUS-EXECUTABLE).

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 1 — Fix sms_rate_limiter + api_key_auth | SURVIVES → WINNER | Active direction |
| Idea 2 — Fix GH #308 idempotency | WEAKENED | Standing action (nightly has sketch) |
| Idea 3 — Add Check 7 to invariants | WEAKENED | Bonus B after fixes land |
| Idea 4 — Fix billing_reconciliation + orchestrator | Not debated (related to winner) | Bonus A |
| Idea 5 — email_sequences god-class split | Not debated | Parking lot (moratorium active) |

**Winner: Idea 1 — Fix plan-name access dicts (sms_rate_limiter.py + api_key_auth.py)**
**Confidence: HIGH**
