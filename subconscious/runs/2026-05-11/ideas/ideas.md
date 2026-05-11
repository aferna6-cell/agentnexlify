# Ideation — Run 16 (2026-05-11)

**Moratorium Status:** ACTIVE. pending_approvals = 4 (runs 4, 7, 8, 14) > threshold = 3.
Run 4 now 25 days pending (> max_pending_age_days = 14). Zero implementation since run 15 (3 days).
Nightly reviews May 9-10 both flagged moratorium and confirmed moratorium still active.

---

### Idea 1: Widget 3-Copy Sync Guard (run 7 re-escalation, day 17)
**Evidence:** `scripts/check-widget-sync.sh` MISSING (verified May 11). Run 15 recommended this 3 days ago — no action taken. Nightly reviews May 9-10 confirm moratorium still active and flag S-effort items as "ready for 1-hour sprint when human approves." Three widget copies (`widget/`, `frontend/public/widget/`, `landing-page-v2/widget/`) currently in sync (nightly checks PASS), but guard is missing — next unsynced push would break all tenant embeds with no automated warning. CLAUDE.md Invariant #4 still says "2 copies."
**Action:** Create `scripts/check-widget-sync.sh` (diff 3 copies, FAIL on diverge). Wire into `scripts/hooks/pre-push`. Fix CLAUDE.md Invariant #4 to list 3 paths.
**Impact:** Closes run 7 (pending 4→3). With bonuses (run 8 = 5 min, run 14 = 20 min) drops pending 4→1 in ~1 hour. Exits moratorium.
**Category:** code_health

---

### Idea 2: Zapier API key plan_status enforcement (security, issue #107)
**Evidence:** bug-patterns.md entry (2026-04-30). `backend/services/zapier_auth.py::_get_api_key_client` resolves API keys without checking `plan_status`. Cancelled/past-due tenants with un-revoked API keys can still authenticate against Zapier endpoints. Issue #107 filed (HIGH). No code fix in 11 days. Zapier is the second external API surface (after widget) where plan-status enforcement was missing.
**Action:** Add `plan_status IN ('active','trialing')` filter inside `_get_api_key_client`. Return 402 for inactive tenants. Add regression test: seed cancelled tenant + valid key + assert auth fails.
**Impact:** Closes authentication bypass for cancelled accounts. Prevents revenue leakage (Zapier features used post-cancellation). High-severity security pattern match from bug-patterns.md.
**Category:** code_health (security)

---

### Idea 3: widget_helpers.py smoke tests (parking lot ROI 2.0)
**Evidence:** Split done via 6cf4646 (2026-04-18, run 5 winner). Status: `implemented_unverified`. 23 days post-split with no regression tests. Only `implemented_unverified` governance item. Nightly reviews May 9-10 show no Railway errors — production evidence suggests split is intact, but governance status is stale.
**Action:** Write `backend/tests/test_widget_helpers_smoke.py`: import each of 3 modules + call 1 function per module. Close `implemented_unverified` governance status.
**Impact:** Formalizes what production use has implied. Documents the split didn't break anything. ROI 2.0 parking lot item.
**Category:** code_health

---

### Idea 4: Onboarding V2 characterization tests (parking lot ROI 1.7)
**Evidence:** `plans/onboarding-v2_plan.md` has 21 issues. Sprint active. Zero characterization tests for the new onboarding flow. Prior sprint (widget_helpers split, run 5) ended as `implemented_unverified` — same pattern possible here. Prevents "built but unverified" syndrome before sprint ends.
**Action:** Write `backend/tests/test_onboarding_characterization.py` covering `POST /api/onboarding/start`, `complete_step`, `get_wizard_state`. Run against real API before declaring V2 sprint done.
**Impact:** Prevents `implemented_unverified` status for the 21-issue V2 sprint. ROI 1.7 parking lot.
**Category:** code_health

---

### Idea 5: Automated moratorium escalation hook (workflow)
**Evidence:** Run 16 is the 2nd consecutive run recommending Widget 3-Copy Sync Guard with zero implementation. JS Silent Catch required 6 moratorium-mode runs (9-13) before being implemented. Both nightly reviews flagged moratorium manually. There's no automated escalation — the subconscious recommends, nightly reviews flag, but no system creates implementation pressure independently.
**Action:** Add a moratorium escalation step to `scripts/daily/nightly-commit-review.sh`: when moratorium is active AND oldest pending > 14 days, auto-create a GitHub comment on the oldest pending issue linking to the winning-concept.md, flagging urgency.
**Impact:** Closes the loop between recommendation and implementation pressure. Reduces reliance on human monitoring the subconscious output.
**Category:** workflow
