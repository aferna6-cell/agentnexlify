# Progress Tracker
_What was built each session. Proves velocity, prevents re-doing work._

## Session 2026-03-24

### Bugs Fixed
1. **API client 204 handling** — `_client.js` `request()` always called `res.json()` which throws on 204 No Content responses from DELETE endpoints. Fixed to check for 204 and empty bodies before parsing.

### Features Built
1. **Appointment Waitlist** (migration 066 + full backend + frontend)
   - Public join endpoint for widget/booking page
   - Dashboard page with stats, filters, notify via email/SMS
   - Dedup prevents same customer joining twice for same date

2. **Lead Scoring Configuration** (migration 067 + full backend + frontend)
   - Per-tenant customizable scoring weights with sliders
   - 6 default factors auto-seeded on first access
   - Add custom factors, toggle enable/disable, reset to defaults

3. **Appointment Confirmation** (backend)
   - Auto-sends email + SMS confirmation when appointment is booked
   - Includes date, time, business name, contact info

4. **Bulk Lead Updates** (backend + frontend API)
   - POST /leads/{tenant_id}/bulk-update endpoint
   - Supports bulk status change, assignment, tag addition
   - Up to 100 leads per request

5. **Conversation Search** (backend + frontend)
   - Server-side search across all message content
   - Enter key triggers deep search, instant filtering for names/previews

6. **Recurring Invoice Automation** (backend)
   - process_recurring_invoices() in automation loop (30min tier)
   - Creates draft invoices from recurring parents
   - Auto-advances next_invoice_date

7. **AI Knowledge Sources Panel** (backend + frontend)
   - GET /knowledge-stats endpoint returns FAQ count, crawled pages, corrections
   - SettingsPage shows visual grid of AI knowledge sources

8. **Appointment No-Show Tracking** (backend + frontend API)
   - GET /no-show-stats endpoint with rate and repeat offenders
   - no_show already valid status in schema

### Backlog
- Added 20 new items for small business daily operations (Tier 7)
- 18 unchecked items remain

### Commits
- 7 commits pushed to origin/main
