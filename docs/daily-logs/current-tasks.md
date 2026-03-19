# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Tomorrow's Top 3 Priorities (2026-03-19)

1. **Verify new pages E2E** — Smart Lists, Forms, Invoices, Pipeline, CSAT (all built but untested end-to-end)
2. **Frontend build check** — 7 commits touched api.js and 4 touched App.jsx today; confirm Vercel build passes
3. **Social media OAuth** — next major feature gap (direct posting to Facebook/Instagram/LinkedIn)

## Active Tasks

### Priority 1 — Verify
- [ ] Verify Smart Lists page works E2E (create, filter, export CSV)
- [ ] Verify Forms page works E2E (create, embed, public submit, lead creation)
- [ ] Verify Invoices + Pipeline pages (carried forward)
- [ ] Verify CSAT page works E2E (new in Cycle 100)
- [ ] Verify public booking page (new in Cycle 96)
- [ ] Verify omnichannel inbox filtering (new in Cycle 98)
- [ ] Verify Facebook Messenger webhook flow (new in Cycle 99)

### Priority 2 — Remaining Backlog
- [ ] Social media platform OAuth (direct posting)
- [ ] Real SERP data integration (SEMrush/Ahrefs)
- [ ] Competitor analysis dashboard
- [ ] Automated social media posting scheduler
- [ ] Documents & E-Signatures (future Tier 6 item)

### Priority 3 — Quality
- [ ] Add contract tests for api.js flows
- [ ] Configure Cloudflare Browser Rendering env vars
- [ ] Verify older features in production
- [ ] Review hotspot files (api.js touched 7x, main.py 7x today — consider splitting)

## Completed Today (2026-03-18)

### Cycle 91
- [x] Migrations 051-052 applied to live Supabase
- [x] Invoices + Pipeline committed (3,423 lines)
- [x] Schema-log.md updated
- [x] Fixed automated morning/evening CLI path
- [x] Fixed health-check.sh rg dependency

### Cycle 92
- [x] Sidebar nav for Invoices + Pipeline
- [x] Bids-to-invoices guard (status + dedup)
- [x] Default pipeline seeding (6 stages)
- [x] Payment reminders for unpaid invoices
- [x] AI Business Insights (weekly brief + dashboard widget + endpoint)
- [x] Create lead endpoint (manual from pipeline)
- [x] PipelinePage QA fixes (movePipelineLead, createLead, silent except)
- [x] Missing api.js exports (updateInvoice, deleteInvoice)

### Cycle 93
- [x] Smart Lists — migration 053, backend + frontend
- [x] Form & Survey Builder — migration 054, backend + frontend
- [x] Sidebar nav for Smart Lists + Forms
- [x] 14 new API functions in api.js
- [x] All Tier 6 features complete

### Cycle 94
- [x] Campaign send → background task (was blocking request thread)
- [x] Form submit rate limiting (10/min)
- [x] Removed dead analytics route
- [x] Fixed GBP OAuth redirect URI
- [x] Migration 055 applied

### Cycle 95
- [x] Parallelized automation loop (asyncio.gather, tiered schedule)
- [x] Batched N+1 queries in automation engine
- [x] Analytics: replaced 10K chat_messages fetch with conversations count
- [x] Retry logic (exponential backoff for email/SMS)
- [x] Fixed check_no_response_leads dedup bug

### Cycle 96
- [x] Public booking page
- [x] Two-way SMS conversations
- [x] Enhanced review automation (Google Place ID, migration 056)
- [x] Conversation channel index (migration 057)

### Cycle 97
- [x] widget.py split into 5 modules (chat, config, booking, lead, helpers)
- [x] Shared dependencies (config.py, dependencies.py)
- [x] Automation engine tests updated

### Cycle 98
- [x] Omnichannel channel manager service
- [x] Facebook Messenger integration (webhook handler)
- [x] Inbox channel filter (widget/sms/facebook)

### Cycle 99
- [x] Facebook connect UI in IntegrationsPage
- [x] Webhook events for Zapier (lead.status_changed)

### Cycle 100
- [x] CSAT dashboard page
- [x] Booking page URL + embed code in Settings
- [x] Migration 058 (conversations.lead_id FK fix)
- [x] Signup website_url auto-crawl

### Cycle 101
- [x] Custom fields UI (LeadDetailDrawer)
- [x] Billing matrix with plan comparison
- [x] Upgrade prompts (UpgradePrompt component)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
