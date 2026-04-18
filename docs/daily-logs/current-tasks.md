# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-17 20:01 EDT (automated evening routine)

## Tomorrow's Top 3 Priorities

1. **ROTATE compromised admin API key in Railway** — DAY 13 of exposure. Key committed in `9c87335`, scrubbed in `d4463d7`. Still live in Railway. **CRITICAL — HUMAN ACTION REQUIRED.**
2. **QA service-layer extraction + scheduled_jobs split** — `ff293f4` (branding/faq/conversations service layer extraction) and `5f3305a` (2,024 LOC scheduled_jobs.py split into 5 files by concern). Landed today, zero production QA. Agent: **qa-tester**.
3. **Reattach HEAD to main + push** — 28 commits today on detached HEAD. Unpushed. Needs human to choose branch + push.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key committed in `9c87335`, scrubbed in `d4463d7`. Key is still live. DAY 13 of exposure — **CRITICAL**. Agent: **devops** / Human. (Carried from Apr 5)
- [ ] **Reattach HEAD to main + push 28 today's commits** — HEAD detached since morning; 28 commits unpushed. Agent: Human. (New 2026-04-17)

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [x] **All migrations 001-101 documented** — verified 2026-04-14 evening health check. No new migrations 2026-04-17.

### Priority 1 — Critical / QA

- [ ] **QA service-layer extraction** — `ff293f4` extracted branding/faq/conversations into service layer. Needs production smoke + regression tests. Agent: **qa-tester**. (New 2026-04-17)
- [ ] **QA scheduled_jobs.py split** — `5f3305a` split 2,024-LOC god file into 5 modules: appointment_jobs, billing_jobs, email_jobs, lead_checks, review_jobs. All cron paths need re-verification. Agent: **qa-tester**. (New 2026-04-17)
- [ ] **QA Stripe marketing addon readiness guard** — `0278eb0` and `0482f7d` hardened Stripe payment readiness + marketing addon. New tests added; need production smoke. Agent: **qa-tester**. (New 2026-04-17)
- [ ] **Act on launch-readiness rubric 114/262 NO-GO findings** — `6e24773` + `92f3345` scored launch readiness as 114/262 NO-GO with 10 HIGH zeros. Dispute threshold set 0.50% (`58d9fe0`). Remaining NO-GO items need fix-list execution. (New 2026-04-17)
- [ ] **QA tenant_scope adoption + CORS fix** — 60+ routers touched in auto-commits + CORS now hardcoded `["*"]`. Verify widget on external customer domains. Cross-tenant leak = critical. Agent: **qa-tester**.
- [ ] **QA industry packs** — 14 new modules landed (`881e026`). No per-pack tests beyond base. Agent: **qa-tester**. (Apr 10)
- [ ] **QA marketing infrastructure** — A/B tests, automation rules, marketing dashboard. Zero QA. Agent: **qa-tester**.
- [ ] **Verify security fixes (2ab39dd, d7572eb, e2dbf36, 29aca88)** — 25+ security patches. Agent: **qa-tester**.
- [ ] **QA Apr 8-10 fix batch** — 18+ bug fixes across multiple commits. Agent: **qa-tester**.
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue` (not just bare `except:`). Agent: **devops**.
- [ ] **QA Managed Agents integration** — Lead qualification + document drafter + field monitor + researcher. Smoke tests pass but no production QA yet. Agent: **qa-tester**.
- [ ] **QA issue-to-pr loop** — Shipped in `777af3a`. PR feedback scripts + skill. Needs testing. Agent: **qa-tester**.
- [ ] **Ingest competitor briefs to KB** — 5 research briefs in `research-briefs/` need `/kb-ingest` to enter the wiki. Agent: manual.

### Priority 2 — Code Quality & Verification

- [ ] **Reconcile silent_frontend_catch_count drift** — morning=0, evening=9. Same script. Fix `scripts/daily/health-check.sh` glob resolution. (New 2026-04-17)
- [ ] **Fix 3 non-admin silent `.catch(() => null)` patterns** — `MarketingDashboardPage.jsx:96`, `LocalSEOPage.jsx:262`, `AuthContext.jsx:89` (in addition to 6 intentional `AdminAnalyticsPage.jsx` admin-only). Agent: **frontend-dev**.
- [ ] **Implement JS silent catch pre-commit guard** — Subconscious run `365d6ea` recommended adding silent `.catch(() => {})` detection to pre-commit hook. Agent: **devops**.
- [ ] **Validate 47 rewritten skills** — `b83577f` rewrote skills to match Anthropic canon. Spot-check critical skills still trigger correctly.
- [ ] **E2E test onboarding wizard** — 6-step wizard shipped 2026-04-01. Needs QA.
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset: **24+ days unverified.**
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more.
- [ ] **QA GitHub autopilot loop** — `feat(autopilot)` landed (`5ddbbce`). PR review scripts + skill. Needs testing. Agent: **qa-tester**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries still need human enrichment. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-69)** — 12 skeleton entries from Apr 7-8 fix commits.
- [ ] **Enrich bug patterns (#72-78)** — 7 skeleton entries from Apr 9 evening.
- [ ] **Enrich bug pattern for `9d48907`** — Landing page Vercel routes fix (Apr 14). Skeleton auto-logged, needs root cause.
- [ ] **Enrich bug patterns for `0278eb0` + `9febf89`** — 2 auto-logged skeletons from today's Stripe + analytics fixes. (New 2026-04-17)
- [ ] **Act on vertical-specialize research findings** — `e3963c5` landed a research project "should-agentnexlify-vertical-specialize-contractor". Review deep-dive + open-questions. (New 2026-04-17)
- [ ] **Act on earlier research findings** — 3 articles (CAC/churn, plateau, unit economics). Pricing and positioning decisions pending.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog (4+ weeks)
- [ ] **Fix 16 test isolation failures** — partially addressed, may still have remaining failures
- [ ] **Automated routine reliability** — April 17 morning log shows `git pull` failed (HEAD detached) and did not auto-reattach.
- [ ] **Create migration-gate hook** — Block new feature commits when pending migration count > 15.
- [ ] **Split bug-patterns.md** — now 1,897 lines. Hot file, split by month/category.
- [ ] **Squash auto-commit noise** — 4/28 today's commits are auto-commits (14%). Down from 33% yesterday. `/go` skill (`fecb531`) should further reduce. Monitor.

## Completed (Recent) — 2026-04-17

- [x] **Service-layer phase 1** — `ff293f4` extracted branding/faq/conversations from `auth.py`
- [x] **`scheduled_jobs.py` split** — `5f3305a` 2,024 LOC → 5 modules (appointment/billing/email/lead/review)
- [x] **Opus 4.7 routing update** — `393d336` updated advisor routing, model IDs, settings across `.claude/rules/`, AGENTS.md, CLAUDE.md, GEMINI.md, managed_agents_registry, llm_runtime, advisor_executor
- [x] **Prompt library update for Opus 4.7** — `0809adb` updated `task-budgets.md` + `PROMPTLIBRARY.md`
- [x] **Excalidraw docs skill (Codex)** — `b49aff4` `.codex/skills/excalidraw-docs/` + automation notes
- [x] **`/go` skill** — `fecb531` verify → simplify → PR → auto-merge; extended with dispute threshold + push-direct-to-main in `58d9fe0`
- [x] **Launch readiness rubric** — `6e24773` 114/262 NO-GO + 10 HIGH zeros
- [x] **Launch stress-test** — `92f3345` 4 failure sequences + operator fix list
- [x] **Stripe hardening** — `0482f7d` + `0278eb0` marketing addon readiness, tests in `tests/test_stripe_readiness.py` and `tests/test_stripe_webhook.py` (`8b9dc7b` observable state idempotency)
- [x] **Analytics package root re-export fix** — `9febf89` fix for `_period_to_days` in `backend/routers/analytics/__init__.py`
- [x] **OG image / iMessage preview** — `81f8749`, `5ab4902`, `3ebbb6c`, `01de159`, `ef234de` 3-tier OG preview iteration
- [x] **Marketing-first landing hero** — `9d27e2e` reorder features on Home.jsx
- [x] **Vertical-specialize research** — `e3963c5` deep-dive + exec summary + key players + open questions
- [x] **KB auto-populate 2x** — morning + evening runs (`bd8011c`, `2bead1d`, `e1a5e6b`, `b452446`); 10 raw sources + 4 wiki articles (claude-code-best-practices, claude-opus-4-7-release, ghl-lead-recovery-system, intercom-fin-monitors-observability)
- [x] **Morning + evening health check** — both ran; evening showed silent catch grep drift (see P2 task)

## Completed (Recent) — 2026-04-14

- [x] **Morning health check** — all green except silent_frontend_catch_count=10 (6 intentional admin, 4 need review)
- [x] **Evening health check** — all stable. TODO/FIXME improved from 1→0.
- [x] **Documentation gap check** — all migrations + bug fixes documented
- [x] **3 research articles** — CAC/churn profile, AI chat widget plateau, unit economics if Anthropic raises prices
- [x] **KARPATHY.md** — four principles for LLM coding (`3d6d819`)
- [x] **Issue-to-PR loop** — feat(automation) shipped (`777af3a`) with ECC agent roster + Karpathy section
- [x] **3 hardening commits** — deployment checks, production monitoring, frontend audits
- [x] **Landing page fix** — Vercel routes (`9d48907`)
- [x] **PR #10 merged** — hard-debug-agentnexlify (`5849ba5`)
- [x] **KB auto-populate** — 2 runs (06:20, 18:26), 13 raw sources, 8 wiki updates

## Overall Progress (2026-04-17 Evening)

- **Last commit:** `ff293f4` (refactor auth service layer, 2026-04-17 18:47)
- **Today's commits:** 28 (2 fix, 2 feat, 2 refactor, 1 research, 5 OG/meta, 4 auto-commit, 6 docs/launch, 6 other)
- **Codebase status:** HEAD detached. 28 unpushed commits. Widget byte-identical.
- **Health check:** Mostly green. `silent_frontend_catch_count=9` (morning=0, grep glob drift — P2 task).
- **Bug patterns total:** 1,897 lines (needs split per P4 task)
- **Migrations documented:** 001-101 (no new 2026-04-17)
- **SECURITY INCIDENT DAY 13:** admin API key — rotate in Railway **IMMEDIATELY**
- **Key activity today:** 2 major refactors (service layer + scheduled_jobs split), Opus 4.7 routing migration, launch readiness scoring + stress-test, Stripe hardening, /go skill shipped

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
