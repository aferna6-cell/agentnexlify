# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Today's Top 3 Priorities (2026-03-20)

1. ~~**Verify migrations 045-058 applied**~~ DONE — all 14 confirmed applied
2. ~~**Delete `_widget_legacy.py` + fix SettingsPage catches**~~ DONE
3. ~~**Verify new pages E2E**~~ DONE — 8 bugs found and fixed across Smart Lists, Forms, Invoices, Pipeline

## Active Tasks

### Priority 1 — Remaining from today's verification
- [ ] Forms embed URL returns JSON not HTML (needs frontend route or backend HTML endpoint)
- [ ] Pipeline frontend should fetch stages from API instead of using hardcoded values
- [ ] Pipeline frontend should use `fetchPipelineBoard` instead of `fetchLeads` for grouped data

### Priority 2 — Quality
- [ ] Add contract tests for api.js flows
- [ ] Configure Cloudflare Browser Rendering env vars
- [ ] Consider splitting api.js into domain modules (hotspot)
- [ ] Consider splitting main.py router registration (hotspot)
- [ ] Verify older features in production

### Priority 3 — Feature Backlog
- [ ] Social media platform OAuth (direct posting)
- [ ] Real SERP data integration (SEMrush/Ahrefs)
- [ ] Competitor analysis dashboard
- [ ] Automated social media posting scheduler
- [ ] Documents & E-Signatures

## Completed Today (2026-03-20)

### Verification & Bug Fixes (Cycle 102)
- [x] Verified all migrations 045-058 applied to live Supabase
- [x] Deleted `backend/routers/_widget_legacy.py`
- [x] Fixed SettingsPage.jsx silent catches
- [x] Fixed Smart Lists filter key mismatch (CRITICAL — filters were silently ignored)
- [x] Fixed Smart Lists `lead_count` → `cached_lead_count`
- [x] Removed Smart Lists non-functional preview button
- [x] Fixed Forms `is_active` read from wrong location
- [x] Fixed Forms `data` → `data_json` submission field
- [x] Fixed Pipeline move payload `new_stage` → `status` (CRITICAL — 422 error)
- [x] Fixed Invoices `markInvoicePaid` empty body (CRITICAL — 422 error)
- [x] Fixed Invoices `items` → `items_json` field name
- [x] Fixed Invoices `payment_link` → `stripe_payment_link`
- [x] Verified CSAT page fully wired
- [x] Verified public booking page fully wired
- [x] Verified omnichannel/Facebook fully wired
- [x] Fixed conversation_inbox.py `tenant_id` → `client_id` (CRITICAL — all inbox ops broken)
- [x] Fixed auth.py `update_conversation_tags` `tenant_id` → `client_id` (CRITICAL)
- [x] Fixed inbox session_id vs UUID mismatch — added `_find_conversation()` helper (CRITICAL)
- [x] Fixed csat.py silent exception — added logging
- [x] Added 4 new entries to bug-patterns.md

### Previous Completed
- [x] Custom fields UI, billing matrix, upgrade prompts (Cycle 101)
- [x] CSAT, booking URL, FK fix, website_url (Cycle 100)
- [x] Facebook connect, webhook events (Cycle 99)
- [x] Omnichannel channel manager, inbox filter (Cycle 98)
- [x] Widget.py split (Cycle 97)
- [x] Public booking, two-way SMS, review automation (Cycle 96)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
