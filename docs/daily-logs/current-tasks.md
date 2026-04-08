# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-08 (automated morning startup)

## Today's Top 3 Priorities

1. **Rotate compromised admin API key in Railway** — Day 3 of exposure. Key committed in 9c87335, scrubbed in d4463d7. Still live in Railway. Agent: **devops**.
2. **Apply critical migrations (090, 093-096)** — 090 blocks autopilot plan, 093 fixes broken RLS, 094-096 are schema reconciliation + production hardening. Agent: **schema-guardian**.
3. **QA tenant_scope.py end-to-end** — New centralized tenant scoping service touching 20+ routers. A bug here = cross-tenant data leak. Agent: **qa-tester**.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key committed in 9c87335, scrubbed in d4463d7. Key is still live. Day 3 of exposure — **CRITICAL**. Agent: **devops**. (Carried from Apr 6)

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [ ] **Apply migration 090 (autopilot plan)** — autopilot subscriptions fail at DB level. Created 2026-04-06. Agent: **schema-guardian** → apply immediately.
- [ ] **Apply migration 093 (fix RLS policies)** — migration 091's auth.uid() policies are semantically broken. Created 2026-04-07. Agent: **schema-guardian**.
- [ ] **Apply migration 094 (reconcile leads schema)** — 8 production columns without migration files. Created 2026-04-07. Agent: **schema-guardian**.
- [ ] **Apply migration 095 (conversation memory)** — JSONB memory column for AI context continuity. Created 2026-04-07. Agent: **schema-guardian**.
- [ ] **Apply migration 096 (production hardening)** — client_id FK canonicalization, automation locks, durable email quotas, OAuth state nonces. Created 2026-04-07. Agent: **schema-guardian**.
- [ ] **Apply migration 077 (widget knowledge_base)** — blocks onboarding wizard KB injection. Created 2026-04-01.
- [ ] **Apply migration 078 (business_type constraint)** — blocks new signups for 17 industries. Created 2026-04-01.
- [ ] **Apply migration 079 (wizard_events)** — blocks wizard funnel analytics. Created 2026-04-01.

### Priority 1 — Critical / Blocking

- [ ] **Apply migrations 083-092** — waitlist, scoring configs, password reset, A/B tests, automation rules, campaign analytics, admin tracking, reminder tracking, autopilot plan, RLS guards. Agent: **schema-guardian**.
- [ ] **Apply migrations 065-070** — client_accounts, waitlist(old), scoring_configs(old), invoice unique, email bounce, pipeline automations. 14+ days stale. Agent: **schema-guardian**.
- [ ] **QA tenant-scoped data access guardrails** — New `tenant_scope.py` service + hardening across 20+ routers (commits 156f5e7, 68a77df). Verify no regressions. Agent: **qa-tester**.
- [ ] **QA marketing infrastructure (shipped 2026-04-06)** — A/B testing, automation rules, marketing dashboard, weekly growth endpoint. Zero QA so far. Agent: **qa-tester**.
- [ ] **Verify security fixes (2ab39dd + d7572eb + e2dbf36 + 29aca88)** — 25+ security/data integrity issues patched. Check for regressions. Agent: **qa-tester**.

### Priority 2 — Verification & QA

- [ ] **End-to-end test onboarding wizard** — 6-step wizard shipped 2026-04-01. Needs QA. Agent: **qa-tester**.
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check added 2026-04-06. Agent: **qa-tester**.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset flow: **14+ days unverified.** Agent: **qa-tester**.
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more. Agent: **qa-tester**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries still need human enrichment. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-63) added Apr 7** — 6 new skeleton entries from Apr 7 fix commits. Need root cause details.
- [ ] **Patterns #46-57 added Apr 7 morning** — fully documented but may benefit from human review.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog (3+ weeks)
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed; April 6 morning did not run. Consider scheduling adjustments.

## Completed (Recent) — 2026-04-08 (Morning Auto)

- [x] **Morning health check run** — all clear (0 bare excepts, 0 dangerous imports, 0 silent catches, 0 TODO/FIXME, widget in sync, .env gitignored, frontend builds)
- [x] **Daily log created** — docs/daily-logs/2026-04-08.md
- [x] **Task backlog refreshed** — priorities updated, carried forward items retained

## Overall Progress (2026-04-08 Morning)

- **Overnight commits:** 0 (quiet night after high-churn day)
- **Health check:** All green — silent frontend catches dropped from 4 to 0
- **Pending migrations:** 22 (unchanged from yesterday evening — none applied, none created)
- **Bug patterns:** 63 total (all documented, 18 added yesterday)
- **Hot zones:** automation_engine.py (14 changes/7d), main.py (14), widget_helpers.py (10)
- **SECURITY INCIDENT DAY 3:** admin API key committed to .env.example — rotate in Railway immediately
- **Frontend build:** PASS (5.22s)
- **Widget sync:** OK

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
