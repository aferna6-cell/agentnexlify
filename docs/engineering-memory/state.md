# Engineering State
## Last Session — 2026-03-24 (Session 8)
- Fixed: NULL-safe .get() round 5 — show_watermark in widget_chat.py (3 locations), bot_name/primary_color/position in widget_config.py, greeting_message/bot_name/primary_color/position in auth.py (2 constructors), widget fields in business_page.py
- Fixed: CRITICAL — decay_stale_lead_scores used dummy UUID "00000000-0000-0000-0000-000000000000" for activity_log.tenant_id dedup marker, which violates FK constraint. Insert always failed silently = no dedup = function ran on every automation tick instead of daily
- Fixed: booking.py consolidated duplicate DB query for tenant data in appointment confirmation
- Fixed: HTML-escape user data in email templates (booking confirmation, re-engagement, overdue escalation)
- Fixed: billing.py eliminated duplicate DB query for business_name in invoice receipt
- Built: Customer Lifetime Value (CLV) tracker — analytics endpoint + AnalyticsPage section
- Built: Appointment utilization rate — analytics endpoint + AnalyticsPage section with bar chart
- Built: Lead aging alerts — automation engine sends daily digest of 48h+ stale leads to paid tenants
- Build status: GREEN (backend + frontend build passing)
- Blockers: Migrations 064-071 not applied to live Supabase (carried forward)
- Next up: SMS conversation in widget, recurring revenue dashboard, invoice partial payments
