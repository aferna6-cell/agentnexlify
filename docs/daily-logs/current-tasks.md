# Current Task Backlog — AgentNexLiFy

Updated: 2026-03-31 (automated evening review)

## Tomorrow's Top 3 Priorities

1. **Commit the email sequences feature** — 5 new files + 7 modified files are ready to commit. Migration 073 already applied to Supabase. `git add backend/routers/email_sequences.py frontend/src/pages/EmailSequencesPage.jsx frontend/src/utils/api/email-sequences.js migrations/073_email_sequences.sql scripts/seed_mtoptions_sequences.py` + modified files, then commit. Agent: **None needed** — straightforward commit.
2. **Apply pending migrations 065–070** — 6 migrations stale since 2026-03-23/25, blocking client login (065), waitlist (066), scoring configs (067), invoice unique index + password reset (068 ×2, renumber required), email bounce (069), pipeline automations (070). **NEW duplicate filenames on 066 and 067.** Stale 7–8 days. Agent: **schema-guardian**.
3. **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook delivery, password reset flow: **7 days unverified.** Agent: **qa-tester**.

## Active Tasks

### Priority 0 — Uncommitted Work (Needs Commit)

- [ ] **Commit email sequences feature** — Migration 073 applied to Supabase; backend router (`email_sequences.py`), frontend page (`EmailSequencesPage.jsx`), API utils (`email-sequences.js`), seed script (`seed_mtoptions_sequences.py`), and modified files (main.py, App.jsx, Sidebar.jsx, widget_lead.py, api/index.js, CLAUDE.md) all uncommitted. Risk: work lost on branch change or reset. Added: 2026-03-31.

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

### Priority 2 — Verification & In-Progress

- [ ] **Production feature verification** — Revenue analytics, pipeline automations, webhook deliveries, password reset, CTO review fixes. All committed 2026-03-25, none production-verified. **7 days stale.**
  - Agent: **qa-tester**
- [ ] **Reduce silent frontend catches (33 remaining)** — `.catch(() => <fallback>)` blocks detected by grep. Architecture decision requires visible error handling. Count steady at 33.
  - Agent: **frontend-dev**
- [ ] **Fix silent catch in ClientLoginPage.jsx:25** — `.catch(() => {})` on business name fetch. Still present.
  - Agent: **frontend-dev**

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries need human enrichment for root cause details. 6 from 2026-03-24, 6 new from 2026-03-25. Carried forward since 2026-03-24.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed due to usage limits. Consider scheduling adjustments or retry mechanism.

## Completed (Recent) — 2026-03-31

- [x] **Migration 073 created and applied** — `migrations/073_email_sequences.sql` created and applied to Supabase (mcp__supabase__apply_migration). Creates 4 tables: `email_sequences`, `email_sequence_steps`, `email_sequence_enrollments`, `email_sequence_sends`. Schema-log.md updated.
- [x] **Email sequences feature built** — backend router, frontend page, API utils, and seed script created for MTOptions. Uncommitted but complete.
- [x] **Migrations 071 and 072 applied** — Widget teaser message (071) and custom_instructions (072) both applied and documented in schema-log.md. MTOptions custom system prompt configured.

## Completed (Recent) — 2026-03-30

- [x] **fix: markdown rendering, analytics 0 count, teaser bubble, lead capture prompting** (2944381) — Analytics now counts unique session_ids in chat_messages; widget + dashboard render AI responses as formatted HTML; greeting teaser bubble added; lead capture prompt improved
- [x] **fix: correct AgentNexLiFy widget API key in index.html** (097cb62) — Transposed characters in API key caused fallback to "Aria" bot name
- [x] **feat: re-embed marketing widget (desktop only) and fix floating CTA arrow** (827ab4f) — Marketing site widget restored with proper embed
- [x] **fix: remove fake testimonials and self-hosted chat widget from marketing site** (b153fc2) — Integrity fix; widget now uses configured greeting_message
- [x] **fix: update mobile CTA text** (36951b6) — Text copy update

## Completed (Recent) — 2026-03-25

- [x] **Codebase audit and critical fixes** (bcb5857) — Stripe dynamic checkout, SMS import fix, crawl exception sanitization, 4 ADRs, model selection docs
- [x] **Pre-feature audit** (3b7846d) — 16 new tests (299 total), rate limit tightening, dead link removal, fake scarcity removal, API key redaction
- [x] **Production site bugs from CTO review** (712b80c) — Pipeline crash fix, Client Portal array guard, onboarding math, FAQ edit, 22 signup verticals
- [x] **CTO site review UX improvements** (0af2b74) — dashboard UX improvements
- [x] **Revenue analytics dashboard** (4b54064) — backend router + frontend page + API utils
- [x] **Rebase merge conflict resolution** (45271d5) — duplicate exports, missing webhook API functions, App.jsx merge
- [x] **Pipeline automations frontend** (e9945ee, 014f11e, 06d453c, f2ac4b9) — PipelineAutomationsPage, webhook delivery dashboard, sidebar nav
- [x] **Conversation assignment notification + appointment validation** (4cc6bc3, c0cbf0d) — revenue dashboard, appointment status validation
- [x] **Evening knowledge base update** — 6 bug patterns (#36-41), 4 schema-log entries (068b, 069, 070)

## Overall Progress (Cycles 116-167+)

- 70+ commits, 299 tests
- 7 migrations (059-065) + 5 new pending (066-070, with 066/067/068 all having duplicate filenames)
- 35 api domain modules (100% split complete)
- 20+ features shipped, 15+ bug fixes, 5+ security patches

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
