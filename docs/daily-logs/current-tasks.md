# Current Task Backlog — AgentNexLiFy

Updated: 2026-04-03 (automated morning startup)

## Today's Top 3 Priorities

1. **Apply migrations 077, 078, and 079** — Migration 077 (widget knowledge_base) blocks onboarding wizard KB injection. Migration 078 (expanded business_type CHECK) blocks new signups for 17 industries. Migration 079 (wizard_events) blocks wizard drop-off analytics. All are **critical pre-launch gates**. Created 2026-04-01, still pending. Agent: **schema-guardian** → apply all three via Supabase MCP.
2. **End-to-end test onboarding wizard** — 15 commits shipped the full 6-step wizard (2026-04-01). Needs QA: real signup flow through all 6 steps, JWT parsing race condition, /onboarding route guard, KB generation, widget embed code. Agent: **qa-tester**.
3. **Apply pending migrations 065–070** — 6 stale migrations blocking client login (065), waitlist (066), scoring configs (067), invoice unique index + password reset (068 x2), email bounce (069), pipeline automations (070). Now 11+ days stale. Duplicate file issues at 066, 067, 068 need resolution first. Agent: **schema-guardian**.

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
- [ ] **Production verification of March 25 features** — Revenue analytics, pipeline automations, webhook deliveries, password reset flow: **9+ days unverified.** Agent: **qa-tester**.
- [ ] **Audit `.get() or ""` operator precedence pattern** — 3 occurrences fixed (birthday greetings, widget_chat, widget_config). Same pattern likely exists elsewhere. Run: `grep -rn '\.get(.*) or .*==' backend/`. Agent: **qa-tester**.
- [ ] **Reduce silent frontend catches (4 truly silent, 62 total)** — 4 empty `.catch(() => {})` blocks: onboarding.js, ClientLoginPage.jsx, MarketingCampaignsPage.jsx, WizardStepEmbed.jsx. Architecture decision requires visible error handling. Agent: **frontend-dev**.

### Priority 3 — Knowledge & Documentation

- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries need human enrichment for root cause details. Carried forward since 2026-03-24.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures
- [ ] **Automated routine reliability** — March 26 evening and March 27 morning both failed due to usage limits. Consider scheduling adjustments or retry mechanism.

## Completed (Recent) — 2026-04-03 (Morning Auto)

- [x] **4 bug fixes documented in bug-patterns.md** — IDOR in auto_populate_kb, operator precedence in restaurant check, widget CSS visibility, null-state guard.
- [x] **Daily log created** — docs/daily-logs/2026-04-03.md with health check results.

## Completed (Recent) — 2026-04-02

- [x] **Migration 080 applied** — conversations RLS policies + unique constraint (f18faa5)
- [x] **MTOptions chatbot audit** — RLS root cause, spam filter, knowledge base, lead capture (f18faa5)
- [x] **Security + operator precedence bugs fixed** — IDOR, `.get() or ""` in 2 files (4f0eec9)
- [x] **Widget desktop visibility fixed** — CSS `!important` overrides for host page compatibility (f16789e)
- [x] **Null-state guard added** — graceful fallback when tenant has no KB/custom instructions (4fd5cab)
- [x] **Auto-KB frontend + share results modal** — (7a73c1b)
- [x] **Widget live badge + lead captured badge + weekly digest email** — (26c3c31)
- [x] **Auto-KB from URL endpoint + tester results snapshot API** — (d0f0124)
- [x] **Multi-model coding agent setup** — Aider + Qwen 3.6 Plus (30945c9)

## Overall Progress

- 9 commits in last 24 hours (4 fixes, 3 features, 1 docs, 1 tooling)
- 3 pending migrations (077-079) — critical pre-launch blockers (unchanged from yesterday)
- 6 stale migrations (065-070) — 11+ days old, duplicates need resolution
- 4 silent frontend catches to fix
- 0 bare excepts, 0 dangerous imports, 0 hardcoded keys
- Widget files in sync
- **Hot zone:** widget_chat.py, widget_helpers.py, widget JS files — highest change velocity

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
