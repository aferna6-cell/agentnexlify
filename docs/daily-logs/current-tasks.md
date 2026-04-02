# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-02 (automated morning startup)

## Today's Top 3 Priorities

1. **Apply migrations 077, 078, and 079** — Migration 077 (widget knowledge_base) blocks onboarding wizard KB injection. Migration 078 (expanded business_type CHECK) blocks new signups for 17 industries. Migration 079 (wizard_events) blocks wizard drop-off analytics. All are **critical pre-launch gates**. Agent: **schema-guardian** → apply all three via Supabase MCP.
2. **End-to-end test onboarding wizard** — 15 commits shipped the full 6-step wizard (2026-04-01). Needs a real signup run through all 6 steps: business info → services → KB generation → widget customize → plan → embed. Verify JWT is set correctly, /onboarding route doesn't bounce, widget embed code works. Agent: **qa-tester**.
3. **Apply pending migrations 065–070** — 6 stale migrations blocking client login (065), waitlist (066), scoring configs (067), invoice unique index + password reset (068 x2), email bounce (069), pipeline automations (070). Now 10+ days stale. Duplicate file issues at 066, 067, 068 need resolution first. Agent: **schema-guardian**.

## Active Tasks

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [ ] **Apply migration 077 (widget knowledge_base)** — adds `knowledge_base` column to `widget_configs`. Required for onboarding wizard KB injection into chat prompt. Created 2026-04-01. Agent: **schema-guardian** → apply immediately.
- [ ] **Apply migration 078 (business_type constraint)** — expands CHECK constraint from 10 → 27 industries. New signups for accounting, bakery, bar_nightclub, etc. will fail at DB insert until this is applied. Created 2026-04-01. Agent: **schema-guardian** → apply immediately.
- [ ] **Apply migration 079 (wizard_events)** — creates `wizard_events` table for onboarding funnel analytics. Created 2026-04-01. Agent: **schema-guardian** → apply immediately.

### Priority 1 — Critical / Blocking

- [ ] **Apply migration 065 (client_accounts)** — white-label client login depends on this table. Schema-log.md shows "Pending". Stale since 2026-03-23.
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 066 (waitlist_entries)** — DUPLICATE FILENAMES: `066_appointment_waitlist.sql` AND `066_waitlist.sql`. Verify they are identical, delete one, then apply. Created 2026-03-23.
  - Agent: **schema-guardian** → verify + manual apply
- [ ] **Apply migration 067 (scoring_configs)** — DUPLICATE FILENAMES: `067_lead_scoring_config.sql` AND `067_scoring_configs.sql`. Verify they are identical, delete one, then apply. Created 2026-03-23.
  - Agent: **schema-guardian** → verify + manual apply
- [ ] **Apply migration 068 (invoice unique + password reset)** — DUPLICATE NUMBER: `068_invoice_number_unique.sql` and `068_password_reset_tokens.sql`. Renumber one before applying.
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 069 (lead email bounced)** — email bounce handling. Created 2026-03-25, not yet applied.
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 070 (pipeline automations)** — pipeline stage automations. Created 2026-03-25, not yet applied.
  - Agent: **schema-guardian** → manual apply

### Priority 2 — Verification & QA

- [ ] **End-to-end test onboarding wizard** — 6-step wizard shipped 2026-04-01 (WizardStepBusiness → Services → KB → Customize → Plan → Embed). Needs QA: real signup flow, JWT parsing race condition, /onboarding route guard, KB generation, widget embed code. Agent: **qa-tester**.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset flow: **8+ days unverified.** Agent: **qa-tester**.
- [ ] **Reduce silent frontend catches (4 truly silent, 62 total)** — 4 empty `.catch(() => {})` blocks: onboarding.js, ClientLoginPage.jsx, MarketingCampaignsPage.jsx, WizardStepEmbed.jsx. 62 total `.catch` patterns across 35 files. Architecture decision requires visible error handling. Agent: **frontend-dev**.
- [ ] **Fix silent catch in ClientLoginPage.jsx:25** — `.catch(() => {})` on business name fetch. Still present. Agent: **frontend-dev**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries need human enrichment for root cause details. Carried forward since 2026-03-24.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed due to usage limits. Consider scheduling adjustments or retry mechanism.

## Completed (Recent) — 2026-04-02 (Morning Auto)

- [x] **Migration 079 documented in schema-log.md** — wizard_events table entry added.
- [x] **2 bug fixes documented in bug-patterns.md** — sidebar hide + analytics FK resolution.
- [x] **Daily log created** — docs/daily-logs/2026-04-02.md with health check results.

## Completed (Recent) — 2026-04-01

- [x] **Onboarding wizard built end-to-end** — 6 step components (WizardStepBusiness, Services, KnowledgeBase, Customize, Plan, Embed), wizard shell with sessionStorage state, API helpers (generateKb, completeOnboarding, checkoutForWizard), /onboarding route with auth-race guard (OnboardingRedirect), billing checkout conditional success_url, generate-kb endpoint, KB injection into widget chat system prompt.
- [x] **Wizard drop-off tracking** — migration 079, backend endpoint, frontend instrumentation (44f7553).
- [x] **5 industry vertical SEO pages enriched** — expanded content, FAQs, structured data (3df8437).
- [x] **Incomplete features hidden from sidebar** — social media, calls, local SEO (ff75a44).
- [x] **Email sequences feature committed** — backend router, frontend page, API utils, seed script, main.py router registration, sidebar nav (a3a2518). Migration 073 already applied.
- [x] **Email sequence auto-enrollment trigger fixed** — `_capture_leads_from_session` now calls enrollment trigger on lead capture (0fead79).
- [x] **lead_captured flag fixed** — `_capture_leads_from_session` now writes back `lead_captured=True` to conversations row (f90a40d). Migration 074 applied.
- [x] **Analytics tenant_id resolution fixed** — conversations.client_id FK was pointing to legacy `clients` table; migration 076 re-pointed it to `tenants`. Analytics now shows real data (87e6333).
- [x] **Widget teaser bubble added** — configurable teaser_message, teaser_enabled, teaser_delay_seconds. Migration 075 applied (3911049).
- [x] **Direct URL navigation fixed** — vercel.json catch-all + App.jsx route additions (b59d969).
- [x] **Post-signup UX bugs fixed** — post-signup redirect, widget on auth pages, industry options, api key mismatch, onboarding route guard (69a7744).
- [x] **Non-blocking bugs fixed** — UUID casting in response_metrics, Privacy/ToS pages real links, Schema.org placeholder removal (418d871).
- [x] **business_type CHECK constraint expanded** — 10 → 27 industries via migration 078. File created; apply pending.
- [x] **5 post-onboarding bugs documented** in bug-patterns.md (5597ed6).
- [x] **Demo script created** — client-ready feature walkthrough with Q&A cheat sheet (88e5ef8).
- [x] **Migrations 077 created** — adds knowledge_base column to widget_configs. Apply pending.

## Overall Progress

- 27 commits in last 24 hours
- 3 pending migrations (077-079) — critical pre-launch blockers
- 6 stale migrations (065-070) — 10+ days old, duplicates need resolution
- 4 silent frontend catches to fix
- 0 bare excepts, 0 dangerous imports, 0 hardcoded keys
- Widget files in sync

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
