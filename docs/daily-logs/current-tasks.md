# Current Task Backlog — AgentNexLiFy

Updated: 2026-03-23 (automated morning routine)

## Top 3 Priorities

1. **Apply migration 065 to live Supabase** — client_accounts table blocking client login in production
2. **Silent frontend catch in ClientLoginPage.jsx** — `.catch(() => {})` hides errors on business name fetch
3. **Verify 30+ features in production** — massive feature velocity (Cycles 154-167) needs production validation

## Active Tasks

### Priority 1 — Critical / Blocking

- [ ] **Apply migration 065 (client_accounts)** — white-label client login (Cycle 163) depends on this table existing in production. Schema-log.md shows "Pending". Use Supabase MCP or SQL editor.
  - Agent: **schema-guardian** → manual apply

### Priority 2 — Code Quality

- [ ] **Fix silent catch in ClientLoginPage.jsx:25** — `.catch(() => {})` on business name fetch. Should at minimum log the error. Health check script doesn't catch this (regex difference).
  - Agent: **frontend-dev**
- [ ] **Production feature verification** — Cycles 154-167 added: client login, AI-to-human handoff, QR codes, competitor analysis, scheduled post auto-publish, dynamic booking placeholders. None verified in production.
  - Agent: **qa-tester**

### Priority 3 — Documentation Gaps

- [x] Document Cycle 156 bug fix (silent except-pass in pipeline seeding) — added to bug-patterns.md
- [x] Document Cycle 159 bug fix (N+1 in CSV import) — added to bug-patterns.md

### Priority 4 — Improvements

- [ ] **Two-way email sync** — still pending from previous backlog
- [ ] **Fix 16 test isolation failures** — carried forward from previous backlog

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
- 7 migrations (059-065), 7 simulations
- 35 api domain modules (100% split complete)
- 15+ features shipped, 10+ bug fixes, 5+ security patches

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
