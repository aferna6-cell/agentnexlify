# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-14 20:07 EDT (automated evening routine)

## Tomorrow's Top 3 Priorities

1. **ROTATE compromised admin API key in Railway** — DAY 12 of exposure. Key committed in 9c87335, scrubbed in d4463d7. Still live in Railway. **CRITICAL — HUMAN ACTION REQUIRED.**
2. **QA tenant_scope adoption + CORS fix in production** — 60+ routers touched, CORS hardcoded to `["*"]`. Highest production risk. Agent: **qa-tester**.
3. **QA Managed Agents integration** — Lead qualifier + doc drafter + field monitor + researcher. Revenue feature, no production QA. Agent: **qa-tester**.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key committed in 9c87335, scrubbed in d4463d7. Key is still live. DAY 12 of exposure — **CRITICAL**. Agent: **devops** / Human. (Carried from Apr 5)

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [x] **All migrations 001-101 documented** — verified 2026-04-14 evening health check. Schema-log.md covers every migration file.

### Priority 1 — Critical / QA

- [ ] **QA tenant_scope adoption + CORS fix** — 60+ routers touched in auto-commits + CORS now hardcoded `["*"]`. Verify widget on external customer domains. Cross-tenant leak = critical. Agent: **qa-tester**.
- [ ] **QA industry packs** — 14 new modules landed (881e026). No per-pack tests beyond base. Agent: **qa-tester**. (Apr 10)
- [ ] **QA marketing infrastructure** — A/B tests, automation rules, marketing dashboard. Zero QA. Agent: **qa-tester**.
- [ ] **Verify security fixes (2ab39dd, d7572eb, e2dbf36, 29aca88)** — 25+ security patches. Agent: **qa-tester**.
- [ ] **QA Apr 8-10 fix batch** — 18+ bug fixes across multiple commits (noshow cache, session_id, header injection, async blocking, hardcoded URLs, CORS, test transport). Agent: **qa-tester**.
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue` (not just bare `except:`). Agent: **devops**.
- [ ] **QA Managed Agents integration** — Lead qualification + document drafter + field monitor + researcher. Smoke tests pass but no production QA yet. Agent: **qa-tester**.
- [ ] **QA issue-to-pr loop** — Shipped in 777af3a. PR feedback scripts + skill. Needs testing. Agent: **qa-tester**.
- [ ] **Ingest competitor briefs to KB** — 5 research briefs in `research-briefs/` need `/kb-ingest` to enter the wiki. Agent: manual.

### Priority 2 — Code Quality & Verification

- [ ] **Fix 4 silent .catch(() => null) patterns** — MarketingDashboardPage (1), LocalSEOPage (1), DocumentsPage (1), InvoicesPage (1). AdminAnalyticsPage (6) are intentional admin-only degraded mode. Agent: **frontend-dev**.
- [ ] **Implement JS silent catch pre-commit guard** — Subconscious run `365d6ea` recommended adding silent `.catch(() => {})` detection to pre-commit hook. Agent: **devops**.
- [ ] **Validate 47 rewritten skills** — `b83577f` rewrote skills to match Anthropic canon. Spot-check critical skills still trigger correctly.
- [ ] **E2E test onboarding wizard** — 6-step wizard shipped 2026-04-01. Needs QA.
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset: **21+ days unverified.**
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more.
- [ ] **QA GitHub autopilot loop** — `feat(autopilot)` landed (5ddbbce). PR review scripts + skill. Needs testing. Agent: **qa-tester**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries still need human enrichment. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-69)** — 12 skeleton entries from Apr 7-8 fix commits. Need root cause details.
- [ ] **Enrich bug patterns (#72-78)** — 7 skeleton entries from Apr 9 evening. Auto-logged, need human review.
- [ ] **Enrich bug pattern for 9d48907** — Landing page Vercel routes fix (Apr 14). Skeleton auto-logged, needs root cause.
- [ ] **Act on research findings** — 3 new articles today (CAC/churn, plateau, unit economics). Pricing and positioning decisions pending.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog (4+ weeks)
- [ ] **Fix 16 test isolation failures** — partially addressed, may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed; April 6 morning did not run.
- [ ] **Create migration-gate hook** — Block new feature commits when pending migration count > 15. Suggested by evening review pattern analysis.
- [ ] **Split bug-patterns.md** — 27 changes in 7 days, #1 hot file. Consider splitting by month/category.
- [ ] **Squash auto-commit noise** — 33% of today's commits are auto-commits. Consider a squash hook for Claude session commits.

## Completed (Recent) — 2026-04-14

- [x] **Morning health check** — all green except silent_frontend_catch_count=10 (6 intentional admin, 4 need review)
- [x] **Evening health check** — all stable. TODO/FIXME improved from 1→0.
- [x] **Documentation gap check** — all migrations + bug fixes documented
- [x] **3 research articles** — CAC/churn profile, AI chat widget plateau, unit economics if Anthropic raises prices
- [x] **KARPATHY.md** — four principles for LLM coding (3d6d819)
- [x] **Issue-to-PR loop** — feat(automation) shipped (777af3a) with ECC agent roster + Karpathy section
- [x] **3 hardening commits** — deployment checks, production monitoring, frontend audits (39d97cf, f938002, 1531abc)
- [x] **Landing page fix** — Vercel routes (9d48907)
- [x] **PR #10 merged** — hard-debug-agentnexlify (5849ba5)
- [x] **KB auto-populate** — 2 runs (06:20, 18:26), 13 raw sources, 8 wiki updates

## Completed (Recent) — 2026-04-11-13

- [x] **KB Karpathy wiki alignment** — auto-populate 2x/day cron (a23de42)
- [x] **KB lint skill** — validates articles against Karpathy template (66df82b)
- [x] **36 plugins installed** — routing rules documented in `.claude/rules/plugins.md` (5bc8e7e)
- [x] **47 skills rewritten** — aligned to Anthropic canon format (b83577f)
- [x] **4 plugin collisions fixed** — disabled duplicates of existing MCPs (e0aa0c2)
- [x] **GitHub autopilot loop** — P3 spec + implementation (b596364, 5ddbbce)
- [x] **Support email rename** — support@ -> help@ across legal + contact pages (730d75b)
- [x] **KB auto-populate fixes** — cron race condition, CLI resolution, schema correction (67bb565, 5bda9b3)
- [x] **KB content** — 15+ new wiki articles (competitors, AI/LLM, regulations, technical)
- [x] **Subconscious run** — JS silent catch guard recommendation (365d6ea)
- [x] **9 bug fixes** — portal, CI, CORS, runtime errors, null coercion, SSRF (Apr 13-14)
- [x] **Launch readiness rubric** — weighted scoring + go/no-go rules (d6a4546)
- [x] **2 research articles** — AI chat widget plateau, CAC/churn profile

## Overall Progress (2026-04-14 Evening)

- **Last commit:** 262df7d (kb log append, 2026-04-14 18:26)
- **Today's commits:** 21 (1 fix, 1 feature, 3 hardening, 3 research, 7 auto-commit, 6 docs/KB)
- **Codebase status:** Clean (git status clean)
- **Health check:** Green (widget sync OK, 0 bare excepts, 0 dangerous imports, 4 meaningful silent catches)
- **Frontend build:** PASS (3.65s)
- **Bug patterns total:** 85+ (all auto-logged)
- **Migrations documented:** 001-101 (all covered in schema-log.md)
- **SECURITY INCIDENT DAY 12:** admin API key — rotate in Railway **IMMEDIATELY**
- **Key activity today:** 1 feature (issue-to-pr), 1 fix, 3 hardening, 3 research, PR #10 merged, KB 2x auto-populate
- **silent_frontend_catch_count:** 4 meaningful (MarketingDashboard, LocalSEO, Documents, Invoices) — unchanged from morning

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
