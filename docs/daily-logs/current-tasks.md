# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-13 (automated morning routine)

## Today's Top 3 Priorities

1. **ROTATE compromised admin API key in Railway** — DAY 10 of exposure. Key committed in 9c87335, scrubbed in d4463d7. Still live in Railway. Agent: **devops** / Human action required. **CRITICAL.**
2. **Apply migrations 077-101** — 25 pending migrations blocking features (autopilot plan, onboarding wizard, RLS fixes, no-show recovery, daily briefing, AI lead qualification, AI document drafting, widget AI fallback). Agent: **schema-guardian**.
3. **QA tenant_scope adoption + CORS fix in production** — 60+ routers touched, plus CORS now hardcoded to `["*"]`. Verify widget works on external customer domains. Agent: **qa-tester**.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key committed in 9c87335, scrubbed in d4463d7. Key is still live. DAY 10 of exposure — **CRITICAL**. Agent: **devops** / Human. (Carried from Apr 5)

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [ ] **Apply migration 090 (autopilot plan)** — autopilot subscriptions fail at DB level. Created 2026-04-06.
- [ ] **Apply migration 093 (fix RLS policies)** — migration 091's auth.uid() policies are semantically broken. Created 2026-04-07.
- [ ] **Apply migration 101 (widget AI fallback)** — enable_ai_fallback flag for support_agent escalation. Created 2026-04-10.
- [ ] **Apply migrations 097-098** — no-show recovery columns, daily briefing toggles, pre-chat form. Created 2026-04-08.
- [ ] **Apply migrations 099-100** — AI lead qualification fields, AI-drafted documents. Created 2026-04-09.
- [ ] **Apply migrations 094-096 (schema reconciliation + hardening)** — Production columns, conversation memory, FK canonicalization. Created 2026-04-07.
- [ ] **Apply migrations 077-079 (onboarding blockers)** — Blocks wizard for new signups. Created 2026-04-01.
- [ ] **Apply migrations 083-092** — waitlist, scoring configs, password reset, A/B tests, automation rules, campaign analytics, admin tracking, reminder tracking. Agent: **schema-guardian**.

### Priority 1 — Critical / QA

- [ ] **QA tenant_scope adoption + CORS fix** — 60+ routers touched in auto-commits + CORS now hardcoded `["*"]`. Verify widget on external customer domains. Cross-tenant leak = critical. Agent: **qa-tester**.
- [ ] **QA industry packs** — 14 new modules landed (881e026). No per-pack tests beyond base. Agent: **qa-tester**. (Apr 10)
- [ ] **QA marketing infrastructure** — A/B tests, automation rules, marketing dashboard. Zero QA. Agent: **qa-tester**.
- [ ] **Verify security fixes (2ab39dd, d7572eb, e2dbf36, 29aca88)** — 25+ security patches. Agent: **qa-tester**.
- [ ] **QA Apr 8-10 fix batch** — 18+ bug fixes across multiple commits (noshow cache, session_id, header injection, async blocking, hardcoded URLs, CORS, test transport). Agent: **qa-tester**.
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue` (not just bare `except:`). Agent: **devops**.
- [ ] **QA Managed Agents integration** — Lead qualification + document drafter + field monitor + researcher. Smoke tests pass but no production QA yet. Agent: **qa-tester**.
- [ ] **Ingest competitor briefs to KB** — 5 research briefs in `research-briefs/` need `/kb-ingest` to enter the wiki. Agent: manual.

### Priority 2 — Verification & Testing

- [ ] **Apply migrations 065-070** — client_accounts, waitlist(old), scoring_configs(old), invoice unique, email bounce, pipeline automations. 14+ days stale.
- [ ] **E2E test onboarding wizard** — 6-step wizard shipped 2026-04-01. Needs QA.
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset: **19+ days unverified.**
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more.
- [ ] **Review 8 silent .catch(() => null) patterns** — AdminAnalyticsPage (6), MarketingDashboardPage (1), LocalSEOPage (1). Health check now shows 0 — verify if fixed or if check changed.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries still need human enrichment. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-69)** — 12 skeleton entries from Apr 7-8 fix commits. Need root cause details.
- [ ] **Enrich bug patterns (#72-78)** — 7 skeleton entries from Apr 9 evening. Auto-logged, need human review.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog (3+ weeks)
- [ ] **Fix 16 test isolation failures** — partially addressed, may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed; April 6 morning did not run.
- [ ] **Create migration-gate hook** — Block new feature commits when pending migration count > 15. Suggested by evening review pattern analysis.

### Priority 5 — New (Apr 11-13)

- [ ] **QA GitHub autopilot loop** — `feat(autopilot)` landed (5ddbbce). PR review scripts + skill. Needs testing. Agent: **qa-tester**.
- [ ] **Validate 47 rewritten skills** — `b83577f` rewrote skills to match Anthropic canon. Spot-check critical skills still trigger correctly.
- [ ] **Implement JS silent catch pre-commit guard** — Subconscious run `365d6ea` recommended adding silent `.catch(() => {})` detection to pre-commit hook. Agent: **devops**.

## Completed (Recent) — 2026-04-11-13

- [x] **KB Karpathy wiki alignment** — auto-populate 2x/day cron (a23de42)
- [x] **KB lint skill** — validates articles against Karpathy template (66df82b)
- [x] **36 plugins installed** — routing rules documented in `.claude/rules/plugins.md` (5bc8e7e)
- [x] **47 skills rewritten** — aligned to Anthropic canon format (b83577f)
- [x] **4 plugin collisions fixed** — disabled duplicates of existing MCPs (e0aa0c2)
- [x] **GitHub autopilot loop** — P3 spec + implementation (b596364, 5ddbbce)
- [x] **Support email rename** — support@ → help@ across legal + contact pages (730d75b)
- [x] **KB auto-populate fixes** — cron race condition, CLI resolution, schema correction (67bb565, 5bda9b3)
- [x] **KB content** — 15+ new wiki articles (competitors, AI/LLM, regulations, technical)
- [x] **Subconscious run** — JS silent catch guard recommendation (365d6ea)

## Completed (Recent) — 2026-04-10

- [x] **Morning health check** — all green (0 dangerous imports, 0 bare excepts, widget sync OK, build PASS 4.45s)
- [x] **Fix: CORS env-driven origins broke widget** — 9b07a59 (bug #79). Hard-coded `allow_origins=["*"]`.
- [x] **Fix: FastAPI test transport deadlocks** — fd24b43. Replaced Starlette TestClient with httpx ASGITransport.
- [x] **Fix: 24+ test files patched for get_service_supabase rename** — 74be54a, d7d73f5, 9277c0e
- [x] **feat: Industry packs** — 14 industry-specific modules (salon, dental, HVAC, legal, medical, etc.) — 881e026
- [x] **feat: Managed agents** — router HTTP tests + field_monitor cron + 5 competitor briefs — b97928a
- [x] **5 competitor research briefs** — GoHighLevel, Drillbit, Birdeye, Oscar Chat, Phonely

## Overall Progress (2026-04-13 Morning)

- **Last commit:** 1360063 (kb log append, 2026-04-13 06:15)
- **Codebase status:** Clean (git status clean)
- **Health check:** All green (widget sync OK, 0 bare excepts, 0 dangerous imports, 0 silent frontend catches)
- **Frontend build:** PASS (5.18s)
- **Bug patterns total:** 82 (+3 today: logger deprecation #80, env var mismatch #81, test client methods #82)
- **Pending migrations:** 25 (077-101, +1 since Apr 10: migration 101 widget AI fallback)
- **SECURITY INCIDENT DAY 10:** admin API key — rotate in Railway **IMMEDIATELY**
- **Key activity (Apr 11-13):** KB infrastructure (Karpathy wiki, auto-populate, lint), plugin/skill overhaul, GitHub autopilot loop
- **silent_frontend_catch_count:** 0 (was 8 on Apr 10 — verify if code was fixed or check was updated)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
