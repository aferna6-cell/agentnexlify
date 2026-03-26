# Current Task Backlog — AgentNexLiFy

Updated: 2026-03-25 (automated evening review)

## Tomorrow's Top 3 Priorities

1. **Apply migrations 065-070 to live Supabase** — 6 pending migrations (065 client_accounts, 066 waitlist, 067 scoring_configs, 068 invoice unique + password reset, 069 email bounce, 070 pipeline automations). 065 blocks client login. Note: 068 has duplicate numbers — renumber before applying.
2. **Reduce silent frontend catches (29 remaining)** — Health check shows 29 silent `.catch(() => {})` blocks. Systematic cleanup needed per architecture decision on visible error handling.
3. **Production verification of today's features** — Revenue analytics, pipeline automations, webhook deliveries, password reset flow — all committed but none verified on production.

## Active Tasks

### Priority 1 — Critical / Blocking

- [ ] **Apply migration 065 (client_accounts)** — white-label client login depends on this table. Schema-log.md shows "Pending".
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 066 (waitlist_entries)** — appointment waitlist feature. Created 2026-03-23, not yet applied.
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 067 (scoring_configs)** — lead scoring config feature. Created 2026-03-23, not yet applied.
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 068 (invoice unique + password reset)** — DUPLICATE NUMBER: 068_invoice_number_unique.sql and 068_password_reset_tokens.sql. Renumber one before applying.
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 069 (lead email bounced)** — email bounce handling. Created 2026-03-25, not yet applied.
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 070 (pipeline automations)** — pipeline stage automations. Created 2026-03-25, not yet applied.
  - Agent: **schema-guardian** → manual apply

### Priority 2 — In-Progress Features

- [ ] **Reduce silent frontend catches** — 29 silent `.catch(() => {})` blocks detected by health check. Architecture decision requires visible error handling.
  - Agent: **frontend-dev**
- [ ] **Fix silent catch in ClientLoginPage.jsx:25** — `.catch(() => {})` on business name fetch. Still present.
  - Agent: **frontend-dev**

### Priority 3 — Verification

- [ ] **Production feature verification** — Revenue analytics, pipeline automations, webhook deliveries, password reset, CTO review fixes. All committed today, none production-verified.
  - Agent: **qa-tester**
- [ ] **Enrich auto-logged bug patterns (#30-41)** — 12 skeleton entries need human enrichment for root cause details. 6 from 2026-03-24, 6 new from 2026-03-25.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures

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

## Completed (Recent) — 2026-03-24

- [x] **Evening knowledge base update** — 6 bug pattern entries (#30-35) added for 3 fix commits from 2026-03-23

## Overall Progress (Cycles 116-167+)

- 65+ commits, 299 tests
- 7 migrations (059-065) + 5 new pending (066-070, with 068 duplicate), 7 simulations
- 35 api domain modules (100% split complete)
- 20+ features shipped, 15+ bug fixes, 5+ security patches

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
