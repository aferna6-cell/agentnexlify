# Engineering State
## Last Session — 2026-03-24 (Session 6)
- Fixed: Rebook suggestion dedup was keyed by lead_id (fails when NULL), now keyed by appointment ID
- Fixed: No-show detection only checked 'confirmed' status, now also catches 'pending' appointments
- Built: Dashboard mobile responsive — comprehensive CSS for all pages (tables, stats grids, modals, touch targets)
- Built: Notification bell quick actions — per-item action buttons (View Lead, Reply, Open Chat, View Tasks) + quick navigation row with count badges
- Built: Customer birthday automation — Settings page toggle + custom message template with {customer_name}/{business_name} placeholders, automation engine respects birthday_enabled flag
- Built: Dashboard customizable widgets — toggle which sections appear (Lead Pipeline, Activity Feed, Appointments, Action Items, AI Insights, Widget Embed, CRM Stats), stored in localStorage
- Built: Widget proactive greeting — configurable auto-open delay (5-120s) with custom first message, migration 071, WidgetPage UI, widget JS updated
- Added: 20 new backlog items focused on small business owner value
- Marked: 11 previously unchecked backlog items that were already done
- Build status: GREEN (backend + frontend build passing)
- Blockers: Migrations 064-071 not applied to live Supabase (carried forward)
- Next up: Lead scoring decay, Invoice payment receipt, Appointment confirmation SMS, Lead duplicate merge from widget
