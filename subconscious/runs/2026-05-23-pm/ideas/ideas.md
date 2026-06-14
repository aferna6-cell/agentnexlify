# Ideas — Run 32 (2026-05-23-pm)

## Evidence Digest

**What changed (last 3 days):**
- 2174732 (largest commit in weeks): god-class refactor — branding_service, control_center, channels_facebook, pipeline, social_media. 5038 additions, 2064 deletions, 31 files, 13 new service files, 5 new test files (2221 lines). auth.py restructured (484 lines touched), branding_service.py deleted.
- 1eaaeec: "Fix billing AMOUNT_TO_PLAN" — came in today but FAILED to add the missing entries. Removed wrong legacy mappings but left 15000 and 25000 absent.
- 1553bf7 (nightly review 2026-05-23): wired test_billing_amount_to_plan.py into CI — now the contradictory tests (asserting 15000/25000 should NOT exist) actively block any correct billing fix from passing CI.
- GH #181 still open. moratorium day 18. Items A/B/D missing.

**What broke:** billing.py AMOUNT_TO_PLAN missing 15000→autopilot ($150/mo) and 25000→professional ($250/mo). CI now certifies this broken state via test_no_wrong_15000_mapping + test_no_wrong_25000_mapping.

**What's missing:** dashboard_service.py (266 lines, new extract) and conversations_service.py (169 lines, new extract) — coverage not confirmed in 5 new test files.

**What's working:** god-class refactor well-tested (2221 lines new tests). Autonomous nightly loop continues. Subconscious self-improving across 31 runs.

---

## 5 Candidate Ideas

### Idea 1: GH #181 Billing Fix — Run 31 Continuation with Stronger Evidence

**Evidence:**
- Direct inspection: AMOUNT_TO_PLAN has 9900 (growth, $99) and 89900 (enterprise, $899) but is missing 15000 (autopilot, $150/mo per CLAUDE.md) and 25000 (professional, $250/mo per CLAUDE.md)
- 1eaaeec attempted billing fix on 2026-05-23 and still missed the entries — confirms the fix is non-obvious even to humans reading the code
- 1553bf7 wired test_billing_amount_to_plan.py into CI — `test_no_wrong_15000_mapping` now asserts `15000 not in AMOUNT_TO_PLAN`, which BLOCKS any correct fix from passing CI (developer adds the entry, CI goes red, developer is confused)
- Test docstring calls 24900/29900/49900 "current pricing" — they are legacy. Misguides future readers.
- GH #181 open, confirmed by nightly review.

**Action:** Add `15000: "autopilot"` and `25000: "professional"` to billing.py AMOUNT_TO_PLAN. Remove `test_no_wrong_15000_mapping` and `test_no_wrong_25000_mapping`. Add `test_current_autopilot_150` and `test_current_professional_250`. Update `test_all_four_current_tiers_present` to use `{9900, 15000, 25000, 89900}`. Close GH #181.

**Impact:** Tenants at current $150/autopilot and $250/professional price points without `metadata.plan` correctly resolve in `_resolve_plan()`. CI guards against future drift. No more contradictory test blocking future billing fixes.

**Category:** code_health

---

### Idea 2: Smoke Tests for Uncovered Extractions — dashboard_service.py + conversations_service.py

**Evidence:**
- 2174732 created 13 new service files. Five new test files (test_extracted_services.py 897L, test_facebook_oauth_webhook.py 758L, test_pipeline_analytics.py 182L, test_pipeline_presets.py 143L, test_social_media_ai.py 241L) total 2221 lines.
- New test files cover: facebook_oauth, facebook_webhook, pipeline_analytics, pipeline_presets, social_media_ai, and extracted_services (likely control_center + social).
- NOT confirmed in any test file: dashboard_service.py (266 lines — dashboard fetch/aggregation logic), conversations_service.py (169 lines — conversation business logic extracted from conversations.py).
- conversations.py only had 10 lines changed in the refactor — the new conversations_service.py is an untested new layer.

**Action:** Write backend/tests/test_dashboard_service.py (smoke imports + 3 representative function calls with mocked Supabase) and verify conversations_service.py is covered by existing tests (grep test_extracted_services.py).

**Impact:** Catches regressions introduced in the largest structural change in weeks before a production incident.

**Category:** code_health

---

### Idea 3: Invoke /moratorium-sprint — Items A+B+D (~40 min)

**Evidence:**
- moratorium-sprint SKILL.md exists (7985fbb, 2026-05-19)
- Items A (check_project_invariants pre-commit, ~5 min), B (widget sync guard, ~15 min), D (CI eval workflow, ~20 min) still MISSING — confirmed each of the last 4 nightly reviews
- Pending 7. After sprint: 7→3 = moratorium exit (threshold is 2 now per max_pending_approvals=2... wait, let me check)
- Moratorium day 18, zero production implementation despite tool being ready 4 days

**Action:** User invokes /moratorium-sprint in interactive session. Tool reads governance.json, executes sketches for Items A+B+D, opens draft PR.

**Impact:** Moratorium exits. Future subconscious runs are free-choice. Post-moratorium: AI-to-Human Handoff v1 (run 4, 37d), Zapier security (GH #107, ROI 2.5), email N+1 (GH #112).

**Category:** workflow

---

### Idea 4: Zapier plan_status Enforcement — GH #107 Security

**Evidence:**
- GH #107 open 23+ days. backend/services/zapier_auth.py::_get_api_key_client resolves keys without plan_status check.
- Cancelled tenants with unrevoked API keys bypass plan tier gate — they continue to use Zapier integration at full throughput.
- Parking lot since run 16 (2026-05-11) with ROI 2.5. Moratorium protocol says: "Route via issue-to-pr-loop, NOT subconscious winner queue."
- No new evidence beyond aging.

**Action:** Add plan_status IN ('active', 'trialing') filter to _get_api_key_client. Write regression test.

**Impact:** Closes security hole. Prevents cancelled tenants from free API access.

**Category:** code_health / security

---

### Idea 5: Pre-commit Billing Sentinel — Guard AMOUNT_TO_PLAN After GH #181 Fix

**Evidence:**
- billing.py has had two AMOUNT_TO_PLAN regressions in 2 sprints (821f660 + c72b535 each touched it incorrectly)
- pattern: developers remove entries without adding correct replacements
- test file is now in CI but tests verify specific values — a pre-commit check would fail immediately at commit time, not in CI

**Action:** Add Check 11 to scripts/hooks/pre-commit: `python3 -c "from backend.routers.billing import AMOUNT_TO_PLAN; assert {9900,15000,25000,89900}.issubset(AMOUNT_TO_PLAN)"`. Runs in <1 second. Fails immediately if any current-price entry is removed.

**Impact:** Prevents the third AMOUNT_TO_PLAN regression. Billing constants become commit-safe not just CI-safe.

**Category:** code_health
