# Engineering State
## Last Session — 2026-03-24 (afternoon)
- Fixed: conversations table queries using tenant_id instead of client_id (sms.py, analytics.py)
- Fixed: NULL plan handling — 22 occurrences of .get("plan", "free") that returned None for NULL DB values
- Fixed: NULL business_name, business_type, city, owner_email across 20+ files
- Built: Bulk lead actions UI (checkboxes, status change, assign, delete in table view)
- Built: Lead activity timeline in detail drawer (aggregates activity_log + appointments + email_events)
- Built: Webhook retry with exponential backoff (3 retries at 5s, 15s, 60s)
- Built: Auto-archive old conversations (>30 days inactive, runs every 30 min)
- In progress: (none)
- Next up: Appointment confirmation SMS/email, birthday automation, dashboard quick actions, email template preview
- Build status: GREEN (backend + frontend both pass)
- Blockers: Migrations 064-067 need manual application to live Supabase
