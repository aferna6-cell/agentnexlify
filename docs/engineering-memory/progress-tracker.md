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
