# Engineering State
## Last Session — 2026-03-24 (Session 7)
- Fixed: NULL-safe .get() patterns in widget_config.py (proactive_enabled, booking_enabled, is_online), auth.py (is_online, plan_status), notifications.py (activity_type, description, priority)
- Built: Lead scoring decay — background task decays scores by 10% for leads inactive 30+ days
- Built: Invoice payment receipt — auto-email itemized receipt to customer on Stripe payment
- Built: Appointment confirmation SMS + email — sent automatically when appointment created
- Built: Lead re-engagement emails — auto-email cold leads after 14 days of inactivity
- Built: Invoice overdue escalation — urgent reminder to customer + owner notification at 7+ days overdue
- Built: Lead phone dedup in widget — prevents duplicate leads from phone-only visitors
- Built: Invoice CSV export — backend endpoint + frontend Export CSV button with date/status filters
- Built: Appointment type analytics — service type breakdown with popularity, no-show rates, revenue estimates
- Built: Auto AI review response — Claude Haiku generates draft when new review detected
- Built: Widget visitor funnel analytics — sessions->leads->appointments conversion rates
- Marked: 11 backlog items as complete that were built this session
- Added: 15 new backlog items focused on small business growth
- Build status: GREEN (backend + frontend build passing)
- Blockers: Migrations 064-071 not applied to live Supabase (carried forward)
- Next up: SMS conversation in widget, lead aging alerts, customer lifetime value, appointment utilization
