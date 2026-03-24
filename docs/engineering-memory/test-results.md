# Test Results
_Track what features have been tested, what passed, what failed._

## 2026-03-23

### Build Tests
- Backend import: PASS (`from backend.main import app`)
- Frontend build: PASS (`npm run build` in 5.06s)

### Code Audit Results
- `from __future__ import annotations`: 0 occurrences (PASS)
- `except BaseException`: 0 occurrences (PASS)
- `leads.tenant_id`: 0 occurrences (PASS)
- `conversations.tenant_id` (query context): 0 remaining after fix (PASS)
- Route shadowing: 0 remaining after fix (PASS)
- Claude model IDs: all claude-sonnet-4-6 (PASS)
- Widget JS sync: files identical (PASS)
- Anthropic client timeout: all have explicit timeout (PASS)
- CORS configuration: wildcard origins correctly set (PASS)

### Features Not Tested (need live environment)
- Recurring invoice generation (needs paid recurring invoice in DB)
- Conversation search (needs chat messages in DB)
- Bulk lead actions (needs leads in DB)
- No-show detection (needs confirmed appointment past start time)

## 2026-03-23 Session 2

### Build Tests
- Backend import: PASS
- Frontend build: PASS (4.00s)

### Code Audit Results
- `from __future__ import annotations`: 0 occurrences (PASS)
- `except BaseException` / bare `except:`: 0 occurrences (PASS)
- `table("leads").eq("tenant_id"`: 0 occurrences (PASS — uses client_id correctly)
- `table("conversations").eq("tenant_id"`: 0 occurrences (PASS — uses client_id correctly)
- Invalid Claude model IDs: 0 occurrences (PASS)
- Widget JS sync: files identical (PASS)
- `lead_stage` column reference: 0 in query context (PASS — only in trigger event names)

### New Features (static analysis)
- Waitlist router: imports OK, no route shadowing, uses client_id for leads (PASS)
- Lead timeline: aggregates 7 tables safely with try/except per source (PASS)
- Webhook retry: exponential backoff logic correct, max 3 retries (PASS)
- Daily digest: dedup via activity_log, paid-plan filter, proper date math (PASS)
- Client self-scheduling: validates booking_enabled, links lead_id, fires webhooks (PASS)
- Scoring config: unique constraint on (tenant_id, factor), weight bounds checked (PASS)

### Features Not Tested (need live environment)
- Waitlist auto-notify on cancellation (needs running server + cancellation)
- Lead timeline display (needs lead with activity history)
- Webhook exponential backoff (needs failing webhook URL)
- Daily digest emails (needs paid tenant + Resend API key)
- Client portal booking (needs client account + available slots)
- Scoring config persistence (needs live Supabase with migration 067)

## 2026-03-23 Session 3

### Build Tests
- Backend import: PASS
- Frontend build: PASS (3.80-5.83s across multiple iterations)

### Code Audit Results
- `from __future__ import annotations`: 0 occurrences (PASS)
- `except:` (bare): 0 occurrences (PASS)
- `table("leads").eq("tenant_id"`: 0 occurrences (PASS)
- `table("conversations").eq("tenant_id"`: 0 occurrences (PASS)
- Invalid Claude model IDs: 0 occurrences (PASS)
- Widget JS sync: files identical (PASS)
- `.get("business_name", "default")`: 0 remaining after fix (PASS — all converted to `or`)
- Route shadowing: 0 remaining after fix (PASS — checked via automated script)
- `.get("owner_email", "")`: 0 remaining after fix (PASS — converted to `or`)

### New Features (static analysis)
- Appointment check-in: validates status (confirmed/pending only), logs activity, fires webhook (PASS)
- Stripe invoice payment webhook: idempotent (skips already-paid), resolves tenant_id, sends notifications (PASS)
- Buffer zone enforcement: extends booked ranges by buffer_minutes, includes checked_in/pending in query (PASS)
- Conversation auto-close: batch update with BATCH_LIMIT, runs on 5-min tier (PASS)
- Lead CSV export: 15 columns, StreamingResponse, max 5000 rows, uses client_id correctly (PASS)
- AI FAQ suggestions: dedupes against existing FAQs, validates JSON response, min 5 conversations (PASS)
- Appointment reschedule: preserves lead_id, resets to confirmed, email+SMS+webhook (PASS)

### Features Not Tested (need live environment)
- Stripe invoice payment (needs live Stripe webhook + Payment Link)
- AI FAQ suggestions (needs live Anthropic API + conversations in DB)
- Appointment reschedule email/SMS (needs Resend + Twilio configured)
- Conversation auto-close (needs conversations with updated_at > 24h ago)
- Lead CSV export download (needs leads in DB)

## 2026-03-23 Session 4

### Build Tests
- Code audit: PASS (all known bug patterns clean)
- sms.py comment fix: verified code uses client_id correctly, only comment was wrong

### Code Audit Results
- `from __future__ import annotations`: 0 occurrences (PASS)
- `except:` (bare): 0 occurrences (PASS)
- `table("leads").eq("tenant_id"`: 0 occurrences (PASS)
- `table("conversations").eq("tenant_id"`: 0 occurrences (PASS)
- Invalid Claude model IDs: 0 occurrences (PASS)
- `.get("key", default)` pattern: 0 regressions (PASS)
- Route shadowing: 0 issues (PASS)

### New Features (static analysis)
- Team performance endpoint: aggregates 5 tables (team_members, conversations, response_metrics, leads, appointments, action_items), proper client_id usage for conversations/leads (PASS)
- UTM analytics endpoint: reads source/metadata fields from leads, proper client_id usage (PASS)
- UTM capture in widget_chat: extracts from visitor_info dict, stores on lead via activity_log metadata (PASS)
- Frontend API functions: follow existing patterns, correct URL construction (PASS)

### Features Not Tested (need live environment)
- Team performance with real team data (needs team_members + assigned conversations)
- UTM tracking end-to-end (needs widget with UTM params + leads in DB)

## 2026-03-24 Session 5

### Build Tests
- Backend import: PASS
- Frontend build: PASS (3.65-5.71s across iterations)

### Code Audit Results
- `from __future__ import annotations`: 0 occurrences (PASS)
- `except:` (bare): 0 occurrences (PASS)
- `table("leads").eq("tenant_id"`: 0 occurrences (PASS)
- `table("conversations").eq("tenant_id"`: 0 occurrences (PASS)
- Invalid Claude model IDs: 0 occurrences (PASS)
- Widget JS sync: files identical (PASS)
- `.get("business_type", "default")`: 0 remaining after fix (PASS — all converted to `or`)
- Operator precedence `.get("plan") or "free" == "free"`: 0 remaining after fix (PASS)
- `created_by` on appointments: 0 occurrences (PASS — was only in analytics_team.py, now fixed)
- `"completed"` on action_items: 0 occurrences in query context (PASS — all use "done")

### New Features (static analysis)
- Team Performance endpoint: aggregates 5+ tables, correct client_id for conversations/leads, uses lead assignment for appointments (PASS)
- UTM analytics endpoint: reads source/metadata from leads/activity_log, correct client_id (PASS)
- Conversation sentiment: migration 068 correct, background task uses Claude Haiku, analytics query correct (PASS)
- Widget chat hours: migration 069 correct, _is_within_chat_hours uses business timezone, manual toggle override works (PASS)
- Bulk invoice generation: max 50 leads, auto-send optional, fires webhooks, correct client_id for leads (PASS)
- Lead nurture score: computed from email_events, no migration needed, correct scoring weights (PASS)

### Features Not Tested (need live environment)
- Conversation sentiment analysis end-to-end (needs closed conversations + Anthropic API key)
- Chat hours auto-switching (needs migration 069 applied + business hours configured)
- Bulk invoice auto-send (needs Resend/Twilio configured)
- Lead nurture score with real data (needs email_events in DB)

## 2026-03-24 Session 6

### Build Tests
- Backend import: PASS
- Frontend build: PASS (4.12-6.18s across iterations)
- Widget JS sync: PASS (files identical)

### Code Audit Results
- `from __future__ import annotations`: 0 occurrences (PASS)
- `except:` (bare): 0 occurrences (PASS)
- `table("leads").eq("tenant_id"`: 0 occurrences (PASS)
- `table("conversations").eq("tenant_id"`: 0 occurrences (PASS)
- Invalid Claude model IDs: 0 occurrences (PASS — all claude-sonnet-4-6 or claude-haiku-4-5-20251001)
- Widget JS sync: files identical (PASS)
- `.get("business_name", default)`: 0 occurrences (PASS — all use `or` pattern)
- `.get("business_type", default)`: 0 occurrences (PASS)
- `.get("owner_email", default)`: 0 occurrences (PASS)
- Operator precedence `.get("plan") or "free" == "free"`: 0 occurrences (PASS)

### Bugs Found and Fixed
- Rebook suggestion dedup keyed by lead_id (NULL fails dedup): FIXED with appointment ID key
- No-show detection only checked confirmed status: FIXED to include pending

### New Features (static analysis)
- Dashboard mobile responsive: media queries for 768px and 480px, tables scroll, grids stack (PASS)
- Notification quick actions: entity_id on items, action_items_count on response, per-type buttons (PASS)
- Birthday automation: respects birthday_enabled, custom template with variable replacement (PASS)
- Dashboard customizer: localStorage prefs, 7 toggleable sections, modal UI (PASS)
- Widget proactive greeting: configurable delay 5-120s, custom message, widget JS updated (PASS)

### Features Not Tested (need live environment)
- Birthday automation end-to-end (needs leads with date_of_birth + Resend API key)
- Proactive greeting timing (needs widget deployed on external page)
- Dashboard customizer persistence across browser sessions
- Notification quick actions navigation (needs live notification data)

## 2026-03-24 Session 7

### Build Tests
- Backend import: PASS
- Frontend build: PASS (3.61-4.19s across iterations)
- Widget JS sync: PASS (files identical)

### Code Audit Results
- `from __future__ import annotations`: 0 occurrences (PASS)
- `except:` (bare): 0 occurrences (PASS)
- `table("leads").eq("tenant_id"`: 0 occurrences (PASS)
- `table("conversations").eq("tenant_id"`: 0 occurrences (PASS)
- Invalid Claude model IDs: 0 occurrences (PASS)
- Widget JS sync: files identical (PASS)
- `.get("business_name", default)`: 0 occurrences (PASS)
- `.get("business_type", default)`: 0 occurrences (PASS)
- `.get("owner_email", default)`: 0 occurrences (PASS)
- `.get("plan", default)`: 0 occurrences — all use `or` pattern (PASS)
- Operator precedence `.get("plan") or "free" == "free"`: 0 occurrences (PASS)
- `created_by` on appointments: only in comment (PASS)
- `"completed"` on action_items: 0 in query context — all use "done" (PASS)
- Route shadowing: 0 issues detected (PASS)
- `except BaseException`: 0 occurrences (PASS)

### Bugs Found and Fixed
- widget_config.py: proactive_enabled, proactive_delay_seconds, booking_enabled passed None to non-optional Pydantic fields: FIXED with `or` pattern
- widget_config.py: _resolve_online_status used `not .get("is_online", True)` which treats None as offline: FIXED with `is not False`
- auth.py: is_online passed None to `bool` Pydantic field: FIXED with `is not False`
- auth.py: plan_status passed None to `str` Pydantic field: FIXED with `or "active"`
- notifications.py: activity_type, description, priority used `.get("key", default)` pattern: FIXED with `or`

### New Features (static analysis)
- Lead scoring decay: idempotent daily run, checks updated_at + activity_log, min score 0 (PASS)
- Invoice payment receipt: resolves customer email from lead, HTML receipt with line items (PASS)
- Appointment confirmation: SMS rate-limited for paid plans, email with formatted time (PASS)
- Lead re-engagement: 14-day cold threshold, 30-day dedup, unsubscribe link included (PASS)
- Invoice overdue escalation: 7-day threshold, status update to overdue, owner notification (PASS)
- Phone dedup in widget: only triggers when no email, fills missing fields on existing lead (PASS)
- Invoice CSV export: 14 columns, date/status filter, lead name resolution (PASS)
- Appointment type analytics: service type matching from notes, 5-min cache (PASS)
- Auto AI review response: Claude Haiku with 30s timeout, only for reviews without existing draft (PASS)
- Widget visitor funnel: conversion rates computed from existing data, 14-day daily trend (PASS)

### Features Not Tested (need live environment)
- Lead scoring decay with real stale leads (needs leads with old updated_at)
- Invoice payment receipt email delivery (needs live Stripe webhook + Resend)
- Appointment confirmation SMS delivery (needs live Twilio + paid tenant)
- Lead re-engagement email delivery (needs cold leads + Resend)
- Invoice overdue escalation triggers (needs overdue invoices in DB)
- Widget funnel with real session data (needs chat_messages in DB)

## 2026-03-24 Session 8

### Build Tests
- Backend import: PASS
- Frontend build: PASS (4.02-4.21s across iterations)
- Widget JS sync: PASS (files identical)

### Code Audit Results
- `from __future__ import annotations`: 0 occurrences (PASS)
- `except:` (bare): 0 occurrences (PASS)
- `except BaseException`: 0 occurrences (PASS)
- `table("leads").eq("tenant_id"`: 0 occurrences (PASS)
- `table("conversations").eq("tenant_id"`: 0 occurrences (PASS)
- Invalid Claude model IDs: 0 occurrences (PASS)
- Widget JS sync: files identical (PASS)
- `.get("business_name", default)`: 0 occurrences (PASS)
- `.get("business_type", default)`: 0 occurrences (PASS)
- `.get("owner_email", default)`: 0 occurrences (PASS)
- `.get("plan", default)`: 0 occurrences — all use `or` pattern (PASS)
- Operator precedence bugs: 0 occurrences (PASS)
- Route shadowing: 0 issues (PASS)
- show_watermark NULL safety: FIXED (3 locations in widget_chat.py, 1 in widget_config.py)

### Bugs Found and Fixed
- show_watermark: `.get("show_watermark", True)` returns None when NULL, crashes non-optional Pydantic `bool` field: FIXED with `is not False`
- widget config string fields: `.get("bot_name", "AI Assistant")` returns None when NULL, crashes Pydantic `str` field: FIXED with `or` pattern
- decay dedup FK violation: dummy UUID always fails FK constraint, no dedup: FIXED with real tenant_id
- Duplicate DB queries in booking.py and billing.py: FIXED by consolidation
- HTML XSS in 3 email templates: FIXED with html.escape()

### New Features (static analysis)
- CLV: aggregates invoices by lead_id, correct client_id-free query (invoices use tenant_id), 5-min cache (PASS)
- Utilization: business_hours JSONB parsing, correct slot calculation, booked count from appointments (PASS)
- Lead aging: correct client_id for leads query, proper dedup via activity_log, paid-plan filter, HTML-escaped output (PASS)

### Features Not Tested (need live environment)
- CLV with real invoice data (needs paid invoices in DB)
- Utilization with real appointments (needs business_hours configured)
- Lead aging alert email delivery (needs stale leads + Resend)
