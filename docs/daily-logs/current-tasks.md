# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-08 (automated evening review)

## Tomorrow's Top 3 Priorities

1. **Rotate compromised admin API key in Railway** — DAY 4 of exposure. Key committed in 9c87335, scrubbed in d4463d7. Still live in Railway. Agent: **devops** / Human action required.
2. **Apply migrations 097-098** — Required for today's new features (daily briefing, no-show recovery, pre-chat form). Also apply 090 (autopilot plan) and 093 (RLS fix). Agent: **schema-guardian**.
3. **Stabilization day** — Zero new features. Focus on QA, migration apply, and verifying today's 27-commit batch. Agent: **qa-tester**.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key committed in 9c87335, scrubbed in d4463d7. Key is still live. DAY 4 of exposure — **CRITICAL**. Agent: **devops** / Human. (Carried from Apr 6)

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [ ] **Apply migration 090 (autopilot plan)** — autopilot subscriptions fail at DB level. Created 2026-04-06.
- [ ] **Apply migration 093 (fix RLS policies)** — migration 091's auth.uid() policies are semantically broken. Created 2026-04-07.
- [ ] **Apply migrations 097-098** — no-show recovery columns, daily briefing toggles, pre-chat form. Created 2026-04-08.
- [ ] **Apply migrations 094-096 (schema reconciliation + hardening)** — Production columns, conversation memory, FK canonicalization. Created 2026-04-07.
- [ ] **Apply migrations 077-079 (onboarding blockers)** — Blocks wizard for new signups. Created 2026-04-01.

### Priority 1 — Critical / QA

- [ ] **QA tenant_scope.py end-to-end** — Centralized tenant scoping touching 20+ routers. Bug = cross-tenant leak. Agent: **qa-tester**.
- [ ] **QA marketing infrastructure** — A/B tests, automation rules, marketing dashboard. Zero QA. Agent: **qa-tester**.
- [ ] **Verify security fixes (2ab39dd, d7572eb, e2dbf36, 29aca88)** — 25+ security patches. Agent: **qa-tester**.
- [ ] **QA today's fix batch (91b98d3, cd1c6fc, 849943f)** — 11+ bug fixes, race condition fix, route shadowing fix. Agent: **qa-tester**.
- [ ] **Extend pre-commit hook** — Flag `except Exception: pass` and `except Exception: continue` (not just bare `except:`). Agent: **devops**.

### Priority 2 — Verification & Batch Migration

- [ ] **Apply migrations 083-092** — waitlist, scoring configs, password reset, A/B tests, automation rules, campaign analytics, admin tracking, reminder tracking. Agent: **schema-guardian**.
- [ ] **Apply migrations 065-070** — client_accounts, waitlist(old), scoring_configs(old), invoice unique, email bounce, pipeline automations. 14+ days stale.
- [ ] **E2E test onboarding wizard** — 6-step wizard shipped 2026-04-01. Needs QA.
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset: **14+ days unverified.**
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries still need human enrichment. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-69)** — 12 skeleton entries from Apr 7-8 fix commits. Need root cause details.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog (3+ weeks)
- [ ] **Fix 16 test isolation failures** — partially addressed, may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed; April 6 morning did not run.

## Completed (Recent) — 2026-04-08

- [x] **Morning health check** — all clear
- [x] **Daily log created** — docs/daily-logs/2026-04-08.md
- [x] **6 fix commits landed** — route shadow, unawaited async, Railway build, race condition, CSV mapping, 22+ swallowed exceptions
- [x] **2 feature commits** — daily briefing SMS + no-show recovery sequences; recovery stats dashboard + settings toggles + pre-chat form builder
- [x] **27 backend tests added** — auth, widget, booking, tenant isolation, schema integration
- [x] **E2E smoke tests added** — widget revenue path
- [x] **Dead code sweep** — removed 3 services + 30 unused API functions
- [x] **Vendor chunk extraction** — xyflow + dompurify split into cacheable chunks (build 5.22s → 4.66s)
- [x] **CLAUDE.md refactored** — split into 9 path-scoped rules files
- [x] **Standards plugin created** — AgentNexLiFy plugin with security reviewer, tenant check, widget sync skills
- [x] **Sentry error monitoring added** — integrated in main.py (needs SENTRY_DSN env var)
- [x] **Migrations 097-098 created** — no-show recovery tracking + daily briefing toggles + pre-chat form config
- [x] **Bug patterns #64-69 documented** — evening auto-log
- [x] **Schema-log updated** — migrations 097-098 documented
- [x] **Evening review completed** — health check, knowledge base, task backlog

## Overall Progress (2026-04-08 Evening)

- **Today's commits:** 27 (high-churn day #2)
- **Files changed:** 180 unique files
- **Fix commits:** 6 (route shadow, async, Railway, race condition, mapping, exceptions)
- **Features shipped:** Daily briefing SMS, no-show recovery, recovery stats dashboard, pre-chat form builder, settings toggles
- **Tests added:** 27 backend + E2E smoke tests (coverage was near-zero before today)
- **Health check:** All green (0 dangerous imports, 0 bare excepts, widget sync OK, build PASS 4.66s)
- **Pending migrations:** 24 (was 22, +2 new, 0 applied)
- **Bug patterns:** 69 total (6 new today)
- **SECURITY INCIDENT DAY 4:** admin API key — rotate in Railway immediately
- **Frontend build:** PASS (4.66s, improved from 5.22s)
- **Widget sync:** OK

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
