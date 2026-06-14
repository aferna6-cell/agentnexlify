# Candidate Ideas — Run 56 (2026-06-12)

## Evidence Digest
- Run 55 winner (fix channels_instagram.py `from __future__` + 10 em-dashes) NOT implemented by nightly d12bd21 — autonomous channel ran but produced no code changes
- `from __future__ import annotations` infection SPREAD: was 1 file (channels_instagram.py, run 55 target); now 4 files (+ auth_password_reset.py, auth_billing.py, auth_google.py introduced by PR #238 auth.py split)
- check_project_invariants.py exits 1 with 2 failures: (1) from __future__ in 4 router files, (2) 10 JSX em-dash violations
- Check 10 NOT in pre-commit (0 grep matches); check-widget-sync.sh MISSING day 50+
- High dev velocity: 5 PRs merged in 3 days (PRs #237-#241) — voice recovery, N+1 fixes, auth split, Twilio sync, e2e CI
- AMOUNT_TO_PLAN still missing 15000→autopilot + 25000→professional (GH #181, rejected_paths)
- email_sequences.py still 1255L (run 41 winner, day many+)
- kb-autopopulate broken 35+ days (agent-browser CLI not installed)

---

### Idea 1: Add pre-commit Check 13 — `from __future__ import annotations` guard (FAIL mode)
**Evidence:** PR #238 (auth.py split) immediately introduced `from __future__` in 3 new router files. Run 55 targeted 1 file; now 4 are infected. 100% recurrence on every router split. Without a guard, every future god-class split produces the same CLAUDE.md Critical Invariant #5 violation. Check 11 (billing-constant-guard, 22 lines bash) and Check 12 (timing-safe guard) were autonomously implemented by nightly — same class.
**Action:** Add ~10-line bash block to scripts/hooks/pre-commit as Check 13: grep FastAPI router/service Python files in staged changes for `from __future__ import annotations`, FAIL if found. Add AUTONOMOUS-EXECUTABLE label in governance.json for nightly execution.
**Impact:** Prevents 422 errors on ALL future router splits, not just current ones. Self-healing: every commit validates the class. Without guard, god-class-splitter (14 targets remaining) will trigger this class every time.
**Category:** code_health

---

### Idea 2: Fix `from __future__` in all 4 files + 10 em-dashes (extends run 55 winner)
**Evidence:** check_project_invariants exits 1 with 4 from __future__ violations (channels_instagram.py + 3 auth split files) + 10 em-dash violations. Run 55 winner targeted only channels_instagram.py — 3 new files were introduced AFTER run 55 was written. Symptomatic fix for current violations.
**Action:** Remove `from __future__ import annotations` from line 1 of channels_instagram.py, auth_password_reset.py, auth_billing.py, auth_google.py. Fix 10 em-dash violations across main.jsx:152, CookieConsent.jsx:5+31, MarketingUpsell.jsx:3, App.jsx:325, Sidebar.test.jsx:27+49, Sidebar.jsx:386, ReferralCard.jsx:24+45. → exits 0 → Check 10 auto-wires tonight.
**Impact:** Unblocks Check 10 (56-day pending). Fixes active 422 risk on auth endpoints. 
**Category:** code_health

---

### Idea 3: Add cross-tenant isolation tests for os_graph_memory.py
**Evidence:** os_graph_memory.py (397L) confirmed zero cross-tenant tests (run 54 parking lot, ROI 2.1). Agent OS shipped 30+ new agents in Phase 3-4 (PRs #205-#212) + knowledge graph (c8a0460) — all operating on shared graph tables. No test validates tenant_a cannot read tenant_b's graph nodes/edges. Pattern: _TENANT_COLUMN_OVERRIDES miss was a 3rd-occurrence bug (c6805a5).
**Action:** Add backend/tests/test_os_graph_isolation.py — 3 parametrized pytest functions: seed 2 tenants' graph nodes, assert cross-tenant read returns empty, assert cross-tenant write is blocked. Mock Supabase RLS.
**Impact:** Closes security gap on Agent OS knowledge graph. Prevents silent data leakage as Agent OS scales to production customers. AUTONOMOUS-EXECUTABLE by nightly.
**Category:** code_health / security

---

### Idea 4: Fix kb-autopopulate.sh — replace agent-browser CLI with WebFetch fallback
**Evidence:** kb-autopopulate.sh broken 35+ days (agent-browser CLI not installed in this environment). With 5 PRs in 3 days, KB is getting stale — new features (voice recovery, Twilio sync, auto-send rules, e2e CI) are not reflected in the knowledge base. KB was already 34d stale at run 53.
**Action:** Edit scripts/daily/kb-autopopulate.sh: detect if agent-browser is installed (`which agent-browser`), fall back to WebFetch/curl if missing. Add 3-line conditional fallback.
**Impact:** Restores twice-daily KB updates. Makes KB current for AI responses about new features. 35-day gap causes agents to answer questions about old architecture.
**Category:** operational

---

### Idea 5: Home.jsx god-class split (1171L → HeroSection + FeaturesSection + CTASection)
**Evidence:** Home.jsx confirmed 1171L (run 55 parking lot, HUMAN-REQUIRED). PR #232 (run 55) refactored Home but it remains >600L threshold (CLAUDE.md Rule 9). god-class-splitter SKILL.md ready (e848b87). post-split-test-repair SKILL.md ready (d481799). Home.jsx is the customer-facing landing page — complexity risk to high-traffic route.
**Action:** Invoke /god-class-splitter on frontend/src/pages/Home.jsx — extract HeroSection.jsx, FeaturesSection.jsx, CTASection.jsx.
**Impact:** Reduces blast radius on landing page edits, enables A/B testing of sections independently. 
**Category:** code_health
**Note:** HUMAN-REQUIRED (frontend JSX splits not in nightly autonomous scope)
