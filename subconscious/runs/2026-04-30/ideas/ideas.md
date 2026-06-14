# Candidate Ideas — 2026-04-30 (Run 9)

## Moratorium Context
`moratorium_active: true`. 4 unimplemented winners remain (runs 3, 4, 7, 8). Run 2 winner demoted: Lead Source Analytics chart EXISTS in `AnalyticsPage.jsx` lines 909–913 (confirmed implemented). Moratorium lift condition: ≤3 pending. Still not met.

Per governance.json protocol: "Run 9 synthesis: if moratorium_active=true, recommend implementing oldest unimplemented winner rather than generating fresh ideas."

Ideas below ranked by age (oldest pending first).

---

### Idea 1: JS Silent Catch Pre-commit Guard (Run 3 — Day 19+)
**Evidence:** Run 3 winner (2026-04-11). Violations confirmed today: `MarketingDashboardPage.jsx:96` (`.catch(() => null)`) and `LocalSEOPage.jsx:262` (`.catch(() => null)`). Pre-commit covers Python bare-excepts but not JS equivalent. Pattern causes silent analytics/SEO failures in production.
**Action:** Add Check 9 to `scripts/hooks/pre-commit` — grep staged `.js`/`.jsx` for `.catch(() => null)` / `.catch(() => {})`. Block on match.
**Impact:** Prevents silent error burial in frontend; breaks the pattern that hid the noshow_recovery CAN-SPAM bug (same root cause — swallowed exception).
**Category:** code_health
**Age:** 19 days unimplemented

---

### Idea 2: AI-to-Human Handoff v1 (Run 4 — Day 14)
**Evidence:** Run 4 winner (2026-04-16). customer-gaps.md: Critical, all 7 industries. Infrastructure exists (conversations table, webhooks, Twilio, Resend). Explicit-trigger-only scoped to 1.5-2 days.
**Action:** Add explicit handoff trigger to widget flow + Twilio/Resend notification on trigger.
**Impact:** Closes critical customer gap across all verticals. Differentiates from GoHighLevel on human-in-loop UX.
**Category:** customer_value
**Age:** 14 days unimplemented

---

### Idea 3: Widget 3-Copy Sync Guard (Run 7 — Day 6)
**Evidence:** Run 7 winner (2026-04-24). `scripts/check-widget-sync.sh` still MISSING today. CLAUDE.md Invariant #4 references 2 widget copies but 3 exist (widget/, frontend/public/widget/, landing-page-v2/widget/). Script was the entire winner — never created.
**Action:** Create `scripts/check-widget-sync.sh` that diffs all 3 widget JS paths and wire into pre-push hook.
**Impact:** Prevents byte-identity drift across 3 widget copies. Invariant #4 currently enforced only by human memory.
**Category:** code_health
**Age:** 6 days unimplemented

---

### Idea 4: Pre-fix Em-dash Violations then Wire check_project_invariants.py (Run 8 — Day 5, 2-step)
**Evidence:** Run 8 winner (2026-04-25). Script EXISTS at `scripts/check_project_invariants.py` but NOT in pre-commit. Critical blocker found today: script fails with 1 error — em-dash violations in `frontend/src/pages/wizard/WizardStepAutoKB.jsx` (lines 140, 172, 254). Wiring now would BLOCK all commits.
**Action:** Step 1: fix em-dash violations in WizardStepAutoKB.jsx. Step 2: add script call to pre-commit.
**Impact:** Closes naming-invariant enforcement gap (client_id, status, areas_of_interest). Currently enforcement is doc-only; 3+ production bugs from this class.
**Category:** code_health
**Age:** 5 days unimplemented. Has a blocker (em-dash fix needed first).

---

### Idea 5: Update Governance to Mark Run 2 as Implemented
**Evidence:** `implementation_lag_warning.oldest_pending` says "2026-04-06 (Lead Source Analytics, run 2)" — but AnalyticsPage.jsx lines 909-913 confirm the Recharts BarChart IS rendered. Governance.json is stale on this item. Fixes the moratorium count (5→4 pending) and corrects the implementation lag narrative.
**Action:** Update `governance.json` — mark run 2 winner as `implemented_unverified`, update `implementation_lag_warning.oldest_pending` to run 3 (JS Silent Catch), decrement `runs_pending_approval` count.
**Impact:** Accurate governance state. Moratorium count reflects reality. One admin task, zero code risk.
**Category:** workflow
**Age:** Governance drift since run 2 shipped
