# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Today's Top 3 Priorities (2026-03-20)

1. **Verify Cycles 109-115 in production** — 7 feature commits overnight (services onboarding, invoice library, deposits, documents/e-signatures, dental simulation) need E2E verification
2. **Split api.js into domain modules** — 30 touches in 7 days, highest frontend hotspot; merge conflict risk continues to grow
3. **Split main.py router registration** — 32 touches in 7 days, second-highest hotspot

## Active Tasks

### Priority 1 — Verify Recent Features
- [ ] Verify Cycle 109: services list + textback in onboarding, security hardening
- [ ] Verify Cycle 110: line item library for invoices
- [ ] Verify Cycle 111: deposit/partial payments + recurring invoices
- [ ] Verify Cycle 112: documents & e-signatures backend + migration
- [ ] Verify Cycle 113: documents page + sidebar + schema docs
- [ ] Verify Cycle 114: document/invoice tests + route fix + Field import
- [ ] Verify Cycle 115: dental office simulation + FAQs + dead code sweep
- [ ] Verify Cycles 104-108 (carried forward from yesterday)

### Priority 2 — Quality & Refactoring
- [ ] Split api.js into domain modules (30 touches in 7 days — critical hotspot)
- [ ] Split main.py router registration (32 touches in 7 days — critical hotspot)
- [ ] Add contract tests for api.js flows
- [ ] Configure Cloudflare Browser Rendering env vars
- [ ] Forms embed URL returns JSON not HTML (feature gap from 2026-03-20 morning)
- [ ] Pipeline frontend should use backend-driven stages (fetchPipelineBoard/fetchPipelineStages)

### Priority 3 — Feature Backlog
- [ ] Social media platform OAuth (direct posting)
- [ ] Real SERP data integration (SEMrush/Ahrefs)
- [ ] Competitor analysis dashboard
- [ ] Automated social media posting scheduler
- [ ] Dental-aware appointment reminders
- [ ] Patient intake forms (dental/healthcare vertical)
- [ ] Insurance/payment plan custom fields (dental/healthcare)

## Completed (Recent)

### 2026-03-19 Evening — Cycles 109-115
- [x] Services list input in onboarding wizard (Cycle 109)
- [x] Missed-call text-back toggle in onboarding (Cycle 109)
- [x] Rate limiting + HTML escaping on review requests (Cycle 109)
- [x] Invoice line item library (Cycle 110)
- [x] Deposit/partial payments + recurring invoices (Cycle 111)
- [x] Documents & e-signatures backend + migration 061 (Cycle 112)
- [x] Documents page + sidebar + schema docs (Cycle 113)
- [x] Document/invoice tests + route fix + Field import fix (Cycle 114)
- [x] Dental office simulation + 4 new FAQs + dead code sweep (Cycle 115)

### 2026-03-20 Morning (Interactive) — Cycle 102
- [x] Fixed 12 critical bugs across Smart Lists, Forms, Invoices, Pipeline, Inbox
- [x] Verified all migrations 045-058 applied to live Supabase
- [x] Deleted `backend/routers/_widget_legacy.py`
- [x] Fixed 2 silent catches in SettingsPage.jsx
- [x] 4 new bug-patterns.md entries

### Previous Completed
- [x] Custom fields UI, billing matrix, upgrade prompts (Cycle 101)
- [x] CSAT, booking URL, FK fix, website_url (Cycle 100)
- [x] Facebook connect, webhook events (Cycle 99)
- [x] Omnichannel channel manager, inbox filter (Cycle 98)
- [x] Widget.py split (Cycle 97)
- [x] Public booking, two-way SMS, review automation (Cycle 96)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
