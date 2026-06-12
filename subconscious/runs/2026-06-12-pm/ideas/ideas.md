# Candidate Ideas — 2026-06-12-pm (Run 57)

## Evidence Summary

**PR #254 landed today** (31 files, 3500 insertions): approve-by-text, activation nudges, tenant health
board, Spanish widget, web push, 13 E2E journeys. It introduced 2 new `from __future__ import
annotations` violations in files that pre-commit Check 2 SHOULD have blocked (push_subscriptions.py
is in routers/). Root cause confirmed: all commits merging via GitHub squash PR bypass pre-commit
hooks entirely — hooks only run on local machines. Additionally, Check 2 only scans `*routers*.py`
(staged files), missing backend/services/ entirely. Result: 4 → 8 infected files in 24 hours.

check_project_invariants.py exits 1 with 3 failures:
- from __future__ in 8 backend files (routers/ + services/)
- 8 JSX em-dash violations (CookieConsent:31, MarketingUpsell:3, App.jsx:329, Sidebar.test.jsx:27/49,
  Sidebar.jsx:386, DemoBanner.jsx:4/7) — PR #254 added DemoBanner + Sidebar violations
- Third failure (likely client_id/lead status pattern in new service files)

Run 56 winner (Check 13 pre-commit guard, AUTONOMOUS-EXECUTABLE) not implemented by nightly d12bd21.

---

### Idea 1: Add `from __future__` CI check to pr-check.yml (AUTONOMOUS-EXECUTABLE)
**Evidence:** Pre-commit Check 2 (FAIL-mode, exists since run 56) only scans `$STAGED_FILES` matching
`*routers*.py` and runs ONLY on local commits — not GitHub PR merges or CI-agent commits.
push_subscriptions.py (routers/) committed with violation despite Check 2 existing. 4→8 files in 24h
proves bypass. Nightly created lead-qualifier-eval.yml (run 47 winner, AUTONOMOUS-EXECUTABLE) — same
mechanism.
**Action:** Add step to .github/workflows/pr-check.yml: grep `from __future__ import annotations`
across all `backend/**/*.py`, fail if found. ~8 lines YAML. AUTONOMOUS-EXECUTABLE.
**Impact:** CI-level enforcement blocks violations on every PR regardless of commit path or hook
installation. Systemic — no bypass route through GitHub merge, agent commits, or squash PRs.
**Category:** code_health

---

### Idea 2: Fix 8 JSX em-dash violations (AUTONOMOUS-EXECUTABLE, unblocks Item A chain)
**Evidence:** check_project_invariants exits 1 with em-dash failures (8 violations across 7 JSX files).
PR #254 added DemoBanner.jsx:4/7, Sidebar.jsx:386, App.jsx:329. Em-dash fix has 100% autonomous
success rate (nightly 8db33df fixed 5 previously via same channel).
**Action:** Replace 8 em-dash chars with hyphens in 7 JSX files. One nightly commit.
**Impact:** Clears one of 3 invariant failures. Partial unblocking — still needs from __future__ fix
for check_project_invariants to exit 0.
**Category:** code_health

---

### Idea 3: Remove `from __future__` from 8 backend files (HUMAN-REQUIRED, ~5 min)
**Evidence:** 8 files infected. Run 55 winner (channels_instagram.py, AUTONOMOUS-EXECUTABLE) not
executed by nightly d12bd21. Python line deletion NOT in confirmed autonomous scope. Human execution
= most reliable path.
**Action:** Delete `from __future__ import annotations` from line 1 of 8 files:
auth_billing.py, auth_google.py, auth_password_reset.py, channels_instagram.py, embed_instructions.py,
push_subscriptions.py (routers/) + activation_nudges.py, branding_helpers.py (services/).
**Impact:** Clears from __future__ invariant failure. Requires human this session.
**Category:** code_health

---

### Idea 4: Fix E2E fixture tenant gap so 13 E2E journeys go green
**Evidence:** PR #254 added 13 E2E journeys (demo funnel, vertical passthrough, approval inbox) in
e2e/journeys/ running in advisory CI (continue-on-error: true). Commit notes: "Runs red until
tonight's demo seed creates the fixture tenants (verified live: demo-login returns 'Demo is not set
up yet')". 13 tests always-red = zero CI signal.
**Action:** Trigger demo seed / verify demo_reset_job.py creates required fixture tenants
(salon/plumbing/financial_services). If it runs nightly, gap may self-resolve tonight.
**Impact:** 13 E2E tests go green → meaningful CI signal from the new advisory job.
**Category:** operational

---

### Idea 5: Add Python line deletion to nightly autonomous scope (scope extension)
**Evidence:** Nightly autonomous channel: JSX subs ✅ SKILL.md creation ✅ pre-commit bash ✅.
Python line deletion ❌ — run 55 winner not executed by d12bd21. Gap confirmed.
**Action:** Extend nightly-commit-review SKILL.md LOW-risk scope to include "delete line 1 from
listed Python files where line == `from __future__ import annotations`". AUTONOMOUS-EXECUTABLE.
**Impact:** Self-healing: nightly auto-clears from __future__ infections same cycle as discovery.
Extends meta-loop machinery for the 5th+ time.
**Category:** workflow
