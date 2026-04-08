# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-07 (automated evening review)

## Tomorrow's Top 3 Priorities

1. **Apply pending migrations (090, 093-096, 077-079, 083-089, 091-092)** — 22 total pending. Priority order: 090 (autopilot plan — actively breaking), 093 (RLS fix — security), 094-096 (schema reconciliation + production hardening), 077-079 (onboarding blockers), 083-089 (batch), 091-092 (audit/reminders). Agent: **schema-guardian**.
2. **Rotate compromised admin API key in Railway** — Key committed in 9c87335, scrubbed in d4463d7. Still live in Railway. Security incident — NOW. Agent: **devops**.
3. **QA tenant scoping + security hardening** — 6 fix commits today touched 20+ backend files. Tenant_scope.py is new — verify it works end-to-end. Agent: **qa-tester**.

## Active Tasks

### Priority 0 — Security (Immediate Action Required)

- [ ] **ROTATE compromised API key in Railway** — Key committed in 9c87335, scrubbed in d4463d7. Key is still live. This is a security incident — rotate now. Agent: **devops**. (Carried from morning — still unresolved)

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [ ] **Apply migration 090 (autopilot plan)** — autopilot subscriptions fail at DB level. Created 2026-04-06. Agent: **schema-guardian** → apply immediately.
- [ ] **Apply migration 093 (fix RLS policies)** — migration 091's auth.uid() policies are semantically broken. Created 2026-04-07. Agent: **schema-guardian**.
- [ ] **Apply migration 094 (reconcile leads schema)** — 8 production columns without migration files. Created 2026-04-07. Agent: **schema-guardian**. NEW today.
- [ ] **Apply migration 095 (conversation memory)** — JSONB memory column for AI context continuity. Created 2026-04-07. Agent: **schema-guardian**. NEW today.
- [ ] **Apply migration 096 (production hardening)** — client_id FK canonicalization, automation locks, durable email quotas, OAuth state nonces. Created 2026-04-07. Agent: **schema-guardian**. NEW today.
- [ ] **Apply migration 077 (widget knowledge_base)** — blocks onboarding wizard KB injection. Created 2026-04-01.
- [ ] **Apply migration 078 (business_type constraint)** — blocks new signups for 17 industries. Created 2026-04-01.
- [ ] **Apply migration 079 (wizard_events)** — blocks wizard funnel analytics. Created 2026-04-01.

### Priority 1 — Critical / Blocking

- [ ] **Apply migrations 083-092** — waitlist, scoring configs, password reset, A/B tests, automation rules, campaign analytics, admin tracking, reminder tracking, autopilot plan, RLS guards. Agent: **schema-guardian**.
- [ ] **Apply migrations 065-070** — client_accounts, waitlist(old), scoring_configs(old), invoice unique, email bounce, pipeline automations. 16+ days stale. Agent: **schema-guardian**.
- [ ] **QA tenant-scoped data access guardrails** — New `tenant_scope.py` service + hardening across 20+ routers (commits 156f5e7, 68a77df). Verify no regressions. Agent: **qa-tester**. NEW today.
- [ ] **QA marketing infrastructure (shipped 2026-04-06)** — A/B testing, automation rules, marketing dashboard, weekly growth endpoint. Zero QA so far. Agent: **qa-tester**.
- [ ] **Verify security fixes (2ab39dd + d7572eb + e2dbf36 + 29aca88)** — 25+ security/data integrity issues patched. Check for regressions. Agent: **qa-tester**.

### Priority 2 — Verification & QA

- [ ] **End-to-end test onboarding wizard** — 6-step wizard shipped 2026-04-01. Needs QA. Agent: **qa-tester**.
- [ ] **Verify expired JWT token handling (6d10cf5)** — 401 interceptor + proactive expiry check added 2026-04-06. Agent: **qa-tester**.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset flow: **13+ days unverified.** Agent: **qa-tester**.
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 fixed, likely more. Agent: **qa-tester**.
- [ ] **Reduce silent frontend catches (4 truly silent)** — onboarding.js, ClientLoginPage.jsx, MarketingCampaignsPage.jsx, WizardStepEmbed.jsx. Agent: **frontend-dev**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries still need human enrichment. Carried since 2026-03-24.
- [ ] **Enrich bug patterns (#58-63) added today** — 6 new skeleton entries from today's fix commits. Need root cause details.
- [ ] **New patterns (#46-57) added this morning** — fully documented but may benefit from human review.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed; April 6 morning did not run. Consider scheduling adjustments.

## Completed (Recent) — 2026-04-07 (Evening Auto)

- [x] **Tenant-scoped data access guardrails** — New `tenant_scope.py` service created, 20+ routers hardened (156f5e7, 68a77df)
- [x] **Production security hardening** — config.py guards, email sender validation, booking/Facebook/widget hardening (29aca88)
- [x] **Comprehensive security hardening** — appointments schema, auth router, widget XSS fixes (e2dbf36)
- [x] **Migration 096 created** — client_id FK, automation locks, email quotas, OAuth nonces (29aca88, 738ba0b)
- [x] **Migration 095 created** — conversation memory JSONB column (0ab4dfc)
- [x] **Migration 094 created** — leads schema reconciliation, 8 missing columns (0ab4dfc)
- [x] **Phase 1-3 schema reconciliation + widget consolidation + tests** (0ab4dfc)
- [x] **Prompt library system** — reusable, versioned prompts for AI workflows (34e69f8)
- [x] **Skills standardized** — 52 SKILL.md files reformatted to universal format (ba359fc)
- [x] **PR #9 merged** — fix automation review risks (6374e62)
- [x] **Bug patterns #58-63 documented** — 6 new entries from today's fix commits
- [x] **Migrations 094-096 documented in schema-log.md**
- [x] **Evening health check run** — all clear

## Completed (Recent) — 2026-04-07 (Morning Auto)

- [x] **Morning health check run** — all clear (0 bare excepts, 0 dangerous imports, 0 TODO/FIXME, widget in sync, .env gitignored)
- [x] **12 new bug patterns documented (#46-57)** — overnight security audit commits fully documented
- [x] **Migration 093 documented in schema-log.md**
- [x] **Daily log created** — docs/daily-logs/2026-04-07.md

## Overall Progress (2026-04-07 Evening)

- **Today's commits:** 22 total (11 overnight documented in morning, 11 post-morning new work)
- **Files changed:** 164 unique files
- **Fix commits:** 6 post-morning (tenant scoping, security hardening, migration safety)
- **New migrations:** 3 (094, 095, 096) — total pending now 22
- **New bug patterns:** 6 (#58-63) + 12 (#46-57) from morning = 18 new patterns today
- **Hot zones:** tenant_scope.py (new, 2 commits), main.py (still high-churn), automation_engine.py (still high-churn)
- **0 bare excepts, 0 dangerous imports, 0 TODO/FIXME, 0 hardcoded keys**
- **4 silent frontend catches** (unchanged)
- **Widget files in sync** (identical content)
- **SECURITY INCIDENT STILL OPEN:** admin API key committed to .env.example — rotate in Railway immediately

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
