# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-20 08:00 EDT (automated morning routine)

## Today's Top 3 Priorities

1. **ROTATE compromised admin API key in Railway** — DAY 16 of exposure. Key committed in `9c87335`, scrubbed in `d4463d7`. Still live in Railway. **CRITICAL — HUMAN ACTION REQUIRED.** Agent: **devops** / Human.
2. **QA migrations 106 + 107 applied 2026-04-19** — `billing_refunds`, `tenant_ai_usage_monthly`, RPCs `reserve_ai_token_budget` + `record_ai_token_usage` + `release_ai_token_reservation`, `refund_request_id` idempotency key. Admin refund endpoint depends on 107. Agent: **schema-guardian** + **qa-tester**.
3. **QA widget_helpers god-class split (6cf4646)** — 1,673-line file split into chat/lead/booking modules. Patch-target fixes landed in c0aef59. Widget chat + booking + lead flows need production smoke. Agent: **widget-specialist** + **qa-tester**.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key still live. DAY 16 of exposure — **CRITICAL**. Agent: **devops** / Human.
- [ ] **Reattach HEAD to main + push 2026-04-17 work** — Resolved? Verify `git branch --show-current == main` and `git status` clean. Carried from 2026-04-17. (New 2026-04-17)

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [x] **Migrations 102, 103, 105, 106, 107 all documented** — 102 backfilled this morning; 106/107 backfilled 2026-04-19 in commit 8560955.
- [ ] **Verify migration 102 applied in prod** — `marketing_addon_*` columns on `tenants`. Log entry says "status unknown — backfill only". Agent: **schema-guardian**.
- [ ] **Verify migrations 103/104/105 applied in prod** — Flags + enrichment source. Agent: **schema-guardian**.

### Priority 1 — Critical / QA

- [ ] **QA migrations 106 + 107 production paths** — AI usage budget reservation, refund idempotency, dunning event log, cancellation event history. Agent: **schema-guardian** + **qa-tester**. (New 2026-04-20)
- [ ] **QA branding_helpers.py extraction (5f7117f)** — Reverse-dep fix. Ensure widget chat helpers still resolve branding correctly. Agent: **widget-specialist**. (New 2026-04-20)
- [ ] **QA widget_chat_helpers shim removal (d2ab107)** — Middle-hop shim dropped under Rule 8 no-half-migrations. Verify all old import paths resolve via new package layout. Agent: **backend-dev**. (New 2026-04-20)
- [ ] **QA widget_helpers god-class split (6cf4646)** — 1,673-LOC split into 3 modules. Cross-origin embed + booking + lead capture need production smoke. Agent: **widget-specialist**. (New 2026-04-19)
- [ ] **QA conftest TESTING + JWT secret env fix (9812fee, 0d94833)** — 105 tests were blocked by missing env vars. Now unblocked; verify full backend pytest green in CI. Agent: **qa-tester**. (New 2026-04-18)
- [ ] **QA business-type personalization (ad88397)** — Industry-aware widget + dashboard behavior. Agent: **qa-tester**. (New 2026-04-18)
- [ ] **QA launch risk guardrails (99f8442)** — AI cost caps, refund audit, dunning events. Agent: **qa-tester**. (New 2026-04-18)
- [ ] **QA service-layer extraction** — `ff293f4` branding/faq/conversations. Agent: **qa-tester**. (Carried)
- [ ] **QA scheduled_jobs.py split** — 5 modules: appointment/billing/email/lead/review. Cron paths re-verified. Agent: **qa-tester**. (Carried)
- [ ] **QA Stripe marketing addon readiness guard** — `0278eb0` + `0482f7d`. Agent: **qa-tester**. (Carried)
- [ ] **Act on launch-readiness rubric 114/262 NO-GO findings** — Dispute threshold 0.50%. Remaining fix-list needs execution. (Carried)
- [ ] **QA tenant_scope adoption + CORS fix** — 60+ routers, CORS `["*"]`. Cross-tenant leak = critical. Agent: **qa-tester**. (Carried)
- [ ] **QA industry packs** — 14 modules landed `881e026`. Agent: **qa-tester**. (Carried)
- [ ] **QA marketing infrastructure** — A/B tests, automation rules. Zero QA. Agent: **qa-tester**. (Carried)
- [ ] **QA Managed Agents integration** — Lead qualifier + document drafter + field monitor + researcher. Agent: **qa-tester**. (Carried)
- [ ] **QA issue-to-pr loop + autopilot loop** — Shipped in `777af3a` + `5ddbbce`. Agent: **qa-tester**. (Carried)
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue`. Agent: **devops**. (Carried)
- [ ] **Ingest competitor briefs to KB** — 5 research briefs in `research-briefs/`. Manual. (Carried)
- [ ] **Verify migration duplicate-number pre-commit guard (2a08588)** — Subconscious run landed pre-commit guard for duplicate migration numbers. Exercise it locally. Agent: **devops**. (New 2026-04-20)

### Priority 2 — Code Quality & Verification

- [ ] **Reconcile silent_frontend_catch_count glob drift** — morning=0, evening=9 on same script. Fix `scripts/daily/health-check.sh` glob resolution. (Carried)
- [ ] **Fix 3 non-admin silent `.catch(() => null)` patterns** — `MarketingDashboardPage.jsx:96`, `LocalSEOPage.jsx:262`, `AuthContext.jsx:89`. Agent: **frontend-dev**. (Carried)
- [ ] **Implement JS silent catch pre-commit guard** — Subconscious `365d6ea` recommendation. Agent: **devops**. (Carried)
- [ ] **Validate 47 rewritten skills** — `b83577f` + `0f1d23a` Anthropic canonical. Spot-check critical skills. (Carried)
- [ ] **E2E test onboarding wizard** — 6-step wizard shipped 2026-04-01. (Carried)
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check. (Carried)
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset: **26+ days unverified.** (Carried)
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more. (Carried)
- [ ] **QA GitHub autopilot loop** — `5ddbbce`. Agent: **qa-tester**. (Carried)
- [ ] **Remove remaining 5 MTOptions references** — Post-cleanup audit ee35999 noted residual references. (New 2026-04-19)
- [ ] **Remove MTOptions-growth from daily smoke tests** — Already done `ce36df7` but verify no remaining references. (New 2026-04-18)

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-69)** — 12 skeleton entries from Apr 7-8.
- [ ] **Enrich bug patterns (#72-78)** — 7 skeleton entries from Apr 9 evening.
- [ ] **Enrich bug pattern for `9d48907`** — Landing page Vercel routes fix (Apr 14).
- [ ] **Enrich bug patterns for `0278eb0` + `9febf89`** — 2 auto-logged skeletons Stripe + analytics. (Carried)
- [ ] **Enrich bug pattern for `c0aef59`** — widget_helpers patch target fix (Apr 19). Auto-logged skeleton exists. (New 2026-04-20)
- [ ] **Enrich bug pattern for `080098b`** — skills Phase 2+3 (Apr 19). Auto-logged skeleton exists. (New 2026-04-20)
- [ ] **Act on vertical-specialize research findings** — `e3963c5`. Review deep-dive + open-questions. (Carried)
- [ ] **Act on earlier research findings** — 3 articles (CAC/churn, plateau, unit economics). Pricing/positioning decisions pending. (Carried)
- [ ] **Review 4 new research briefs (2026-04-18/19/20)** — TCPA/CAN-SPAM regulatory, smb-self-serve, telemetry coverage, white-label-reseller, widget-first defensibility, SMB verticals willingness to pay, historical document automation waves. (New 2026-04-20)
- [ ] **Compile / ingest 2026-04-18 competitor landscape snapshot (fd6a09e)** — Raw kb source. Run `/kb-compile`. (New 2026-04-20)

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — pending 5+ weeks.
- [ ] **Fix 16 test isolation failures** — partially addressed.
- [ ] **Automated routine reliability** — Apr 17 morning log showed `git pull` failed on detached HEAD. Verify auto-reattach logic.
- [ ] **Create migration-gate hook** — Block new feature commits when pending migration count > 15.
- [ ] **Split bug-patterns.md** — now 2,035 lines. Hot file, split by month/category.
- [ ] **Squash auto-commit noise** — 4 auto-commits on 2026-04-19, 2 on 2026-04-20 morning. Monitor.

## Completed (Recent) — 2026-04-19

- [x] **Migration 106 + 107 applied + verified** (8560955, 106/107 applied via Supabase MCP; docs backfilled)
- [x] **Branding helpers refactor** — `5f7117f` extract branding_helpers.py (reverse-dep fix) + `d2ab107` drop widget_chat_helpers middle-hop shim (Rule 8)
- [x] **Dead imports cleanup** — `e18f326` removed 14 dead imports across 6 files (audit Rank 7+10)
- [x] **widget_helpers god-class split** — `6cf4646` 1,673-LOC → 3 modules (chat/lead/booking)
- [x] **Widget patch-target fix** — `c0aef59` restored widget_helpers patch targets
- [x] **Skills Phase 2+3** — `080098b` bundled scripts (source-validation/improve-architecture/kb-compile), shell injection for morning/deploy-check/health-check/tenant-chatbot-audit, improve-architecture YAML fix
- [x] **Skills canonical rewrite** — `0f1d23a` Anthropic canonical SKILL.md patterns repo-wide
- [x] **3 new skills** — `ad3343c` source-validation, flowchart-decision-builder, scqa-writing
- [x] **Obsidian direct-vault mode** — `5f11559` documented
- [x] **Research runs** — telemetry coverage, smb-self-serve, white-label reseller, widget defensibility

## Completed (Recent) — 2026-04-20 AM

- [x] **Subconscious run — Migration Duplicate Number Pre-commit Guard** — `2a08588`
- [x] **KB auto-populate morning run** — `fa768c6`
- [x] **Morning health check** — all green (dangerous_router_imports=CLEAR, bare_except_count=0, silent_frontend_catch_count=0, widget_sync=OK, gitignore_env=YES)
- [x] **Migration 102 backfill in schema-log.md**

## Overall Progress (2026-04-20 Morning)

- **Last commit:** `2a08588` (subconscious: migration duplicate number pre-commit guard, 2026-04-20)
- **Commits since 2026-04-17 20:00:** 49
- **Codebase status:** Clean (no uncommitted changes). Widget byte-identical. HEAD on main.
- **Health check:** ALL GREEN.
- **Bug patterns total:** 2,035 lines (needs split per P4 task)
- **Migrations documented:** 001-107 (102 backfilled this morning)
- **Hardcoded API keys scan:** 0 matches in backend/ + frontend/src/ + widget/
- **TODO/FIXME count:** 0 backend, 0 frontend
- **SECURITY INCIDENT DAY 16:** admin API key — rotate in Railway **IMMEDIATELY**
- **Key activity since Apr 17:** Migrations 106+107 applied, branding helpers refactor, widget god-class split, skills canonical rewrite, 7 research runs

---

_This file is auto-updated by morning and evening routines. Manual edits welcome._
