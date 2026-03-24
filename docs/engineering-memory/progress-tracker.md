# Progress Tracker
_What was built each session. Proves velocity, prevents re-doing work._

## Session 2026-03-24 (afternoon)

### Bugs Fixed
1. **conversations table FK misuse** — sms.py and analytics.py queried conversations with tenant_id instead of client_id. All 6 occurrences fixed (4 in analytics.py, 2 in sms.py including an insert).
2. **NULL plan from Supabase** — 22 `.get("plan", "free")` calls returned None when DB had NULL. Fixed to `or "free"` pattern across 7 files (auth, billing, widget_chat, widget_config, sequences, team, automation_engine).
3. **NULL business_name/type/city in customer-facing text** — 40+ `.get("key", "default")` calls returned None for NULL DB values. Fixed across 20 files (widget prompts, emails, SMS, invoices, calls, SEO, bids, jobs, billing).
4. **NULL owner_email in Stripe customer creation** — Could pass None to Stripe. Fixed in billing.py and auth.py.

### Features Built
1. **Bulk Lead Actions UI** — Checkbox selection on LeadsPage table view with bulk action bar. Change stage, assign/unassign, delete multiple leads at once. Visual selection highlighting.
2. **Lead Activity Timeline** — New GET /leads/{tenant_id}/{lead_id}/activity endpoint. Aggregates activity_log + appointments + email_events into unified timeline. Rendered in LeadDetailDrawer with icons and relative timestamps.
3. **Webhook Retry Improvement** — Upgraded from single 30s retry to 3 retries with exponential backoff (5s, 15s, 60s). Better logging per retry attempt.
4. **Auto-Archive Old Conversations** — New background task in 30-min automation tier. Archives conversations with status open/closed and updated_at > 30 days. Up to 200 per cycle.

### Commits
- 8 commits on detached HEAD

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
