# Progress Tracker
_What was built each session. Proves velocity, prevents re-doing work._

## 2026-03-23 Session

### Bugs Fixed (Phase A)
1. **conversations.client_id regression #3** — Fixed 8 locations across sms.py (2), analytics.py (4), services/conversation.py (2)
2. **Route shadowing** — Fixed documents.py (templates unreachable) and webhooks.py (schema/events unreachable)
3. **NULL plan defaults** — Fixed 23 occurrences of `.get("plan", "free")` pattern across 6 files
4. **NULL business_name defaults** — Fixed 13 occurrences across 6 files
5. **Silent except blocks** — Added logging to 2 silent fallbacks in sequences.py
6. Total: 48 individual code fixes across 13 files

### Features Built (Phase B)
1. **Recurring invoice auto-generation** (automation_engine.py + main.py)
   - Processes paid recurring invoices where next_invoice_date <= today
   - Clones items/amounts, generates sequential number, advances date
   - Activity log dedup, webhook fire, 4 interval types
2. **Conversation search** (conversation_inbox.py + inbox.js + ConversationsPage.jsx)
   - Full-text search via ilike on chat_messages
   - Snippet extraction with context around match
   - Enriched with lead names, conversation tags
   - Frontend: debounced server search with results overlay
3. **Bulk lead actions** (leads.py + leads.js + LeadsPage.jsx)
   - Checkbox selection on LeadTable with select-all
   - 4 actions: assign, change_status, add_tag, delete
   - Bulk action bar with dynamic parameter inputs
   - Max 200 leads per batch
4. **Appointment no-show detection** (automation_engine.py + analytics.py + main.py)
   - Auto-marks confirmed appointments as no_show after 30 min past start
   - No-show analytics endpoint with rate calculation + repeat offenders
   - Activity log entries for dashboard visibility

### Backlog
- Added 15 new backlog items (waitlist, timeline, bulk actions, webhook retry, etc.)
- Updated bug-patterns.md with 3 new entries

## 2026-03-23 Session 2

### Bug Hunt (Phase A)
- All automated checks PASS: no __future__ annotations, no bare excepts, no bad model IDs
- No client_id/tenant_id confusion found (previous fixes holding)
- Widget JS files in sync
- Build GREEN on both backend and frontend

### Features Built (Phase B)
1. **Appointment Waitlist** (migration 066, waitlist.py, WaitlistPage.jsx)
   - Full CRUD: join, check, list, stats, update, delete
   - Auto-notify on cancellation (email + SMS, first-come first-served)
   - Hooks into existing appointment cancel flow
   - Frontend: stats cards, filter tabs, action buttons
2. **Lead Activity Timeline** (leads.py, LeadDetailDrawer.jsx)
   - Backend aggregates 7 tables: activity_log, chat_messages, appointments, invoices, documents, email_events, client_notes
   - Chronological feed sorted newest-first
   - Frontend: collapsible panel with type-coded icons
3. **Webhook Retry with Exponential Backoff** (webhook_dispatcher.py)
   - 3 retries: 1min, 5min, 30min
   - Log retry attempt number in webhook_logs
   - Auto-disable after 10 consecutive failures (unchanged)
4. **Daily Quick Stats Email Digest** (automation_engine.py, main.py)
   - Morning email to paid-plan owners with yesterday's metrics
   - Covers: new leads, conversations, appointments, revenue
   - Dedup via activity_log (one per tenant per day)
5. **Client Portal Self-Scheduling** (client_portal.py, ClientDashboardPage.jsx, booking.py)
   - GET /client/slots, POST /client/book, DELETE /client/appointments
   - Full booking flow: date picker, slot grid, instant booking
   - Cancel button on confirmed appointments
   - Waitlist notification on client cancellations
   - Updated create_appointment() to accept optional lead_id
6. **Configurable Lead Scoring Weights** (migration 067, leads.py, SettingsPage.jsx)
   - 13 default scoring factors
   - Per-tenant weight customization
   - Enable/disable individual factors
   - Reset to defaults option

### Backlog
- Marked 8 items as complete
- Added 18 new backlog items (total unchecked: 26)

## 2026-03-23 Session 3

### Bugs Fixed (Phase A)
1. **NULL-safe defaults round 2** — Fixed 15 instances of `.get("business_name", default)` pattern across 12 files (dependencies.py, local_seo.py, calls.py, widget_booking.py, widget_helpers.py, invoices.py, billing.py, automations.py, business_page.py, twilio_webhooks.py, jobs.py, auth.py)
2. **NULL-safe defaults for business_type** — Fixed 3 instances in local_seo.py, widget_config.py, widget_chat.py
3. **NULL-safe defaults for owner_email** — Fixed 2 instances in billing.py, auth.py (Stripe customer creation)
4. **Route shadowing: client portal** — client_router for /client/* static routes, included before parameterized /{tenant_id}/* routes
5. **Route shadowing: GBP** — callback_router for /callback static route, included before parameterized routes
6. Total: 20+ individual code fixes across 17 files

### Features Built (Phase B)
1. **Appointment check-in** — POST /check-in, Calendar UI button, activity log, webhook
2. **Stripe invoice payment webhook** — _handle_invoice_payment() in billing.py, auto-updates invoice to paid, owner email, activity log, webhook
3. **Appointment buffer zones** — Fixed conflict detection to extend booked ranges by buffer_minutes
4. **Conversation auto-close** — auto_close_inactive_conversations() in automation engine, 24h timeout, runs every 5 min
5. **Lead export to CSV** — GET /export endpoint with 15 columns, frontend Export CSV button
6. **AI FAQ suggestions** — POST /faq/suggest analyzes 50 conversations via Claude, frontend suggestion cards with Add/Dismiss
7. **Appointment reschedule** — POST /reschedule with email+SMS notifications, activity log, webhook, Calendar UI

### Backlog
- Marked 8 items as complete
- 18 unchecked items remaining

## 2026-03-23 Session 4

### Bug Hunt (Phase A)
- Code audit: all known bug patterns check PASS
- conversations table: all queries correctly use client_id (verified sms.py, analytics.py, widget_helpers.py)
- .get() or pattern: no regressions found
- Route shadowing: no new issues found
- Fixed misleading comment in sms.py (said conversations uses tenant_id but code correctly uses client_id)

### Features Built (Phase B)
1. **Team Performance Dashboard** (analytics.py backend endpoint)
   - GET /analytics/{tenant_id}/team-performance with per-member metrics
   - Conversations handled count per assigned team member
   - Average response time per team member
   - Leads assigned count per team member
   - Appointments booked count per team member
   - Action items completed count per team member
   - Period filtering (7/30/90/365 days)
2. **Lead Source UTM Tracking** (analytics.py backend + widget_chat.py capture)
   - UTM parameter capture from widget visitor_info (utm_source, utm_medium, utm_campaign)
   - Stored on leads table via source field and metadata
   - GET /analytics/{tenant_id}/lead-sources-utm analytics endpoint
   - Breakdown by utm_source, utm_medium, utm_campaign
   - Lead count and conversion rate per UTM source
3. **Frontend API functions** for both features (analytics.js)

### Backlog
- 16 unchecked items remaining

## 2026-03-24 Session 5

### Bugs Fixed (Phase A)
1. **NULL-safe .get() round 3** — Fixed 7 instances of `.get("key", "default")` pattern across bids.py, widget_helpers.py, reviews.py, jobs.py, content.py
2. **analytics_team.py: non-existent columns** — appointments query used `created_by` (doesn't exist), action_items query used `updated_at` (doesn't exist). Fixed to use lead assignment and `created_at` respectively
3. **analytics_team.py: wrong status value** — action_items filter used "completed" but CHECK constraint only allows "done"
4. **CRITICAL: operator precedence bug** — `tenant.get("plan") or "free" == "free"` always evaluated to True, skipping ALL paid tenants from birthday greetings and rebook suggestions. Fixed with parentheses: `(tenant.get("plan") or "free") == "free"`
5. Total: 11 code fixes across 8 files

### Features Built (Phase B)
1. **Team Performance + UTM Analytics** (AnalyticsPage.jsx)
   - Team performance table: conversations, avg response time, leads, appointments, tasks per member
   - UTM campaign analytics: source/medium/campaign breakdown with conversion rates
   - Both load in parallel with existing analytics calls
2. **Conversation Sentiment Analysis** (migration 068, automation_engine.py, analytics_team.py, AnalyticsPage.jsx)
   - Migration: sentiment column on conversations (positive/neutral/negative)
   - Background: Claude Haiku analyzes closed conversations every 30 min
   - Analytics: distribution cards, proportional bar, recent negative list
3. **Widget Chat Hours** (migration 069, widget_config.py, WidgetPage.jsx)
   - Separate schedule from business hours for AI chat availability
   - Auto online/offline based on time + business timezone
   - Per-day enable/start/end configuration on WidgetPage
4. **Bulk Invoice Generation** (invoices.py)
   - POST /invoices/{tenant_id}/bulk for up to 50 leads at once
   - Same line items, tax, due date for all; optional auto-send via email/SMS
5. **Lead Nurture Score** (leads.py, leads.js)
   - Computed from email_events: opens +1, clicks +3, replies +5
   - Trend indicators: warming/cooling/stable/cold
   - No migration needed — computed on-the-fly

## 2026-03-24 Session 6

### Bugs Fixed (Phase A)
1. **Rebook suggestion dedup keyed by lead_id** — When lead_id is NULL (nullable FK on appointments), PostgreSQL NULL != NULL means no dedup happened. Fixed to key by appointment ID instead.
2. **No-show detection missed pending appointments** — Only checked `status = 'confirmed'` but pending appointments past start_time are also no-shows. Fixed to check both confirmed and pending.

### Features Built (Phase B)
1. **Dashboard Mobile Responsive** (index.css)
   - Comprehensive media queries for 768px and 480px breakpoints
   - Tables: horizontal scroll on mobile for all data tables
   - Stats grids: stack to 2-col on tablets, 1-col on phones
   - Pipeline: horizontal scroll with snap points on mobile
   - Modals: full-width (95vw) on mobile
   - Touch: min 40px button targets on small phones
   - Sidebar: already had hamburger/overlay (verified working)
2. **Notification Bell Quick Actions** (NotificationBell.jsx, notifications.py, schemas.py)
   - Per-notification action buttons: View Lead/Reply for leads, Open Chat for conversations, View for appointments, View Tasks for action items
   - Quick navigation row with colored count badges (leads, appointments, conversations, tasks)
   - Backend: entity_id on NotificationItem, action_items_count on response
3. **Customer Birthday Automation** (migration 070, SettingsPage.jsx, automation_engine.py, auth.py)
   - Settings page toggle + custom message template with {customer_name}/{business_name}
   - Automation engine respects birthday_enabled flag (previously sent to all paid tenants)
   - HTML template support for custom birthday messages
4. **Dashboard Customizable Widgets** (Dashboard/index.jsx)
   - Customize button opens modal with toggle per widget section
   - 7 toggleable sections: Lead Pipeline, Activity Feed, Appointments, Action Items, AI Insights, Widget Embed, CRM Stats
   - Preferences stored in localStorage per tenant, persist across sessions
5. **Widget Proactive Greeting** (migration 071, widget JS, WidgetPage.jsx, schemas.py, widget_config.py)
   - Migration: proactive_enabled, proactive_delay_seconds, proactive_message on widget_configs
   - Widget JS: uses configurable delay instead of hardcoded 5s, shows custom message without API call
   - WidgetPage: Proactive Greeting section with toggle, delay input (5-120s), message textarea
   - Both widget JS copies synced

### Backlog
- Marked 11 items as complete (were already built in previous sessions)
- Added 20 new backlog items (total unchecked: ~25)

## 2026-03-24 Session 7

### Bugs Fixed (Phase A)
1. **NULL-safe .get() round 4** — Fixed 7 instances in widget_config.py (proactive_enabled, proactive_delay_seconds, booking_enabled, is_online in 2 places), auth.py (is_online, plan_status), notifications.py (activity_type, description, priority). These would cause Pydantic validation errors when Supabase columns are NULL.
2. Total: 7 code fixes across 3 files

### Features Built (Phase B)
1. **Lead scoring decay** (automation_engine.py, main.py)
   - Background task decays lead_score by 10% for leads with no interaction in 30+ days
   - Daily dedup via activity_log, checks both updated_at and activity_log for recent activity
2. **Invoice payment receipt** (billing.py)
   - Auto-sends itemized receipt email to customer when invoice paid via Stripe
   - Includes line items, subtotal, tax, total paid, business name
3. **Appointment confirmation SMS + email** (booking.py)
   - SMS confirmation to customer phone (paid plans only, rate-limited)
   - Email confirmation with formatted date/time and notes
4. **Lead re-engagement emails** (automation_engine.py, main.py)
   - Auto-emails leads with status new/contacted that haven't interacted in 14+ days
   - 30-day dedup window, respects unsubscribe, includes unsubscribe link
5. **Invoice overdue escalation** (automation_engine.py, main.py)
   - Urgent email to customer for invoices 7+ days past due
   - Owner notification with amount/customer/due date
   - Auto-updates invoice status to 'overdue'
6. **Lead phone dedup in widget** (widget_helpers.py)
   - When widget captures lead with phone but no email, checks for existing lead by phone
   - Auto-fills missing fields on matched lead, prevents duplicate creation
7. **Invoice CSV export** (invoices.py, invoices.js, InvoicesPage.jsx)
   - GET /invoices/{tenant_id}/export with date range and status filters
   - 14-column CSV with resolved customer names
   - Frontend Export CSV button on InvoicesPage
8. **Appointment type analytics** (analytics.py)
   - GET /analytics/{tenant_id}/appointment-types with service type breakdown
   - Popularity, completion rate, no-show rate, revenue estimate per type
9. **Auto AI review response** (automation_engine.py)
   - When check_new_reviews detects a new review, auto-generates Claude Haiku draft
   - Stores ai_draft_response on the review record for owner to review
10. **Widget visitor funnel analytics** (analytics.py)
    - GET /analytics/{tenant_id}/widget-funnel
    - Sessions started -> leads captured -> appointments booked
    - Conversion rates and daily trend data

### Backlog
- Marked 11 items as complete (built this session + Widget proactive greeting from Session 6)
- Added 15 new backlog items (total unchecked: ~31)

## 2026-03-24 Session 8

### Bugs Fixed (Phase A)
1. **NULL-safe .get() round 5** — Fixed show_watermark in widget_chat.py (3 locations using `is not False`), bot_name/primary_color/position/greeting_message in widget_config.py + auth.py (2 constructors) + business_page.py. All switched from `.get("key", default)` to `.get("key") or default`.
2. **CRITICAL: decay_stale_lead_scores FK violation** — Dedup marker used dummy UUID "00000000-0000-0000-0000-000000000000" for activity_log.tenant_id, which has FK constraint to tenants. Insert always failed silently, meaning NO dedup — function ran on every 30-min automation tick instead of once daily. Fixed to use real tenant_id from processed leads.
3. **Duplicate DB query in booking.py** — Appointment confirmation SMS and email each queried tenants table separately. Consolidated to single query.
4. **HTML XSS in email templates** — customer_name, biz_name, notes, interest, inv_number all interpolated raw into HTML emails. Fixed with html.escape() in booking.py, automation_engine.py (re-engagement + overdue escalation).
5. **Duplicate DB query in billing.py** — Invoice payment receipt queried tenants twice for biz_name. Hoisted initialization before try block.
6. Total: 15+ code fixes across 6 files

### Features Built (Phase B)
1. **Customer Lifetime Value (CLV)** (analytics.py, analytics.js, AnalyticsPage.jsx)
   - GET /analytics/{tenant_id}/customer-lifetime-value
   - Aggregates paid invoices by lead_id with revenue, invoice count, dates
   - Top N customers table on AnalyticsPage with stat cards
   - No migration needed — computed from existing invoices table
2. **Appointment Utilization Rate** (analytics.py, analytics.js, AnalyticsPage.jsx)
   - GET /analytics/{tenant_id}/appointment-utilization
   - Compares business_hours available slots vs booked appointments
   - Daily breakdown with utilization percentage bar chart
   - Stat cards: utilization %, available, booked, slot duration
3. **Lead Aging Alerts** (automation_engine.py, main.py)
   - Daily digest email to paid tenants listing leads in "new" status for 48h+
   - Grouped by tenant, HTML table with name/email/phone/age
   - Dedup via activity_log per tenant per day
   - Runs on 30-min automation tier

### Backlog
- Marked 3 items as complete (CLV, utilization, lead aging alerts)
- 28 unchecked items remaining
