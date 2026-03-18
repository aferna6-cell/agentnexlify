# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Top Priorities (2026-03-18)

1. **Apply migrations 051-052 + commit Invoices & Pipeline** — uncommitted since March 17
2. **Fix automated morning/evening CLI path** — broken 2 days running

## Active Tasks

### Priority 0 — Immediate
- [ ] Apply migration 051 (invoices) to live Supabase
- [ ] Apply migration 052 (pipeline_stages) to live Supabase
- [ ] Commit Invoices + Pipeline work (~3,100 lines uncommitted)
- [ ] Update schema-log.md with migrations 051-052

### Priority 1 — Verify & Complete
- [ ] Verify Invoices page works end-to-end (CRUD, send, Stripe link)
- [ ] Verify Pipeline page works end-to-end (stages, board, drag-move)
- [ ] Add Invoices + Pipeline to sidebar navigation
- [ ] Wire bids-to-invoices auto-conversion
- [ ] Default pipeline seeding (industry-specific stages)
- [ ] Payment reminders for unpaid invoices

### Priority 2 — Infrastructure
- [ ] Fix automated morning/evening routine — Claude CLI not found in Task Scheduler PATH
- [ ] Verify older features still work in production (action items, shared inbox, snippets, chat flows)

### Priority 3 — Tier 6 Continued
- [ ] AI Business Insights — weekly intelligence brief
- [ ] Smart Lists — dynamic lead segments
- [ ] Form & Survey Builder

### Priority 4 — Existing Backlog
- [ ] Social media platform OAuth (direct posting)
- [ ] Real SERP data integration
- [ ] Add contract tests for api.js flows
- [ ] Configure Cloudflare Browser Rendering env vars

## Completed (Recent)

- [x] Invoices module — migration 051, backend router, frontend page (2026-03-17, uncommitted)
- [x] Pipeline module — migration 052, backend router, frontend page (2026-03-17, uncommitted)
- [x] Bug fixes: local_seo.py (UnboundLocalError, safer int parsing) (2026-03-17)
- [x] Bug fixes: marketing_campaigns.py (isolated status update) (2026-03-17)
- [x] UX polish — mobile sidebar, empty states, welcome email, no-response automation — Cycle 90 (2026-03-17)
- [x] Security: input validation + double-send protection — Cycle 89 (2026-03-17)
- [x] Tests: 10 tests for social media + marketing campaigns — Cycle 89 (2026-03-17)
- [x] SEO audit hub, social media marketing, campaign blasts — Cycle 88 (2026-03-17)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
