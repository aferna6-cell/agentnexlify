# Candidate Ideas — 2026-04-28-pm

Evidence window: 2026-04-25 → 2026-04-28.

## Evidence Digest (200 words)

Three days of high-volume commits: local_seo.py god-class extraction (673→221 LOC, 2 phases, full test coverage added in test_local_seo_handlers.py 414 lines); agent-system hardening (check_agent_system.py expanded, evaluate_agent_routing.py added 292 LOC, autopilot dispatch improved); steal-list features (idempotency, rate-limit, XFF spoofing fix merged via PRs #95/#96).

**Critical finding:** e68677a (2026-04-28) partially implemented Run 9 winner — patched 4 silent-catch violations (widget_chat.py:299, AuthContext.jsx:89, MarketingDashboardPage.jsx:90/96, LocalSEOPage.jsx:262) with proper logging. Pre-commit Check 9 (the guard) was NOT added. New violations can silently regress.

**Moratorium status:** e68677a classifies as `implemented_weakened` for run 3. Pending drops to 3 (runs 4, 7, 8) → moratorium LIFT condition met (≤ 3). Fresh ideas allowed.

**Other gaps found:** check-widget-sync.sh not created (run 7 pending), check_project_invariants.py not wired (run 8 pending), no billing/stripe tests exist (stripe_webhooks.py 188 LOC, no test files), local_seo_handlers.py already at 886 LOC (god class threshold 600), evaluate_agent_routing.py not wired into CI.

---

### Idea 1: Add pre-commit Check 9 — JS Silent Catch Guard
**Evidence:** e68677a patched 4 violations but no guard added. pre-commit hook ends at Check 8 (line 232). Same 3 violations (MarketingDashboardPage, LocalSEOPage, AuthContext) were undiscovered for 14+ days before subconscious found them — without a guard, the next batch can stay undiscovered equally long. Run 3 winner (2026-04-11, 17 days) is partially implemented; this is the missing half.
**Action:** Add ~8 lines to scripts/hooks/pre-commit: scan staged .js/.jsx/.ts/.tsx for `.catch(() => null)` or `.catch(() => {})`, BLOCK with message.
**Impact:** Closes run 3 fully; drops pending count to 3 → moratorium lifted. Prevents silent-catch regression on any future commit. S-effort.
**Category:** code_health

---

### Idea 2: Wire scripts/check_project_invariants.py into pre-commit
**Evidence:** 037865f added check_project_invariants.py (stdlib-only, catches client_id/tenant_id naming violations). Run 8 winner (2026-04-25, 3 days pending). Hook end still at Check 8; script unwired. Two spec-drift bugs (bug-patterns.md) used wrong column names — this guard would have caught both.
**Action:** Add single call to scripts/hooks/pre-commit after existing Python checks. ~3 lines. Exits non-zero on violations.
**Impact:** Blocks commits that use tenant_id/lead_stage/service_interest on covered tables. Closes run 8 winner. S-effort.
**Category:** code_health

---

### Idea 3: Create scripts/check-widget-sync.sh and wire into pre-push
**Evidence:** Run 7 winner (2026-04-24, 4 days pending). CLAUDE.md Invariant #4 states byte-identical widget copies; 3 paths confirmed (widget/, frontend/public/widget/, landing-page-v2/widget/). Script was never created. Any widget change that misses one copy silently breaks tenant embeds.
**Action:** Create scripts/check-widget-sync.sh (md5sum comparison of 2 active copies: widget/ → frontend/public/widget/) + add call to scripts/hooks/pre-push.
**Impact:** Prevents invisible widget drift at push time. Closes run 7 winner. S-effort.
**Category:** code_health

---

### Idea 4: Stripe webhook smoke tests
**Evidence:** stripe_webhooks.py 188 LOC, zero test files (test_billing*, test_stripe* absent). Parking-lot entry ROI 2.2 from run 7. Issue #99 (from run 9 backlog) identified SignatureVerificationError catch order bug in stripe_webhooks.py:46 that a smoke test would have caught. 821f660 touched 16 billing files with zero QA; no regression coverage exists.
**Action:** Create backend/tests/test_stripe_webhooks_smoke.py — 4-5 tests covering: valid sig path, invalid sig → 400 (not 500), plan-tier lookup, subscription cancelled event dispatch. Use existing mock patterns from test_widget_chat.py.
**Impact:** Catches billing regressions before prod. Issue #99 class prevented. ROI 2.2.
**Category:** code_health

---

### Idea 5: Split local_seo_handlers.py (886 LOC god class)
**Evidence:** local_seo_handlers.py was created yesterday (a002e18) and immediately breached the 600-line god-class threshold (User Rule 9) at 886 LOC. Contains 12 handler functions across 4 distinct domains: audit (execute_seo_audit, fetch_latest_audit, fetch_audit_history), keyword (execute_keyword_tracking, fetch_keyword_suggestions, fetch_keyword_rankings), competitor (execute_competitor_analysis, execute_analyze_seo_profile, fetch_seo_profile), geo (execute_geo_score, fetch_latest_geo_score, fetch_dashboard_widget).
**Action:** Split into backend/services/local_seo/ package: audit_handlers.py, keyword_handlers.py, competitor_handlers.py, geo_handlers.py. Update import in routers/local_seo.py.
**Impact:** Enforces Rule 9; prevents further bloat in the newly-created layer. Mirrors widget_helpers split pattern (run 5).
**Category:** code_health
