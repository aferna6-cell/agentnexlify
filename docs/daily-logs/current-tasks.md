# Current Task Backlog — AgentNexLiFy

Updated: 2026-07-20 (subconscious run 99 complete)

## Subconscious Run 99 — Action Items (2026-07-20)

- [x] **PR #482 closed, superseded by PR #483** — subconscious run 99 artifacts + Step 9F SKILL.md implementation merged via #483.
- [x] **Step 9F implemented in SKILL.md** — KB staleness check live on main (origin/main via PR #483). First nightly will run it.
- [ ] **ROTATE AUTOPILOT_GH_TOKEN in Railway** — GH #399, Day 18+. 30 ai-ready issues blocked. (Human action)
- [ ] **Set REFERRAL_REWARD_ENABLED=1 in Railway** — GH #413, Day 29+. Booking chain complete since PR #475. (Human action)

---

Updated: 2026-05-01 09:31 EDT (automated morning startup)

## Tomorrow's Top 3 Priorities

1. **ROTATE compromised admin API key in Railway** — DAY 34 of exposure. Still live. **CRITICAL — HUMAN ACTION REQUIRED.** Agent: **devops** / Human.
2. **Commit + QA `agent_escalation` service + tests** — `backend/services/agent_escalation.py` + `backend/tests/test_agent_escalation.py` untracked at EOD 2026-05-06. Rule 8 (no half-done migrations) risk. Agents: **backend-dev** + **qa-tester**.
3. **Fix Zapier plan_status bypass (GH issue #107)** — `_get_api_key_client` does not enforce `tenants.plan_status`; cancelled tenants still authenticate. Agents: **backend-dev** + **schema-guardian** + **qa-tester**.

## Completed (Recent)

### 2026-05-06 (today)
- [x] Health check: all green (no regression vs morning snapshot)
- [x] `e9c100e` ops: nightly-commit-review 2026-05-06 log written
- [x] `b25dbc4` kb: PageIndex tree-RAG assessment logged (decision: watch, no adopt)
- [x] `641a819` docs: yesterday's automated evening review committed
- [x] Daily log written for 2026-05-06
- [ ] **Carryover:** `agent_escalation` service + tests still untracked — see priority #2
- [ ] **Carryover:** 2 raw KB articles (subquadratic-claim, solo-agency-7-agent) added without compile cycle

### 2026-05-05
- [x] Health check: all green (silent_frontend_catch_count=0, was 6 this morning)
- [x] `72f8204` fix(admin-analytics): 6 silent catches → console.warn + pre-commit Check 9 (closes #109)
- [x] **Implement JS silent catch pre-commit guard** — Check 9 landed in `scripts/hooks/pre-commit` (Priority 2 task closed)
- [x] `27e06f0` refactor(settings): split SettingsPage god-class into 6 modules under `frontend/src/pages/settings/` (Rule 9)
- [x] `8f680e8` feat: AgentShield config security gate + baseline + GH workflow
- [x] `64e9058` feat: deterministic KB health check (`scripts/kb/kb-health.py`)
- [x] `edd6016` feat: require eval fixtures for canonical skills
- [x] `3b34984` refactor: prune always-on Claude prompt injections (CLAUDE.md, settings.json)
- [x] `d68fafa` subconscious run 14 — Wire golden eval harness to CI (winning concept selected)
- [x] `a84a5fa` ops: nightly-commit-review log written
- [x] `ee35d1f` kb: PageIndex tree-RAG assessment (watch, no adopt)
- [x] KB autopopulate ran 11:16 + 18:28; 5 wiki articles compiled
- [x] Daily log written for 2026-05-05

### 2026-05-01 (morning)
- [x] Health check: all green (dangerous_router=CLEAR, bare_except=0, silent_frontend_catch=0, widget_sync=OK, gitignore_env=YES)
- [x] Hardcoded API key scan: clean
- [x] Auto-log skeleton bug-pattern entries for `8050912` (Zapier plan_status bypass — issue #107 + LOW reasoning-trace cleanup)
- [x] Schema-log audit: migrations 100-117 documented; no new migrations in last 48h
- [x] Daily log written for 2026-05-01

### 2026-04-30 (no morning routine ran — gap day)
- [x] `8050912` fix(nightly-review): `_mask_phone` cleanup + filed issue #107
- [x] `f4b8166` feat(attribution): extend `get_activity_totals` with dollars/hours — slice 2
- [x] `f54dc7e` feat(attribution): dollar/hours attribution service — slice 1
- [x] `2baf7b2` merge: slice 3 UI — totals headline + activity feed UI
- [x] `37c151c` plans(onboarding-v2): implementation plan + 21 issue drafts
- [x] `8b91ec7` skills(agent-filter): Kimi K2.6 / GPT-5.5 cross-provider routing skip list
- [x] Subconscious runs 10/11/12 — JS Silent Catch Guard governance work
- [x] `0f2f075` ops-automation Phase 1 marked DONE (verified shipped 2026-04-22)

### 2026-04-29
- [x] Health check + hardcoded API key scan: clean
- [x] Auto-log skeleton entries for `ee4bc16` + `fb57995`
- [x] Merge `feature/58-zapier-auth` → main (`eed7794`); 98 upstream commits merged (`c02083c`)
- [x] Verify `scheduled_jobs` not dead code (`4540b39`); verify AMOUNT_TO_PLAN billing (`23f15cc`)

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key still live. **DAY 29 of exposure.** Agent: **devops** / Human.
- [ ] **Fix Zapier plan_status bypass (GH issue #107)** — backend-dev. Add `plan_status` check inside `_get_api_key_client`; regression test for cancelled tenant + valid key. (New 2026-05-01)
- [ ] **QA Zapier API key auth + per-key rate-limiting (merged `eed7794`)** — Agents: **schema-guardian** + **qa-tester** + **backend-dev**.
- [ ] **QA missed-call-text-back automation + migration 111 (`6020a43`)** — Agents: **qa-tester** + **widget-specialist**.
- [ ] **QA fraud guardrails — disposable email + signup velocity (`164d21b`)** — Agent: **qa-tester** + **backend-dev**.
- [ ] **QA onboarding wizard route + Stripe link (`c7c74f1`, `62f8722`)** — Agent: **qa-tester** + **frontend-dev**.

### Priority 0 — Schema (Pre-Launch)

- [ ] **Verify migration 117 (`zapier_api_keys`) applied in prod** — rename collision resolved 2026-04-28. Agent: **schema-guardian**.
- [ ] **Verify migration 116 (`idempotency_keys_rls`) applied in prod** — closes RLS gap from 114. Agent: **schema-guardian**.
- [ ] **Verify migrations 113/114/115 applied in prod** — fraud guardrails, idempotency_keys, contextual_reindex_marker. Agent: **schema-guardian**.
- [ ] **Verify migration 102 applied in prod** — `marketing_addon_*` columns on `tenants`. Agent: **schema-guardian**.
- [ ] **Verify migrations 103/104/105 applied in prod** — Flags + enrichment source. Agent: **schema-guardian**.

### Priority 1 — Critical / QA

- [ ] **QA dollar/hours attribution slices 1+2 (`f54dc7e`, `f4b8166`)** — verify `get_activity_totals` extension; agents: **qa-tester** + **backend-dev**. (New 2026-05-01)
- [ ] **QA slice 3 UI — totals headline + activity feed (`2baf7b2`)** — agents: **qa-tester** + **frontend-dev**. (New 2026-05-01)
- [ ] **Review onboarding-v2 implementation plan + 21 issue drafts (`37c151c`)** — feed to `prd-to-issues` skill, schedule into sprint. Agent: **planner**. (New 2026-05-01)
- [ ] **QA agent-filter Kimi K2.6 / GPT-5.5 routing (`8b91ec7`)** — verify cross-provider skip list. Agent: **qa-tester**. (New 2026-05-01)
- [x] ~~**Land JS Silent Catch Guard pre-commit hook (subconscious runs 10-12)**~~ — DONE 2026-05-05 (`72f8204` Check 9 + AdminAnalyticsPage fix).
- [ ] **QA steal-list 1-6 idempotency + rate-limit (`b0b1fb4`)** — base of `fb57995` fix. Agent: **qa-tester** + **backend-dev**.
- [ ] **QA `local_seo` refactor (`80f9815`, `a002e18`)** — verify no regression in vertical-tier SEO content. Agent: **qa-tester** + **frontend-dev**.
- [ ] **Verify agent-system guardrails (`d60331e`, `c289c2f`, `2bb6982`)** — `scripts/check_agent_system.py` clean, autopilot rollout cleanup. Agent: **devops**.
- [ ] **QA migrations 108/109/110 production paths** — photo-quote, drive-kb, zapier api keys. Agent: **schema-guardian** + **qa-tester**.
- [ ] **QA widget null-state 4-way guard (`8d026e6`)** — Agent: **widget-specialist**.
- [ ] **QA managed agents health probe (`3b0ce34`)** — Agent: **qa-tester**.
- [ ] **QA appointment_booker scaffold (`e2ac565`)** — Agent: **qa-tester**.
- [ ] **QA migrations 106 + 107 production paths** — Agent: **schema-guardian** + **qa-tester**.
- [ ] **QA invariants expansion (fac6124)** — Agent: **qa-tester**.
- [ ] **QA branding_helpers.py extraction (5f7117f)** — Agent: **widget-specialist**.
- [ ] **QA widget_chat_helpers shim removal (d2ab107)** — Agent: **backend-dev**.
- [ ] **QA widget_helpers god-class split (6cf4646)** — Agent: **widget-specialist**.
- [ ] **QA conftest TESTING + JWT secret env fix (9812fee, 0d94833)** — Agent: **qa-tester**.
- [ ] **QA business-type personalization (ad88397)** — Agent: **qa-tester**.
- [ ] **QA launch risk guardrails (99f8442)** — Agent: **qa-tester**.
- [ ] **QA service-layer extraction** — `ff293f4`. Agent: **qa-tester**.
- [ ] **QA scheduled_jobs.py split** — 5 modules. Agent: **qa-tester**.
- [ ] **QA Stripe marketing addon readiness guard** — `0278eb0` + `0482f7d`. Agent: **qa-tester**.
- [ ] **Act on launch-readiness rubric 114/262 NO-GO findings**.
- [ ] **QA tenant_scope adoption + CORS fix** — Agent: **qa-tester**.
- [ ] **QA industry packs** — `881e026`. Agent: **qa-tester**.
- [ ] **QA marketing infrastructure** — Agent: **qa-tester**.
- [ ] **QA Managed Agents integration** — Agent: **qa-tester**.
- [ ] **QA issue-to-pr loop + autopilot loop** — `777af3a` + `5ddbbce`. Agent: **qa-tester**.
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue`. Agent: **devops**.
- [ ] **Ingest competitor briefs to KB** — 5 briefs + `ghl-voice-ai-review-2026.md`. Manual `/kb-ingest` + `/kb-compile`.
- [ ] **Exercise migration duplicate-number pre-commit guard (2a08588)** — verified once via 117 collision; revisit. Agent: **devops**.

### Priority 2 — Code Quality & Verification

- [ ] **Implement reasoning-trace comment scanner pre-commit hook (LOW finding from `8050912`)** — flag `reasoning:`, `step N:`, `let me`, `I need to` patterns inside production source. Agent: **devops**. (New 2026-05-01)
- [ ] **Reconcile silent_frontend_catch_count glob drift**.
- [ ] **Fix 3 non-admin silent `.catch(() => null)` patterns** — Agent: **frontend-dev**.
- [x] ~~**Implement JS silent catch pre-commit guard**~~ — DONE 2026-05-05 in `72f8204` (Check 9 added).
- [ ] **Validate 47 rewritten skills** — `b83577f` + `0f1d23a`.
- [ ] **E2E test onboarding wizard** — Agent: **qa-tester** + **frontend-dev**.
- [ ] **Verify expired JWT token handling (6d10cf5)**.
- [ ] **Production verification of March 25 features** — **37+ days unverified.**
- [ ] **Audit `.get() or ""` operator precedence pattern**.
- [ ] **QA GitHub autopilot loop** — `5ddbbce`. Agent: **qa-tester**.
- [ ] **Remove remaining 5 MTOptions references**.
- [ ] **Remove MTOptions-growth from daily smoke tests**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich bug pattern for `8050912` Zapier plan_status bypass** — Skeleton auto-logged 2026-05-01 (issue #107). Run `/log-bug` for full root-cause + remediation detail once fix lands. (New 2026-05-01)
- [ ] **Enrich bug pattern for `8050912` reasoning-trace LOW** — auto-logged 2026-05-01. (New 2026-05-01)
- [ ] **Enrich bug pattern for `ee4bc16`** — slowapi callable signature fix. Auto-logged 2026-04-29.
- [ ] **Enrich bug pattern for `fb57995`** — idempotency race + RLS + XFF.
- [ ] **Compile `knowledge-base/wiki/competitors/ghl-voice-ai-review-2026.md`** — `/kb-compile`.
- [ ] **Enrich bug patterns from origin/main 2026-04-23 CI batch** — `4d9b25f`, `bcaba73`, `dbdcb23`, `212e04d`.
- [ ] **Enrich bug pattern for `fac6124`**.
- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeletons. (Carried since 2026-03-24)
- [ ] **Enrich bug patterns (#58-69)** — 12 skeletons from Apr 7-8.
- [ ] **Enrich bug patterns (#72-78)** — 7 skeletons from Apr 9 evening.
- [ ] **Enrich bug pattern for `9d48907`**.
- [ ] **Enrich bug patterns for `0278eb0` + `9febf89`**.
- [ ] **Enrich bug pattern for `c0aef59`**.
- [ ] **Enrich bug pattern for `080098b`**.
- [ ] **Act on vertical-specialize research findings (`e3963c5`)**.
- [ ] **Act on earlier research findings** — CAC/churn, plateau, unit economics.
- [ ] **Review 4 new research briefs (2026-04-18/19/20)**.
- [ ] **Compile / ingest 2026-04-18 competitor landscape snapshot (`fd6a09e`)**.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — pending 6+ weeks.
- [ ] **Fix 16 test isolation failures** — partially addressed.
- [ ] **Automated routine reliability** — Apr 17 morning log showed `git pull` failed on detached HEAD; no morning log on 2026-04-30 either. Verify auto-reattach + cron firing.
- [ ] **Create migration-gate hook** — Block new feature commits when pending migration count > 15.
- [ ] **Split bug-patterns.md** — now ~2,340 lines, 200 ### entries. Hot file. (Updated 2026-05-01)
- [ ] **Codify widget 3-way sync check as skill**.
- [ ] **Monitor `managed_agents_registry.py` for god-class trajectory**.
- [ ] **Tighten `auto-commit.sh` debounce**.
