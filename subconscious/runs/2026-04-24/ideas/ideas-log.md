# Ideas Log — 2026-04-24

Generated from evidence gathered: 52 commits in 7 days, current-tasks.md P0-P4 review,
bug-patterns.md audit, governance.json implementation-lag analysis, pre-commit hook inspection.

---

### Idea 1: Widget 3-Copy Sync Guard (CLAUDE.md Invariant + CI Script)
**Evidence:** current-tasks.md (2026-04-21 evening): "Codify widget 3-way sync check as skill —
widget/ + frontend/public/widget/ + landing-page-v2/widget/ touched twice today." CLAUDE.md
only mentions 2 copies. The third copy (landing-page-v2/widget/) was touched twice in 48h, meaning
it is actively live, not legacy-dead. Fresh, high-signal.
**Action:** (1) Update CLAUDE.md Critical Invariant #4 to list all 3 widget paths. (2) Create
`scripts/check-widget-sync.sh` that diffs all 3 copies and exits non-zero on mismatch. (3) Wire
into pre-push hook or daily health-check.
**Impact:** Prevents silent widget drift in landing-page-v2 — customer demos run from landing page.
Drifted widget = broken demo = lost conversion. S-effort, zero infrastructure dependencies.
**Category:** code_health

---

### Idea 2: Widget Hot-Zone Regression Suite (Playwright E2E)
**Evidence:** governance.json parking_lot explicitly notes: "UNBLOCKED by run 5 winner
(widget_helpers.py split must land first). Promote to winner candidate in run 7." widget_helpers.py
split confirmed implemented via commit 6cf4646. ROI 2.1 in parking lot.
**Action:** Add Playwright E2E suite covering: cross-origin embed render, lead capture form submit,
booking flow initiation, AI fallback trigger. 4 tests, ~80 lines.
**Impact:** Automated regression net over the freshly-split widget modules.
**Category:** code_health

---

### Idea 3: Stripe Billing Smoke Tests — Post-Pricing-Update Harness
**Evidence:** Commit 821f660 (2026-04-23) touched 16 files across billing.py, BillingPage.jsx,
UpgradePrompt.jsx, WizardStepPlan.jsx. Revenue-critical pricing change with zero QA planned in
current-tasks.md. Pattern from bug-patterns.md: frontend-backend field name mismatches cause
silent billing failures.
**Action:** Create billing constants test harness — frontend component smoke tests for plan prices
+ backend plan-tier contract tests asserting pricing matches CLAUDE.md constants.
**Impact:** Prevents silent billing bugs from future pricing changes.
**Category:** customer_value / code_health

---

### Idea 4: bug-patterns.md Split by Month
**Evidence:** bug-patterns.md is 2,204 lines. Priority 4 task in current-tasks.md: "Split
bug-patterns.md — now >2,160 lines. Hot file, split by month/category." Read tool requires
offset/limit to load it — bug lookups now fail unless the engineer paginates.
**Action:** Split into monthly files + keep `bug-patterns-current.md` for hot entries.
Update auto-logger path to write to current file. Add INDEX.md.
**Impact:** Faster bug lookups, no offset/limit workaround, cleaner auto-logger writes.
**Category:** workflow

---

### Idea 5: Governance State Reconciliation
**Evidence:** governance.json shows 4 items as "pending_approval" but inspection reveals:
widget_helpers.py split is implemented (6cf4646) and migration duplicate guard is partially
implemented (Check 5 in pre-commit as WARNING not FAIL). Stale governance erodes trust in
the system — future runs get wrong prior context.
**Action:** Update governance.json to mark implemented items accurately. Add verification
step to SKILL.md Phase 0: "reconcile governance before generating ideas."
**Impact:** Accurate state for future runs.
**Category:** workflow
