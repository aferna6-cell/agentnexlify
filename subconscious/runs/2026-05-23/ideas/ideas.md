# Ideas — Run 31 (2026-05-23)

## Evidence Digest (200 words)

17 commits in last 24h. Key signals:

**CRITICAL:** c72b535 (run 30's trigger event) removed wrong AMOUNT_TO_PLAN entries but failed to
add the current-price entries `15000→autopilot` and `25000→professional`. GH #181 filed by
nightly review (1553bf7) confirms the gap. Worse: `test_billing_amount_to_plan.py` lines 38-44
*explicitly assert* these keys should NOT exist (legacy expectation from issue #81) — CI is now
wired to this file and certifies the broken state as correct.

**God-class momentum:** `god-class-refactor_plan.md` created (c63888f), `local_seo_handlers.py`
split done as template. 54 targets remain. `email_sequences.py` (1255 lines) is the highest-ROI
next split.

**OS cleanup:** non-Claude AI configs removed (41b1952), .gitignore updated.

**Moratorium still active:** Items A/B/D (check-widget-sync.sh, widget sync guard,
lead-qualifier-eval.yml) all MISSING. Pending = 6.

**Run 30 winner partially addressed:** nightly review wired `test_billing_amount_to_plan.py`
into CI (1553bf7). But the test guards wrong values. `PLAN_TO_STRIPE_PRICE` cited in run 30
sketch does not exist in billing.py — sketch would have failed if implemented verbatim.

---

## Idea 1: Fix GH #181 — Add current-price entries to AMOUNT_TO_PLAN + fix contradictory test

**Evidence:**
- GH #181 (nightly review 1553bf7): c72b535 removed wrong mappings but did not add
  `15000→autopilot` ($150/mo) or `25000→professional` ($250/mo)
- `AMOUNT_TO_PLAN` inspection (billing.py:263-281): 9900→growth ✓, 89900→enterprise ✓,
  but 15000 and 25000 absent
- `test_billing_amount_to_plan.py` lines 38-44 assert `15000 NOT in` and `25000 NOT in`
  AMOUNT_TO_PLAN — these were correct for issue #81's old wrong entries, but are now
  backwards: CI certifies the missing mappings as correct behavior
- CLAUDE.md documented prices: autopilot=$150/mo, professional=$250/mo

**Action:**
Add `15000: "autopilot"` and `25000: "professional"` to AMOUNT_TO_PLAN in billing.py:281.
Update test file: remove/invert lines 38-44, add assertions that 15000 and 25000 DO map
correctly, update `test_all_four_current_tiers_present` to use `{9900, 15000, 25000, 89900}`.

**Impact:** Closes GH #181. Prevents silent plan downgrade for all current autopilot and
professional customers whose Stripe sessions lack metadata.plan. Corrects CI from certifying
broken state to catching future regressions.

**Category:** code_health
**Effort:** S (~15 min, 2 dict entries + ~4 test method updates)

---

## Idea 2: Invoke /moratorium-sprint (Items A+B+D, ~40 min)

**Evidence:**
- Items A/B/D all MISSING after 18+ moratorium days
- moratorium-sprint SKILL.md ready (7985fbb, 2026-05-19)
- Item A: check_project_invariants pre-commit (3 lines, 5 min)
- Item B: check-widget-sync.sh + pre-push wire + CLAUDE.md fix (15 min)
- Item D: .github/workflows/lead-qualifier-eval.yml (20 min)
- Pending 6→2 after sprint = moratorium exits

**Action:** Invoke /moratorium-sprint in interactive session.

**Impact:** Moratorium exits; full winner pipeline unblocked; 4 long-pending code-health guards
finally land.

**Category:** workflow
**Effort:** M (~40 min)

---

## Idea 3: email_sequences.py god-class split (1255 lines, first in queue)

**Evidence:**
- god-class-refactor_plan.md (c63888f): 54 targets, local_seo template done
- email_sequences.py is 3rd largest backend file at 1255 lines
- GH #112 (N+1: 1001 queries per 1000 enrollments, ROI 2.3) requires touching this file
- GH #113 (120-line duplication, _process_pending_sends) same file
- Template pattern established (local_seo execute + fetch + router migration)

**Action:** Split email_sequences.py → email_sequences_crud.py + email_sequences_enrollment.py
+ email_sequences_send.py. Full Rule 8 migration (all importers, tests green, old file deleted).

**Impact:** Closes GH #112/#113 opportunity, reduces blast radius on future sequence fixes.
Moratorium-safe (code health, not a new approval-queue item).

**Category:** code_health
**Effort:** M (~2 hr)

---

## Idea 4: Zapier plan_status enforcement (GH #107, 23+ days, ROI 2.5)

**Evidence:**
- bug-patterns.md entry: zapier_auth.py::_get_api_key_client resolves keys without
  plan_status check — cancelled tenants bypass tier gate
- GH #107 (2026-04-30), parking lot ROI 2.5 (highest in parking lot)
- 23 days since filing; no fix yet
- Fix path defined in bug-patterns.md: add `plan_status IN ('active','trialing')` filter

**Action:** Add plan_status filter to _get_api_key_client; add regression test seeding
cancelled tenant + valid key + asserting auth fails.

**Impact:** Closes security hole for cancelled-tenant Zapier bypass. S-effort, moratorium-safe.

**Category:** security / code_health
**Effort:** S (~20 min)

---

## Idea 5: Add current-price test coverage to test_billing_amount_to_plan.py (standalone)

**Evidence:**
- Existing test covers $249 (24900), $299 (29900), $499 (49900) — all LEGACY prices
- Current prices $99 (9900, in dict ✓ but untested), $150 (15000, MISSING), $250 (25000, MISSING)
  have no test coverage
- This is a subset of Idea 1 — subsumed if Idea 1 wins

**Action:** Add test methods for current prices (9900, 15000, 25000, 89900) to the existing
test class.

**Impact:** CI catches future billing regressions on current price points.

**Category:** code_health
**Effort:** XS (~5 min, subsumed by Idea 1)
**Note:** This idea is strictly subsumed by Idea 1. If Idea 1 wins, Idea 5 is implemented as part of it.
