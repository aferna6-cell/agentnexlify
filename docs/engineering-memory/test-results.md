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
