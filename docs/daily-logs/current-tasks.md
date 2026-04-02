# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-01 (automated evening review)

## Tomorrow's Top 3 Priorities

1. **Apply migrations 077 and 078** — Migration 077 (widget knowledge_base) blocks the onboarding wizard from injecting knowledge into the chat prompt. Migration 078 (expanded business_type CHECK) blocks new signups for 17 industries. Both are **critical pre-launch gates** for the onboarding wizard. Agent: **schema-guardian** → apply both via Supabase MCP.
2. **End-to-end test onboarding wizard** — 15 commits shipped the full 6-step wizard today. Needs a real signup run through all 6 steps: business info → services → KB generation → widget customize → plan → embed. Verify JWT is set correctly, /onboarding route doesn't bounce, widget embed code works. Agent: **qa-tester**.
3. **Apply pending migrations 065–070** — 6 stale migrations blocking client login (065), waitlist (066), scoring configs (067), invoice unique index + password reset (068 ×2), email bounce (069), pipeline automations (070). Now 9+ days stale. Agent: **schema-guardian**.

## Active Tasks

### Priority 0 — Schema (Critical / Pre-Launch Blocker)

- [ ] **Apply migration 077 (widget knowledge_base)** — adds `knowledge_base` column to `widget_configs`. Required for onboarding wizard KB injection into chat prompt. Created 2026-04-01. Agent: **schema-guardian** → apply immediately.
- [ ] **Apply migration 078 (business_type constraint)** — expands CHECK constraint from 10 → 27 industries. New signups for accounting, bakery, bar_nightclub, etc. will fail at DB insert until this is applied. Created 2026-04-01. Agent: **schema-guardian** → apply immediately.

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

- [ ] **End-to-end test onboarding wizard** — 6-step wizard shipped today (WizardStepBusiness → Services → KB → Customize → Plan → Embed). Needs QA: real signup flow, JWT parsing race condition, /onboarding route guard, KB generation, widget embed code. Agent: **qa-tester**.
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset flow: **7+ days unverified.** Agent: **qa-tester**.
- [ ] **Reduce silent frontend catches (33 remaining)** — `.catch(() => <fallback>)` blocks detected by grep. Architecture decision requires visible error handling. Count steady at 33.
  - Agent: **frontend-dev**
- [ ] **Fix silent catch in ClientLoginPage.jsx:25** — `.catch(() => {})` on business name fetch. Still present.
  - Agent: **frontend-dev**

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries need human enrichment for root cause details. Carried forward since 2026-03-24.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed due to usage limits. Consider scheduling adjustments or retry mechanism.

## Completed (Recent) — 2026-04-01

- [x] **Onboarding wizard built end-to-end** — 6 step components (WizardStepBusiness, Services, KnowledgeBase, Customize, Plan, Embed), wizard shell with sessionStorage state, API helpers (generateKb, completeOnboarding, checkoutForWizard), /onboarding route with auth-race guard (OnboardingRedirect), billing checkout conditional success_url, generate-kb endpoint, KB injection into widget chat system prompt.
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
- [x] **Migration 077 created** — adds knowledge_base column to widget_configs. Apply pending.

## Completed (Recent) — 2026-03-31

- [x] **Migration 073 created and applied** — `migrations/073_email_sequences.sql` creates 4 tables: `email_sequences`, `email_sequence_steps`, `email_sequence_enrollments`, `email_sequence_sends`. Schema-log.md updated.
- [x] **Email sequences feature built** — backend router, frontend page, API utils, and seed script created for MTOptions. Now committed.
- [x] **Migrations 071 and 072 applied** — Widget teaser message (071) and custom_instructions (072) both applied and documented in schema-log.md. MTOptions custom system prompt configured.

## Completed (Recent) — 2026-03-30

- [x] **fix: markdown rendering, analytics 0 count, teaser bubble, lead capture prompting** (2944381)
- [x] **fix: correct AgentNexLiFy widget API key in index.html** (097cb62)
- [x] **feat: re-embed marketing widget (desktop only) and fix floating CTA arrow** (827ab4f)
- [x] **fix: remove fake testimonials and self-hosted chat widget from marketing site** (b153fc2)
- [x] **fix: update mobile CTA text** (36951b6)

## Overall Progress (Cycles 116-167+)

- 96+ commits today alone (running total 70+ previously), 299 tests
- 9 migrations applied this cycle (073-076, +073 previously), 4 pending (077, 078, 065-070 backlog)
- 35 api domain modules (100% split complete)
- 20+ features shipped, 15+ bug fixes, 5+ security patches
- **Today's landmark: onboarding wizard complete (6 steps, end-to-end)**

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
