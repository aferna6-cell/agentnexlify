# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-24 08:00 EDT (automated morning routine)

## Today's Top 3 Priorities

1. **ROTATE compromised admin API key in Railway** — DAY 22 of exposure. Key committed `9c87335`, scrubbed `d4463d7`. Still live in Railway. **CRITICAL — HUMAN ACTION REQUIRED.** Agent: **devops** / Human.
2. **Reconcile local `main` divergence with `origin/main`** — local HEAD is 6 ahead / 12 behind `origin/main`. Origin has onboarding-v2 Week 1 feature (`1432b68`) + migrations 115/116/117 + CI fixes (`4d9b25f`, `bcaba73`, `dbdcb23`, `212e04d`). Local has Stripe pricing + dotenv bump + noshow_recovery fix + 2026-04-24 subconscious run. Needs `git fetch + git rebase origin/main` (or merge) before further work. Agent: **devops** / Human.
3. **QA 2026-04-22 missed-call-text-back automation (`6020a43`, migration 111)** — migration 111 now documented in `schema-log.md` but prod apply still unverified; feature has zero QA pass. Agents: **qa-tester** + **widget-specialist**.

## Completed (Recent)

### 2026-04-24
- [x] Document migration 111 (`missed_call_texts`, `tenants.avg_ticket_override`, automations backfill) in `schema-log.md`
- [x] Add skeleton bug-pattern entries for origin/main CI fixes — `4d9b25f`, `bcaba73`, `dbdcb23`, `212e04d`
- [x] Morning health check: all green (dangerous_router=CLEAR, bare_except=0, silent_frontend_catch=0, widget_sync=OK, gitignore_env=YES)
- [x] Scan for hardcoded API keys: clean (no `sk_live_`/`sk_test_`/`sk-ant-` literals in code)

### 2026-04-23
- [x] KB autopopulate cycle — 14 raw ingests + 4 wiki promotions (`d540d32`, `f1f88ae`)
- [x] Automated evening review 2026-04-23 (this file)

### 2026-04-22
- [x] Ship missed-call-text-back ops automation + migration 111 (`6020a43`)
- [x] Add validation + distribution tooling for skills (`867919b`)
- [x] Commit 4 Phase-3 PRDs + schema-reference audit (`429c964`)
- [x] Verify path-scoped rules + align CLAUDE.md 200-line target (`fb79d3b`)
- [x] DESIGN.md tenant theming parked as phase-2 of onboarding-v2 (`6065043`)
- [x] Add plan-review-fanout skill + reference packs + context-budget hook (`9d42d98`)
- [x] Automated evening review 2026-04-21 (`734145a`)
- [x] Map Claude Code 35 techniques to AgentNexLiFy workflow (PR #78)
- [x] Auto-log bug fix from `33e0462` (appointment_booker tenant_id→client_id rename)
- [x] Adopt parallel Codex orchestration workstreams (PR #76)

### 2026-04-21
- [x] Scaffold `appointment_booker` managed agent (`e2ac565`)
- [x] Add managed agents health probe (`3b0ce34`)
- [x] Widen widget null-state guard → KB/CI/business_type/FAQs (`8d026e6`)
- [x] Expose marketing suite in dashboard sidebar (`56d7412`)
- [x] Seed + KB for power-washing prospect demo (`cece29f`)
- [x] Advance contractor wedge + launch-readiness evidence (`1d95fe6`)
- [x] Auto-log bug pattern skeletons for `8d026e6` + `3b0ce34`
- [x] KB ingest + compile: powerwash vertical intel, GHL April 2026 updates, AI harness pricing, Anthropic postmortem, state-of-AI-search 2026

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key still live. **DAY 22 of exposure.** Agent: **devops** / Human.
- [ ] **Reconcile local `main` divergence with `origin/main`** — 6 ahead / 12 behind. See Top-3 Priority 2 above. Agent: **devops** / Human. (New 2026-04-24)
- [ ] **Reattach HEAD to main + push 2026-04-17 work** — Verify `git branch --show-current == main` and `git status` clean. (Carried)
- [ ] **Investigate `morning-auto.sh` silent failure on 2026-04-23** — no daily log landed at 08:00; evening routine had to create the file. Agent: **devops**. (2026-04-24 morning ran successfully — verify cron schedule still OK after divergence resolved.)
- [ ] **QA missed-call-text-back automation + migration 111 (`6020a43`)** — newest shipped ops automation; zero QA. Migration 111 now documented in `schema-log.md` (2026-04-24). Agents: **qa-tester** + **widget-specialist**. (Carried 2026-04-23)

### Priority 0 — Schema (Pre-Launch)

- [ ] **Verify migration 102 applied in prod** — `marketing_addon_*` columns on `tenants`. Log entry says "status unknown — backfill only". Agent: **schema-guardian**.
- [ ] **Verify migrations 103/104/105 applied in prod** — Flags + enrichment source. Agent: **schema-guardian**.

### Priority 1 — Critical / QA

- [ ] **QA migrations 108/109/110 production paths** — photo-quote, drive-kb, zapier api keys. Agent: **schema-guardian** + **qa-tester**. (New 2026-04-21)
- [ ] **QA widget null-state 4-way guard (`8d026e6`)** — Exercise FAQ probe cache (`_CHAT_CACHE_TTL`); verify fallback triggers only when KB + CI + FAQs all empty and business_type = 'other'. Agent: **widget-specialist**. (New 2026-04-21 evening)
- [ ] **QA managed agents health probe (`3b0ce34`)** — Endpoint live; test coverage green; verify 503 surfaces on provider outage. Agent: **qa-tester**. (New 2026-04-21 evening)
- [ ] **QA appointment_booker scaffold (`e2ac565`)** — Registry wiring + fixtures; verify advisor-executor pattern hooks. Agent: **qa-tester**. (New 2026-04-21 evening)
- [ ] **QA migrations 106 + 107 production paths** — AI usage budget reservation, refund idempotency, dunning event log, cancellation event history. Agent: **schema-guardian** + **qa-tester**. (Carried)
- [ ] **QA invariants expansion (fac6124)** — conversations.tenant_id guard added to `check_project_invariants.py`. Exercise CI path; confirm auto-hook fails a synthetic bad commit. Agent: **qa-tester**. (New 2026-04-21)
- [ ] **QA branding_helpers.py extraction (5f7117f)** — Reverse-dep fix. Ensure widget chat helpers still resolve branding correctly. Agent: **widget-specialist**. (Carried)
- [ ] **QA widget_chat_helpers shim removal (d2ab107)** — Middle-hop shim dropped (Rule 8 no half-migrations). Verify all old import paths resolve via new layout. Agent: **backend-dev**. (Carried)
- [ ] **QA widget_helpers god-class split (6cf4646)** — 1,673-LOC split into 3 modules. Cross-origin embed + booking + lead capture need prod smoke. Agent: **widget-specialist**. (Carried)
- [ ] **QA conftest TESTING + JWT secret env fix (9812fee, 0d94833)** — Verify full backend pytest green in CI. Agent: **qa-tester**. (Carried)
- [ ] **QA business-type personalization (ad88397)** — Industry-aware widget + dashboard behavior. Agent: **qa-tester**. (Carried)
- [ ] **QA launch risk guardrails (99f8442)** — AI cost caps, refund audit, dunning events. Agent: **qa-tester**. (Carried)
- [ ] **QA service-layer extraction** — `ff293f4` branding/faq/conversations. Agent: **qa-tester**. (Carried)
- [ ] **QA scheduled_jobs.py split** — 5 modules: appointment/billing/email/lead/review. Cron paths re-verified. Agent: **qa-tester**. (Carried)
- [ ] **QA Stripe marketing addon readiness guard** — `0278eb0` + `0482f7d`. Agent: **qa-tester**. (Carried)
- [ ] **Act on launch-readiness rubric 114/262 NO-GO findings** — Dispute threshold 0.50%. Remaining fix-list needs execution. (Carried)
- [ ] **QA tenant_scope adoption + CORS fix** — 60+ routers, CORS `["*"]`. Cross-tenant leak = critical. Agent: **qa-tester**. (Carried)
- [ ] **QA industry packs** — 14 modules landed `881e026`. Agent: **qa-tester**. (Carried)
- [ ] **QA marketing infrastructure** — A/B tests, automation rules. Zero QA. Agent: **qa-tester**. (Carried)
- [ ] **QA Managed Agents integration** — Lead qualifier + document drafter + field monitor + researcher. Agent: **qa-tester**. (Carried)
- [ ] **QA issue-to-pr loop + autopilot loop** — Shipped `777af3a` + `5ddbbce`. Agent: **qa-tester**. (Carried)
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue`. Agent: **devops**. (Carried)
- [ ] **Ingest competitor briefs to KB** — 5 research briefs in `research-briefs/`. Manual. (Carried)
- [ ] **Exercise migration duplicate-number pre-commit guard (2a08588)**. Agent: **devops**. (Carried)

### Priority 2 — Code Quality & Verification

- [ ] **Reconcile silent_frontend_catch_count glob drift** — morning=0, evening=9 on same script. Fix `scripts/daily/health-check.sh` glob resolution. (Carried)
- [ ] **Fix 3 non-admin silent `.catch(() => null)` patterns** — `MarketingDashboardPage.jsx:96`, `LocalSEOPage.jsx:262`, `AuthContext.jsx:89`. Agent: **frontend-dev**. (Carried)
- [ ] **Implement JS silent catch pre-commit guard** — Subconscious `365d6ea` recommendation. Agent: **devops**. (Carried)
- [ ] **Validate 47 rewritten skills** — `b83577f` + `0f1d23a` Anthropic canonical. Spot-check critical skills. (Carried)
- [ ] **E2E test onboarding wizard** — 6-step wizard shipped 2026-04-01. (Carried)
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check. (Carried)
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset: **27+ days unverified.** (Carried)
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more. (Carried)
- [ ] **QA GitHub autopilot loop** — `5ddbbce`. Agent: **qa-tester**. (Carried)
- [ ] **Remove remaining 5 MTOptions references** — Post-cleanup audit ee35999 noted residual. (Carried)
- [ ] **Remove MTOptions-growth from daily smoke tests** — Done `ce36df7` but verify no remaining references. (Carried)

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich bug patterns from origin/main 2026-04-23 CI batch** — skeletons added 2026-04-24 for `4d9b25f` (secret-scan false positive), `bcaba73` (onboarding-v2 coverage relocation), `dbdcb23` (pyyaml), `212e04d` (importlib.reload + asyncio marks). Run `/log-bug` on each for root-cause + prevention detail. (New 2026-04-24)
- [ ] **Enrich bug pattern for `fac6124`** — Invariants guard conversations.tenant_id. Auto-logged skeleton 2026-04-21. (New 2026-04-21)
- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-69)** — 12 skeleton entries from Apr 7-8.
- [ ] **Enrich bug patterns (#72-78)** — 7 skeleton entries from Apr 9 evening.
- [ ] **Enrich bug pattern for `9d48907`** — Landing page Vercel routes fix (Apr 14).
- [ ] **Enrich bug patterns for `0278eb0` + `9febf89`** — Stripe + analytics. (Carried)
- [ ] **Enrich bug pattern for `c0aef59`** — widget_helpers patch target fix (Apr 19). (Carried)
- [ ] **Enrich bug pattern for `080098b`** — skills Phase 2+3 (Apr 19). (Carried)
- [ ] **Act on vertical-specialize research findings (`e3963c5`)** — Review deep-dive + open questions. (Carried)
- [ ] **Act on earlier research findings** — CAC/churn, plateau, unit economics. Pricing/positioning decisions pending. (Carried)
- [ ] **Review 4 new research briefs (2026-04-18/19/20)** — TCPA/CAN-SPAM, smb-self-serve, telemetry, white-label-reseller, widget-first, SMB verticals WTP, historical document automation waves. (Carried)
- [ ] **Compile / ingest 2026-04-18 competitor landscape snapshot (`fd6a09e`)** — `/kb-compile`. (Carried)

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — pending 5+ weeks.
- [ ] **Fix 16 test isolation failures** — partially addressed.
- [ ] **Automated routine reliability** — Apr 17 morning log showed `git pull` failed on detached HEAD. Verify auto-reattach.
- [ ] **Create migration-gate hook** — Block new feature commits when pending migration count > 15.
- [ ] **Split bug-patterns.md** — now >2,160 lines. Hot file, split by month/category.
- [ ] **Codify widget 3-way sync check as skill** — widget/ + frontend/public/widget/ + landing-page-v2/widget/ touched twice today. Bundle CI gate. (New 2026-04-21 evening)
- [ ] **Monitor `managed_agents_registry.py` for god-class trajectory** — 3 edits today. Split if next extension pushes past 600 LOC. (New 2026-04-21 evening)
- [ ] **Tighten `auto-commit.sh` debounce** — 3 auto-commit churn commits today. Reduce commit-log noise. (New 2026-04-21 evening)
