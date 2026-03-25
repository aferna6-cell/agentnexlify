# Current Task Backlog — AgentNexLiFy

Updated: 2026-03-24 (automated evening review)

## Tomorrow's Top 3 Priorities

1. **Apply migrations 065-067 to live Supabase** — client_accounts (065), waitlist_entries (066), scoring_configs (067) are all pending. 065 blocks client login in production.
2. **Complete and commit Revenue Analytics feature** — backend router, frontend page, and API util are written but uncommitted. Wire up and test.
3. **Fix silent catch in ClientLoginPage.jsx:25** — `.catch(() => {})` still present despite being flagged. Health check regex doesn't detect it.

## Active Tasks

### Priority 1 — Critical / Blocking

- [ ] **Apply migration 065 (client_accounts)** — white-label client login depends on this table. Schema-log.md shows "Pending". Use Supabase MCP or SQL editor.
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 066 (waitlist_entries)** — appointment waitlist feature. Created 2026-03-23, not yet applied.
  - Agent: **schema-guardian** → manual apply
- [ ] **Apply migration 067 (scoring_configs)** — lead scoring config feature. Created 2026-03-23, not yet applied.
  - Agent: **schema-guardian** → manual apply

### Priority 2 — In-Progress Features

- [ ] **Revenue Analytics feature** — backend/routers/revenue.py, frontend RevenuePage.jsx, and API util created but uncommitted. Needs testing and commit.
  - Agent: **backend-dev** + **frontend-dev**
- [ ] **Fix silent catch in ClientLoginPage.jsx:25** — `.catch(() => {})` on business name fetch. Health check script regex mismatch means this isn't auto-detected.
  - Agent: **frontend-dev**

### Priority 3 — Verification

- [ ] **Production feature verification** — Cycles 154-167 added 14+ features, none production-verified.
  - Agent: **qa-tester**
- [ ] **Enrich auto-logged bug patterns (#30-35)** — 6 new skeleton entries added 2026-03-24. Need human enrichment for root cause details.

### Priority 4 — Carried Forward

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — partially addressed by d1a36c6 (12 files patched), may still have remaining failures

## Completed (Recent) — 2026-03-24

- [x] **Evening knowledge base update** — 6 bug pattern entries (#30-35) added for 3 fix commits from 2026-03-23

## Completed (Recent) — 2026-03-23

- [x] **Morning health check and review** — documented 21 commits from Cycles 147-167
- [x] **Bug patterns updated** — entries #28 (silent except-pass) and #29 (N+1 CSV import) added
- [x] **Schema-log updated** — migrations 066 and 067 documented
- [x] **Hero copy updated on Home.jsx** — more specific value prop
- [x] **FormBuilderPage em-dash cleanup** — replaced em-dashes with hyphens for consistency
- [x] **Pipeline crash fix** — 38fb69f (committed after evening review)
- [x] **4-bug fix** — 5e9abcc (stripe_webhooks, widget_chat, conversation.py FK, billing XSS)
- [x] **Test isolation fix** — d1a36c6 (12 test files patched)

## Completed Since Last Update (Cycles 147-167)

- [x] **api.js split: 100% complete** — all 257 functions in 35 domain modules, monolith deleted (Cycles 147-153)
- [x] **White-label client login** — client registration + login with portal token verification (Cycle 163)
- [x] **AI-to-human handoff** — seamless widget-to-team transfer (Cycle 161)
- [x] **Auto-publish scheduled posts/campaigns** — automation loop integration (Cycle 162)
- [x] **QR code generator** — downloadable QR codes for business page + booking links (Cycle 166)
- [x] **Competitor analysis dashboard** — AI-estimated SEO comparison (Cycle 167)
- [x] **Dynamic booking placeholder** — business-type-aware booking text (Cycle 160)
- [x] **Security hardening** — timing attack fix, form DoS protection, narrow public selects (Cycle 164)
- [x] **Performance** — N+1 fix in CSV import (Cycle 159), dead code sweeps (Cycles 155, 165)
- [x] **Legal compliance** — AI system prompt compliance block (Cycle 158)
- [x] **API consistency** — all pages using centralized API utils (Cycle 167)

## Overall Progress (Cycles 116-167)

- 52 commits, 85+ tests
- 7 migrations (059-065) + 2 new pending (066-067), 7 simulations
- 35 api domain modules (100% split complete)
- 15+ features shipped, 10+ bug fixes, 5+ security patches

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
