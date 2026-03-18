# Platform Improvements Design Spec

**Date:** 2026-03-18
**Scope:** Critical fixes, performance, quick-win features, code quality, omnichannel foundation
**Phases:** 5 (incremental, each phase shippable independently)

---

## Phase 1: Critical Fixes

### 1A. Campaign send → background task
**File:** `backend/routers/marketing_campaigns.py`
**Problem:** `send_campaign()` sends up to 500 emails/SMS synchronously in the HTTP handler, blocking a worker for minutes.
**Fix:** After validating the campaign and building the recipient list, set `status=sending` and `sending_started_at=now()` in the DB and dispatch the actual send loop to `asyncio.create_task()`. Return immediately with `{"status": "sending", "campaign_id": "..."}`. The background task must:
- Wrap the entire send loop in `try/except` — on unhandled error, mark campaign `status=failed` with error details.
- Update campaign with final counts on completion.
- Add a startup recovery check to the automation loop: campaigns stuck in `sending` for >30 minutes get marked `failed`.
**Acceptance:** Campaign endpoint returns within 2 seconds. Campaign status transitions: draft → sending → sent/failed. Crashed background tasks don't leave campaigns stuck forever.

### 1B. Rate limit public form submit
**File:** `backend/routers/forms.py`
**Problem:** Public form endpoints have zero rate limiting. Attackers can spam unlimited fake leads.
**Fix:** Add `@limiter.limit("10/minute")` to `POST /api/v1/forms/public/{token}/submit` and `@limiter.limit("30/minute")` to `GET /api/v1/forms/public/{token}`. Requires `from backend.limiter import limiter` and adding `request: Request` as a parameter on both endpoints (required by slowapi).
**Acceptance:** 11th submission within a minute returns 429.

### 1C. Remove duplicate analytics route
**File:** `backend/routers/analytics.py`
**Problem:** Two `GET /{tenant_id}/response-times` handlers. First (line ~381) is dead code shadowed by second (line ~564).
**Fix:** Delete the `get_response_times` function (the first of two `/{tenant_id}/response-times` handlers). Keep `get_response_time_analytics` (the second one, which queries `response_metrics`). Identify by function name, not line numbers (they shift with edits).
**Acceptance:** Response times endpoint returns data from `response_metrics` table. No behavior change for callers.

### 1E. Exclude password_hash from team members endpoint
**File:** `backend/routers/team.py`
**Problem:** Team members GET endpoint uses `select("*")` which returns `password_hash` to the frontend. This is a security vulnerability.
**Fix:** Change to explicit column list excluding `password_hash`. Apply immediately — this is a data exposure issue, not just an optimization.
**Acceptance:** Team members API response never contains `password_hash`.

### 1D. Fix GBP OAuth redirect URI
**File:** `backend/routers/gbp.py`, line 46
**Problem:** Uses `settings.frontend_url` for OAuth callback. Should be backend URL since the callback handler is a backend API endpoint.
**Fix:** Change to `settings.api_url` or construct from `request.url_for()`. If no `api_url` setting exists, add one to `backend/config.py` (default: `"https://agentnexlify-production.up.railway.app"`).
**Acceptance:** Google OAuth redirect lands on the backend callback endpoint.

---

## Phase 2: Performance & Reliability

### 2A. Batch N+1 queries in automation engine
**File:** `backend/services/automation_engine.py`
**Problem:** `check_no_response_leads()` does 150-250 DB roundtrips per 60s cycle (3-5 queries per lead for 50 leads). `trigger_sequence()` does per-sequence queries for step delays.
**Fix:**
- Batch-fetch all recent conversations for the 50 leads in one query (using `client_id.in_()` or similar).
- Batch-fetch last message timestamps for all relevant session_ids in one query.
- Batch-fetch active sequence + first step data in a single joined query.
- Iterate results in Python using dicts keyed by lead_id/sequence_id.
**Acceptance:** `check_no_response_leads()` executes <=5 DB queries for the read/check phase regardless of lead count (down from 150-250). `trigger_sequence()` calls for qualifying leads are additional but only affect the small subset that need enrollment. `trigger_sequence()` itself executes <=2 queries per invocation.

### 2B. Fix analytics session counting
**File:** `backend/routers/analytics.py`
**Problem:** Overview endpoint fetches up to 10,000 `chat_messages` rows to count unique sessions in Python. Same pattern in conversations trend and response times.
**Fix:** Replace with `conversations` table queries using `count="exact"` and appropriate date filters. Three endpoints affected: overview (~line 92), conversations trend (~line 272), response time analytics (~line 399).
**Acceptance:** Overview endpoint no longer fetches chat_messages for counting. Response time drops significantly for tenants with high message volume.

### 2C. Parallelize automation loop
**File:** `backend/main.py`
**Problem:** 11 automation functions run sequentially. A slow function delays all subsequent ones.
**Fix:** Group functions by frequency and run via `asyncio.gather()`:
- **Every 60s:** `process_pending_steps`, `check_no_response_leads`, `send_appointment_reminders`
- **Every 5 min:** `send_pending_review_requests`, `send_onboarding_emails`, `send_portal_links`, `send_csat_surveys`, `check_new_reviews`, `send_invoice_payment_reminders`
- **Every 30 min:** `send_monthly_reports`, `send_weekly_intelligence_briefs`
Add a 30s timeout per function via `asyncio.wait_for()`.
**Acceptance:** Automation loop cycle time is bounded by the slowest function, not the sum of all. Functions that only need to run every 5/30 minutes don't execute every 60s.

### 2D. Add retry logic for external services
**File:** New `backend/services/retry.py`
**Problem:** Anthropic, Resend, and Twilio calls fail permanently on transient errors (5xx, timeouts).
**Fix:** Create `async def with_retry(fn, max_retries=2, backoff_base=1.0)` that:
- Calls `fn()`
- On transient error (5xx, 529 Anthropic overloaded, timeout, connection error): wait `backoff_base * 2^attempt` seconds, retry
- On 4xx or non-transient error: raise immediately
- After max_retries exhausted: raise the last error
Apply to: `send_email()`, `send_sms()`, and Anthropic `messages.create()` calls in automation_engine.py.
**Acceptance:** A single Resend 503 doesn't permanently fail an automation step. Two consecutive failures still fail (with logging).

---

## Phase 3: Quick-Win Features

### 3A. Public Booking Page
**Problem:** No standalone shareable booking URL. Customers can only book through the chat widget.
**Implementation:**
- Backend: `GET /api/v1/book/{business_slug}` — public, no auth. Returns server-rendered HTML page showing business name, available time slots (from `business_hours` + `appointments`), and a booking form (name, email, phone, slot selection). Styled with tenant's branding colors from `widget_configs`.
- Backend: `POST /api/v1/book/{business_slug}/submit` — validates slot availability, creates appointment, creates/updates lead (using `client_id`), sends confirmation email. Rate limited at 5/minute.
- Frontend: add "Booking Link" section to Settings page showing the URL + iframe embed code with copy buttons.
- No new migration needed. Uses existing `business_hours`, `appointments`, `leads`, `tenants` tables.
- Implementation note: create or reuse a shared `get_tenant_by_slug(slug)` helper (currently duplicated in auth.py, crawl.py, business_page.py).
**Acceptance:** Business owner texts `https://...railway.app/api/v1/book/joes-plumbing` to a customer. Customer sees available slots, books, gets confirmation. Appointment appears in dashboard calendar.

### 3B. Two-Way SMS Conversations
**Problem:** Business owners can't initiate text conversations from the dashboard.
**Implementation:**
- Backend: `POST /api/v1/sms/{tenant_id}/send` — authenticated. Accepts `{phone, message}`. Sends via Twilio from the tenant's provisioned number. Stores in `chat_messages` with `session_id=sms_{normalized_phone}`, `role=assistant`. Creates/finds conversation record. Fires `conversation.message` webhook.
- Frontend: add "New SMS" button to ConversationsPage. Opens compose panel with phone number input + message textarea. On send, the SMS conversation appears in the conversation list (the inbound webhook path already handles replies).
- Guard: tenant must have a provisioned phone number. If not, show "Set up your business phone number first" with link to Settings.
- Implementation note: the `sms_{normalized_phone}` session_id convention is already used by `twilio_webhooks.py` for inbound SMS and missed-call text-back. Verify this at implementation time to ensure the Phase 5B backfill (`WHERE session_id LIKE 'sms_%'`) will match existing records.
**Acceptance:** Business owner opens Conversations, clicks "New SMS", texts a customer. Customer's reply appears in the same thread. Thread is visible alongside widget chats.

### 3C. Enhanced Review Automation
**Problem:** Review requests go out immediately with a generic Google search link. No follow-up.
**Implementation:**
- Migration 055: `ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_place_id TEXT`. Small migration.
- Backend: update `send_pending_review_requests()` in automation_engine.py:
  1. Use `google_place_id` to construct direct review link: `https://search.google.com/local/writereview?placeid={id}`. Fall back to existing `google_review_link` if no place_id.
  2. Change default delay from "immediately after completion" to 2 hours (configurable via `review_request_config.delay_hours`, which already exists).
  3. Add follow-up: 48 hours after initial request, if no new review in `reviews` table for that tenant since the request, send one follow-up. Dedup via `activity_log` with type `review_followup_{lead_id}`.
- Frontend: add "Google Place ID" field to Settings page (in the Reviews section, near existing `google_review_link`). Tooltip explaining how to find it.
**Acceptance:** After appointment marked completed, review request goes out 2 hours later with direct Google link. If no review after 48 hours, one follow-up is sent. No more than one follow-up per customer.

---

## Phase 4: Code Quality & Testing

### 4A. Split widget.py into 4 modules
**File:** `backend/routers/widget.py` (2,396 lines)
**Target structure:**
- `widget_chat.py` — chat endpoint, AI response generation, message storage, system prompt construction, conversation tags, action item extraction (~800 lines)
- `widget_config.py` — config GET endpoint, branding, online/offline toggle, file upload, menu data (~400 lines)
- `widget_lead.py` — lead capture, dedup, phone/email regex extraction, lead scoring background task, contact extraction (~500 lines)
- `widget_booking.py` — appointment booking flow, slot calculation, booking confirmation, bid request detection (~300 lines)
- `widget_helpers.py` — shared utilities: tenant/config cache, origin check, rate limit keys, MODEL constant (~200 lines)

All register under `/api/v1/widget` prefix. No API contract changes. Widget JS unaffected. The split follows existing function boundaries — each function already has a clear responsibility.

### 4B. Extract shared dependencies
**File:** New `backend/dependencies.py`
**Contents:**
- `verify_tenant(claims: dict, tenant_id: str)` — canonical tenant verification, replacing ~27 copies across router files
- `get_business_context(tenant_id: str, db)` — tenant + business info lookup, replacing 2 duplicates
**Migration strategy:** Update files touched in Phases 1-3 first. Remaining files migrated incrementally in future cycles. No behavioral change.

### 4C. Automation engine tests
**File:** New `tests/test_automation_engine.py`
**Coverage targets (15-20 tests):**
- `process_pending_steps()`: happy path (step executes, status advances), no pending steps, step with failed email
- `send_invoice_payment_reminders()`: overdue invoice (marks overdue + sends), due-tomorrow invoice (sends nudge), already-reminded today (skips), invoice with no lead (skips)
- `send_weekly_intelligence_briefs()`: Monday sends brief, Tuesday skips, already-sent-this-week skips, free plan skips
- `trigger_sequence()`: matching stage triggers enrollment, non-matching stage skips, already-enrolled skips
- `check_no_response_leads()`: lead with no response triggers sequence, lead with recent response skips
**Approach:** Mock `get_supabase()` to return controlled data. Mock `send_email()` and `send_sms()` to verify calls without side effects.

### 4D. Narrow select("*") in high-traffic endpoints
**Endpoints to fix (10 highest-traffic):**
1. Widget config GET — select only: id, tenant_id, api_key, bot_name, primary_color, greeting_message, position, branding, booking_enabled, is_online, offline_message
2. Widget chat POST — select only needed tenant fields for system prompt
3. Leads list GET — already paginated, narrow to display columns
4. Conversations list GET — narrow to: id, session_id, status, tags, assigned_to, created_at, updated_at
5. Dashboard overview GET — narrow per-query based on what the dashboard displays
6. Appointments list GET — narrow to calendar display fields
7. Analytics overview GET — already uses count queries (post Phase 2B fix)
8. Notifications GET — narrow to: type, description, created_at, lead_id
9. FAQ list GET — select: id, question, answer, category
10. Team members GET — already fixed in Phase 1E

Note: Phase 4D should be done after Phase 4A (widget split) so that widget items target the post-split file names.

**Acceptance:** No `select("*")` in these 10 endpoints.

---

## Phase 5: Omnichannel Foundation

### 5A. Message normalization layer
**File:** New `backend/services/channel_manager.py`
**Interface:**
```python
class NormalizedMessage:
    channel: str       # "widget" | "sms" | "facebook" | "instagram" | "whatsapp" | "email"
    tenant_id: str
    session_id: str    # channel-specific: "sms_{phone}", "fb_{sender_id}", etc.
    sender_name: str
    sender_identifier: str  # phone, email, fb_id, etc.
    content: str
    attachments: list[dict]
    timestamp: datetime
    raw_payload: dict  # original webhook data

async def receive(msg: NormalizedMessage) -> None:
    """Store message, trigger lead capture, optionally trigger AI response."""

async def send(tenant_id: str, session_id: str, content: str, channel: str = None) -> bool:
    """Send outbound message via the correct channel."""
```
Inbound: webhook handlers call `channel_manager.receive()` after normalizing. Receive stores in `chat_messages`, creates/updates conversation, triggers lead extraction, optionally queues AI response.
Outbound: team inbox reply calls `channel_manager.send()`. Channel auto-detected from session_id prefix, or explicitly passed. Dispatches to Twilio (SMS), Facebook API, widget websocket, etc.
**Migration path:** Existing widget.py and twilio_webhooks.py continue working. New channels use the channel_manager from day one. Existing channels migrate incrementally.

### 5B. Migration 056: channel column on conversations
```sql
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS channel TEXT DEFAULT 'widget';
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(tenant_id, channel);
-- Backfill SMS conversations (uses sms_ prefix convention from twilio_webhooks.py)
UPDATE conversations SET channel = 'sms' WHERE session_id LIKE 'sms_%';
```
Note: The `conversations` table uses `tenant_id` (not `client_id`) as its FK column. The `leads` table is the one that uses `client_id`. The index must use `tenant_id`. The backfill UPDATE should be small for most tenants; if table is large, batch with `LIMIT 1000` in a loop.
**Acceptance:** Every conversation has a `channel` value. Existing widget conversations default to 'widget'. SMS conversations correctly tagged.

### 5C. Facebook Messenger integration
**New files:** `backend/routers/channels_facebook.py`, extends `integrations` table or new `channel_configs` table.
**OAuth flow:**
1. Dashboard: "Connect Facebook" button on Integrations page
2. Redirects to Facebook Login (permissions: `pages_messaging`, `pages_manage_metadata`)
3. Callback stores page access token in `integrations` table (provider='facebook')
4. Backend subscribes to page webhook events via Facebook Graph API

**Inbound messages:**
1. Facebook sends webhook to `POST /api/v1/channels/facebook/webhook`
2. Verify signature (app secret HMAC)
3. Normalize to `NormalizedMessage(channel="facebook", session_id="fb_{sender_psid}", ...)`
4. Call `channel_manager.receive()`
5. If AI auto-response enabled: generate response via Claude, send back via Facebook Send API

**Outbound messages:**
1. Team member replies in conversation inbox
2. `channel_manager.send()` detects `channel="facebook"`, calls Facebook Send API with page access token

**Config:** New env vars: `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `FACEBOOK_VERIFY_TOKEN`.

### 5D. Inbox channel filter
**File:** `frontend/src/pages/ConversationsPage.jsx`
**Changes:**
- Add channel filter dropdown: All / Widget / SMS / Facebook (extensible for future channels)
- Each conversation row shows a small channel icon (chat bubble for widget, phone for SMS, Facebook 'f' for Messenger)
- Reply composer auto-selects outbound channel matching the conversation's source channel
- API: `GET /api/v1/inbox/{tenant_id}/conversations` gains optional `?channel=sms` query param
**Acceptance:** Filtering by "SMS" shows only SMS threads. Replying to a Facebook conversation sends via Facebook Messenger, not SMS.

---

## Implementation Order

```
Phase 1 (critical fixes)     → Commit as Cycle 94
Phase 2 (performance)        → Commit as Cycle 95
Phase 3 (quick-win features) → Commit as Cycle 96-97
Phase 4 (code quality)       → Commit as Cycle 98-99
Phase 5 (omnichannel)        → Commit as Cycle 100+
```

Each phase is independently shippable. Phases 1-2 should be done before any deploy. Phases 3-5 can be reordered based on priorities.

## Dependencies

- Phase 1 has no dependencies (all self-contained fixes)
- Phase 2A depends on understanding the automation engine (read-heavy)
- Phase 3B (two-way SMS) benefits from Phase 5A (channel_manager) but can ship standalone first and migrate later
- Phase 4A (widget split) should happen before Phase 5A (channel_manager) so the widget chat logic is already isolated
- Phase 5C (Facebook) requires Phase 5A (channel_manager) and 5B (channel column)

## Out of Scope

- Mobile app (Large, separate project, Q2 2026)
- QuickBooks/Xero integration (Medium, separate spec needed)
- Consumer financing (Medium, requires partner relationship)
- GPS dispatch (Large, depends on mobile app)
- White-label/agency mode (Large, separate spec needed)
- Visual workflow automation builder (Medium-Large, separate spec)

These are captured in the backlog for future design cycles.
