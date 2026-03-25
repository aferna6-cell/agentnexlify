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

## Session 2026-03-24 (night)

### Bugs Fixed
1. **Birthday greeting operator precedence** — `tenant.get("plan") or "free" == "free"` always evaluated to True due to Python operator precedence. Fixed to `(tenant.get("plan") or "free") == "free"`. This meant birthday greetings were never being sent to paid tenants.
2. **log_activity wrong args in assign_lead** — Was passing `db` (Supabase client object) as `tenant_id` parameter. Fixed to use keyword arguments.

### Features Built
1. **Dashboard Quick Actions** — Quick Book modal (creates appointments from dashboard), Add Lead modal (creates leads directly), Send Campaign navigation. Added POST /appointments/{tenant_id}/dashboard-book JWT-protected endpoint.
2. **Lead Notes from Conversations** — "Lead Note" button on ConversationsPage links to the conversation's associated lead. Inline textarea with success feedback. Backend now returns lead_id in conversation list response.
3. **Service Type Selection on Booking Page** — Public booking page shows radio button service type selector when service_types are configured. Records selected service in appointment notes.
4. **Team Member Activity Log** — GET /team/{tenant_id}/activity endpoint filters activity_log entries with performed_by metadata. TeamActivityPage with member filter, time range, grid layout. Added performed_by tracking to lead create and assign actions.
5. **Email Template Preview with Sample Data** — resolveTemplateVars() in SequenceBuilder replaces {{variables}} with highlighted sample data. Blue highlight for known vars, yellow for unknown.
6. **Invoice Payment Webhook** — Stripe webhook handler now detects invoice payments (checkout.session.completed with invoice_id metadata), marks invoice as paid, fires invoice.paid webhook event, logs activity.

### Commits
- 5 commits pushed to origin/main

## Session 2026-03-25

### Bugs Fixed
1. **Appointment double-booking race condition** — Added pre-insert overlap check in create_appointment() and graceful handling of DB EXCLUDE constraint violations. All callers (public booking, dashboard booking, booking page) now return 409 on conflict instead of 500.
2. **Invoice number uniqueness** — Migration 068 adds unique index on (tenant_id, invoice_number). Invoice creation retries up to 3x with incrementing sequence on conflict.
3. **Widget session cleanup** — New prune_stale_widget_sessions() function deletes chat_messages from sessions inactive >90 days. Skips sessions with active conversations. Runs in 30-min automation tier.

### Features Built
1. **Dashboard KPI deltas** — New GET /analytics/{tenant_id}/kpi-deltas endpoint. Compares this week vs last week for leads, conversations, appointments, hot leads. DeltaBadge component shows green up/red down/gray flat arrows with percentages. New appointments-this-week card.
2. **Lead CSV export** — GET /leads/{tenant_id}/export-csv with stage/search/assigned_to filters. Downloads CSV with all lead fields including tags (comma-separated). "Export CSV" button on LeadsPage respects current filters.
3. **Appointment iCal feed** — GET /appointments/{tenant_id}/ical?key={api_key} returns .ics calendar feed. Includes last 30 days + next 90 days appointments. Businesses subscribe in Google Calendar/Apple Calendar.
4. **Appointment reschedule page** — HMAC-signed reschedule URLs in confirmation emails. Public page shows available slots for next 14 days. Customer can pick new date/time or cancel directly. Activity logging for both actions.
5. **Bulk invoice send** — POST /invoices/{tenant_id}/bulk-send sends up to 50 invoices. Creates Stripe payment links, dispatches via email/SMS. InvoicesPage: checkbox column, select-all, bulk action bar.

### Commits
- 5 commits pushed to origin/main
