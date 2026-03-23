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
