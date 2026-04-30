# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-29 08:05 EDT (automated morning startup)

## Today's Top 3 Priorities

1. **ROTATE compromised admin API key in Railway** — DAY 27 of exposure. Still live. **CRITICAL — HUMAN ACTION REQUIRED.** Agent: **devops** / Human.
2. **QA Zapier API key auth + rate-limiting (PR #91, branch `feature/58-zapier-auth`)** — `migrations/117_zapier_api_keys.sql` rename done (`c2a489d`). Verify migration applied prod, end-to-end auth + per-key limiter. Agents: **schema-guardian** + **qa-tester** + **backend-dev**.
3. **QA missed-call-text-back automation + migration 111 (`6020a43`)** — feature shipped 2026-04-22, prod apply + end-to-end QA still unverified. Agents: **qa-tester** + **widget-specialist**.

## Completed (Recent)

### 2026-04-29 (this morning)
- [x] Health check: all green (dangerous_router=CLEAR, bare_except=0, silent_frontend_catch=0, widget_sync=OK, gitignore_env=YES)
- [x] Hardcoded API key scan: clean
- [x] Auto-log skeleton bug-pattern entries for `ee4bc16` (slowapi rate-limit signature fix) + `fb57995` (idempotency race + RLS + XFF spoofing fixes)
- [x] Schema-log audit: migrations 100-117 all documented, no updates needed
- [x] Confirmed `62f8722` + `e68677a` already auto-logged

### 2026-04-28
- [x] Merge `origin/main` into `feature/58-zapier-auth` (`91250a0`) — branch now 28 ahead / 0 behind
- [x] Rename `112_zapier_api_keys` → `117_zapier_api_keys.sql` to resolve collision (`c2a489d`)
- [x] Silent-errors logging hardening (`e68677a`)

### 2026-04-26 to 2026-04-27
- [x] Ship Zapier CRM export endpoint with API key auth + per-key rate limiting (`eddcc3b`, PR #91)
- [x] Steal-list 1-6: idempotency keys + rate-limit module + tenant fraud guards (`b0b1fb4`)
- [x] Fix idempotency SELECT-then-INSERT race → upsert ignore_duplicates (`fb57995`)
- [x] Migration 116: enable RLS on `idempotency_keys` (was missing on 114)
- [x] Fix XFF spoofing: switch to `request.client.host` (`fb57995`)
- [x] Fix slowapi `_chat_rate_limit` signature for callable limit providers (`ee4bc16`)
- [x] Fraud guardrails: disposable-email + signup velocity (`164d21b`)
- [x] Onboarding wizard route + Stripe link (`c7c74f1`)
- [x] Onboarding soft edges (`62f8722`)

### 2026-04-25
- [x] `local_seo` refactor (`80f9815`, `a002e18`)

### 2026-04-24
- [x] Document migration 111 in `schema-log.md`
- [x] Skeleton bug-pattern entries for origin/main CI fixes — `4d9b25f`, `bcaba73`, `dbdcb23`, `212e04d`

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key still live. **DAY 27 of exposure.** Agent: **devops** / Human.
- [ ] **QA Zapier API key auth + per-key rate-limiting (PR #91)** — backend route + service + migration 117. Verify auth fail paths, rate-limit reset, key revocation. Agents: **schema-guardian** + **qa-tester** + **backend-dev**. (New 2026-04-29)
- [ ] **QA missed-call-text-back automation + migration 111 (`6020a43`)** — Agents: **qa-tester** + **widget-specialist**. (Carried)
- [ ] **QA fraud guardrails — disposable email + signup velocity (`164d21b`)** — Agent: **qa-tester** + **backend-dev**. (New 2026-04-29)
- [ ] **QA onboarding wizard route + Stripe link (`c7c74f1`, `62f8722`)** — Agent: **qa-tester** + **frontend-dev**. (New 2026-04-29)

### Priority 0 — Schema (Pre-Launch)

- [ ] **Verify migration 117 (`zapier_api_keys`) applied in prod** — rename collision resolved 2026-04-28. Agent: **schema-guardian**. (New 2026-04-29)
- [ ] **Verify migration 116 (`idempotency_keys_rls`) applied in prod** — closes RLS gap from 114. Agent: **schema-guardian**. (New 2026-04-29)
- [ ] **Verify migrations 113/114/115 applied in prod** — fraud guardrails, idempotency_keys, contextual_reindex_marker. Agent: **schema-guardian**. (New 2026-04-29)
- [ ] **Verify migration 102 applied in prod** — `marketing_addon_*` columns on `tenants`. Agent: **schema-guardian**.
- [ ] **Verify migrations 103/104/105 applied in prod** — Flags + enrichment source. Agent: **schema-guardian**.

### Priority 1 — Critical / QA

- [ ] **QA steal-list 1-6 idempotency + rate-limit (`b0b1fb4`)** — base of `fb57995` fix. Agent: **qa-tester** + **backend-dev**. (New 2026-04-29)
- [ ] **QA `local_seo` refactor (`80f9815`, `a002e18`)** — verify no regression in vertical-tier SEO content. Agent: **qa-tester** + **frontend-dev**. (New 2026-04-29)
- [ ] **Verify agent-system guardrails (`d60331e`, `c289c2f`, `2bb6982`)** — `scripts/check_agent_system.py` clean, autopilot rollout cleanup. Agent: **devops**. (New 2026-04-29)
- [ ] **QA migrations 108/109/110 production paths** — photo-quote, drive-kb, zapier api keys. Agent: **schema-guardian** + **qa-tester**. (Carried)
- [ ] **QA widget null-state 4-way guard (`8d026e6`)** — Agent: **widget-specialist**. (Carried)
- [ ] **QA managed agents health probe (`3b0ce34`)** — Agent: **qa-tester**. (Carried)
- [ ] **QA appointment_booker scaffold (`e2ac565`)** — Agent: **qa-tester**. (Carried)
- [ ] **QA migrations 106 + 107 production paths** — Agent: **schema-guardian** + **qa-tester**. (Carried)
- [ ] **QA invariants expansion (fac6124)** — Agent: **qa-tester**. (Carried)
- [ ] **QA branding_helpers.py extraction (5f7117f)** — Agent: **widget-specialist**. (Carried)
- [ ] **QA widget_chat_helpers shim removal (d2ab107)** — Agent: **backend-dev**. (Carried)
- [ ] **QA widget_helpers god-class split (6cf4646)** — Agent: **widget-specialist**. (Carried)
- [ ] **QA conftest TESTING + JWT secret env fix (9812fee, 0d94833)** — Agent: **qa-tester**. (Carried)
- [ ] **QA business-type personalization (ad88397)** — Agent: **qa-tester**. (Carried)
- [ ] **QA launch risk guardrails (99f8442)** — Agent: **qa-tester**. (Carried)
- [ ] **QA service-layer extraction** — `ff293f4`. Agent: **qa-tester**. (Carried)
- [ ] **QA scheduled_jobs.py split** — 5 modules. Agent: **qa-tester**. (Carried)
- [ ] **QA Stripe marketing addon readiness guard** — `0278eb0` + `0482f7d`. Agent: **qa-tester**. (Carried)
- [ ] **Act on launch-readiness rubric 114/262 NO-GO findings** — (Carried)
- [ ] **QA tenant_scope adoption + CORS fix** — Agent: **qa-tester**. (Carried)
- [ ] **QA industry packs** — `881e026`. Agent: **qa-tester**. (Carried)
- [ ] **QA marketing infrastructure** — Agent: **qa-tester**. (Carried)
- [ ] **QA Managed Agents integration** — Agent: **qa-tester**. (Carried)
- [ ] **QA issue-to-pr loop + autopilot loop** — `777af3a` + `5ddbbce`. Agent: **qa-tester**. (Carried)
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue`. Agent: **devops**. (Carried)
- [ ] **Ingest competitor briefs to KB** — 5 briefs + new `ghl-voice-ai-review-2026.md` (untracked). Manual `/kb-ingest` + `/kb-compile`. (Updated 2026-04-29)
- [ ] **Exercise migration duplicate-number pre-commit guard (2a08588)** — verified once via 117 collision; revisit. Agent: **devops**. (Updated 2026-04-29)

### Priority 2 — Code Quality & Verification

- [ ] **Reconcile silent_frontend_catch_count glob drift** — (Carried)
- [ ] **Fix 3 non-admin silent `.catch(() => null)` patterns** — Agent: **frontend-dev**. (Carried)
- [ ] **Implement JS silent catch pre-commit guard** — Agent: **devops**. (Carried)
- [ ] **Validate 47 rewritten skills** — `b83577f` + `0f1d23a`. (Carried)
- [ ] **E2E test onboarding wizard** — now relevant given `c7c74f1` route + `62f8722` soft edges. Agent: **qa-tester** + **frontend-dev**. (Updated 2026-04-29)
- [ ] **Verify expired JWT token handling (6d10cf5)** — (Carried)
- [ ] **Production verification of March 25 features** — **35+ days unverified.** (Carried)
- [ ] **Audit `.get() or ""` operator precedence pattern** — (Carried)
- [ ] **QA GitHub autopilot loop** — `5ddbbce`. Agent: **qa-tester**. (Carried)
- [ ] **Remove remaining 5 MTOptions references** — (Carried)
- [ ] **Remove MTOptions-growth from daily smoke tests** — (Carried)

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich bug pattern for `ee4bc16`** — slowapi callable signature fix. Auto-logged 2026-04-29. Run `/log-bug` for root-cause + prevention detail. (New 2026-04-29)
- [ ] **Enrich bug pattern for `fb57995`** — idempotency race + RLS + XFF. Auto-logged 2026-04-29. (New 2026-04-29)
- [ ] **Compile `knowledge-base/wiki/competitors/ghl-voice-ai-review-2026.md`** — untracked file in working tree; `/kb-compile`. (New 2026-04-29)
- [ ] **Enrich bug patterns from origin/main 2026-04-23 CI batch** — `4d9b25f`, `bcaba73`, `dbdcb23`, `212e04d`. (Carried)
- [ ] **Enrich bug pattern for `fac6124`** — (Carried)
- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeletons. (Carried since 2026-03-24)
- [ ] **Enrich bug patterns (#58-69)** — 12 skeletons from Apr 7-8. (Carried)
- [ ] **Enrich bug patterns (#72-78)** — 7 skeletons from Apr 9 evening. (Carried)
- [ ] **Enrich bug pattern for `9d48907`** — (Carried)
- [ ] **Enrich bug patterns for `0278eb0` + `9febf89`** — (Carried)
- [ ] **Enrich bug pattern for `c0aef59`** — (Carried)
- [ ] **Enrich bug pattern for `080098b`** — (Carried)
- [ ] **Act on vertical-specialize research findings (`e3963c5`)** — (Carried)
- [ ] **Act on earlier research findings** — CAC/churn, plateau, unit economics. (Carried)
- [ ] **Review 4 new research briefs (2026-04-18/19/20)** — (Carried)
- [ ] **Compile / ingest 2026-04-18 competitor landscape snapshot (`fd6a09e`)** — (Carried)

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — pending 6+ weeks.
- [ ] **Fix 16 test isolation failures** — partially addressed.
- [ ] **Automated routine reliability** — Apr 17 morning log showed `git pull` failed on detached HEAD. Verify auto-reattach.
- [ ] **Create migration-gate hook** — Block new feature commits when pending migration count > 15.
- [ ] **Split bug-patterns.md** — now ~2,300 lines, 198 ### entries. Hot file. (Updated 2026-04-29)
- [ ] **Codify widget 3-way sync check as skill** — (Carried)
- [ ] **Monitor `managed_agents_registry.py` for god-class trajectory** — (Carried)
- [ ] **Tighten `auto-commit.sh` debounce** — (Carried)
