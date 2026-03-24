# Engineering State
## Last Session — 2026-03-24 (Session 5)
- Fixed: NULL-safe .get() pattern regressions in 7 locations (bids.py, widget_helpers.py, reviews.py, jobs.py, content.py)
- Fixed: analytics_team.py — appointments used non-existent created_by column, action_items used wrong status value "completed" (should be "done") and non-existent updated_at column
- Fixed: CRITICAL operator precedence bug in automation_engine.py — `tenant.get("plan") or "free" == "free"` always True, causing ALL paid tenants to be skipped from birthday greetings and rebook suggestions
- Built: Team Performance + UTM Analytics sections on AnalyticsPage (frontend)
- Built: Conversation Sentiment Analysis (migration 068, backend auto-analysis via Claude Haiku, analytics endpoint, frontend visualization)
- Built: Widget Chat Hours (migration 069, separate schedule from business hours, auto online/offline, WidgetPage UI)
- Built: Bulk Invoice Generation (POST /invoices/{tenant_id}/bulk, up to 50 leads, optional auto-send)
- Built: Lead Nurture Score (computed from email_events, warming/cooling trends)
- Build status: GREEN (backend + frontend build passing)
- Blockers: Migrations 064-069 not applied to live Supabase (carried forward)
- Next up: Dashboard mobile responsive, Quick actions from notification bell, Email template visual editor
