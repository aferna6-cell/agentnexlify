# Current Task Backlog — AgentNexLiFy

Updated by the automated morning/evening routines and interactive sessions.

## Today's Top 3 Priorities (2026-03-19)

1. **Verify migrations 045-048 applied** — 4 migrations found undocumented; need live DB confirmation
2. **Verify new pages E2E** — Smart Lists, Forms, Invoices, Pipeline, CSAT (all built but untested end-to-end)
3. **Frontend build check** — api.js (40 touches) and App.jsx (19 touches) this week; confirm Vercel build passes

## Active Tasks

### Priority 1 — Verify / Critical
- [ ] Verify migrations 045-048 applied to live Supabase (seo_profiles, csat_responses, custom_field_definitions, tenants.autopilot_enabled)
- [ ] Verify Smart Lists page works E2E (create, filter, export CSV)
- [ ] Verify Forms page works E2E (create, embed, public submit, lead creation)
- [ ] Verify Invoices + Pipeline pages (carried forward)
- [ ] Verify CSAT page works E2E (new in Cycle 100)
- [ ] Verify public booking page (new in Cycle 96)
- [ ] Verify omnichannel inbox filtering (new in Cycle 98)
- [ ] Verify Facebook Messenger webhook flow (new in Cycle 99)

### Priority 2 — Feature Backlog
- [ ] Social media platform OAuth (direct posting)
- [ ] Real SERP data integration (SEMrush/Ahrefs)
- [ ] Competitor analysis dashboard
- [ ] Automated social media posting scheduler
- [ ] Documents & E-Signatures (future Tier 6 item)

### Priority 3 — Quality
- [ ] Fix 2 silent catches in SettingsPage.jsx (lines 878, 914 — genuinely empty .catch(() => {}))
- [ ] Add contract tests for api.js flows
- [ ] Configure Cloudflare Browser Rendering env vars
- [ ] Consider splitting api.js into domain modules (40 changes in 7 days — hotspot)
- [ ] Consider splitting main.py router registration (36 changes in 7 days — hotspot)
- [ ] Delete archived `backend/routers/_widget_legacy.py`
- [ ] Verify older features in production

### Priority 4 — Improvements
- [ ] Add frontend build validation to CI
- [ ] Audit `.catch(() => null)` patterns in dashboard pages

## Completed Yesterday (2026-03-18)

### Cycle 101
- [x] Custom fields UI (LeadDetailDrawer)
- [x] Billing matrix with plan comparison
- [x] Upgrade prompts (UpgradePrompt component)

### Cycle 100
- [x] CSAT dashboard page
- [x] Booking page URL + embed code in Settings
- [x] Migration 058 (conversations.lead_id FK fix)
- [x] Signup website_url auto-crawl

### Cycle 99
- [x] Facebook connect UI in IntegrationsPage
- [x] Webhook events for Zapier (lead.status_changed)

### Earlier (last 7 days)
- [x] Omnichannel channel manager + Facebook Messenger + inbox filter (Cycle 98)
- [x] Widget.py split into 5 modules (Cycle 97)
- [x] Public booking page + two-way SMS + review automation (Cycle 96)
- [x] Parallelized automation loop + batch queries (Cycle 95)
- [x] Campaign background task + rate limiting + OAuth fix (Cycle 94)
- [x] Smart Lists + Form Builder (Cycle 93)
- [x] Payment reminders + AI insights + sidebar nav (Cycle 92)
- [x] Invoicing + Sales Pipeline (Cycle 91)

---

_This file is auto-updated by morning and evening routines. Manual edits are welcome._
