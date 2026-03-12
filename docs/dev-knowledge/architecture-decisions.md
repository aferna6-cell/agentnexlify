# Architecture Decisions — AgentNexLiFy

Why key technical choices were made. Claude Code reads this to avoid undoing intentional decisions.

---

### Multi-tenant from day one
Every table has tenant_id (or client_id for leads). All queries filter by it. Non-negotiable.

### FastAPI + Supabase (no ORM)
Direct Supabase client, not SQLAlchemy. Raw SQL migrations, not Alembic. Simpler, more explicit.

### React/Vite on Vercel, FastAPI on Railway
Separate hosting. CORS required for cross-origin API calls. Frontend is React/Vite (not Next.js).

### JWT for auth only, API for display data
JWT claims don't refresh when plan changes. Display data (plan name, usage counts) must come from live API calls.

### Widget as embeddable script
Lowest friction for customers. Works on any website via script tag. CORS must allow customer domains. Widget uses data-api-key attribute for tenant identification.

### Widget file sync requirement
widget/agentnexlify-widget.js and frontend/public/widget/agentnexlify-widget.js must be identical. Both serve the widget from different contexts.

### Numbered SQL migrations
Manual numbering in migrations/. Simple, explicit, no tooling dependency. Note: duplicate numbers exist at 005 and 007 (historical).

### chat_messages as canonical store
Migration 006 created chat_messages as the reliable message store. The older conversations table (migration 001) stores messages as JSONB and is considered unreliable.

### 4 Uvicorn workers in production
In-memory counters, caches, and background loops are per-process only. Do not treat them as globally authoritative.

### No setup fees, free tier prominent
Partner feedback: setup fees scare small businesses. Volume strategy.

### Only show built features on website
Trust-building. Don't market features that don't work yet.

### Businesses with no website = key market
Hosted business pages (agentnexlify.com/biz/{slug}) for businesses without websites. Added in migration 009.

### Plan naming
Canonical: free, growth ($199), professional ($399), enterprise ($799). Old names foundation and operations were renamed in migration 013.

### Unlimited conversations
Migration 013 cleared conversation limits. All plans now have unlimited conversations.

---

### Exception handling strategy
**Date:** 2026-03-11
**Decision:** Every `except` block must either (1) log the exception, (2) re-raise it, or (3) have a comment explaining why silence is intentional. Never use `except BaseException:` — always use `except Exception:` to allow `KeyboardInterrupt`, `SystemExit`, and `asyncio.CancelledError` to propagate for clean shutdown.
**Why:** 10 `except BaseException:` blocks in widget.py were preventing graceful Uvicorn shutdown. One was `except BaseException: pass` that silently swallowed lead scoring failures. Silent except blocks in analytics.py hid database errors.
**Enforcement:** Pre-commit hook checks for bare excepts. The QA agent audits for this pattern.

---

### lead_stage_change is an event name, not a column name
**Date:** 2026-03-11
**Decision:** Keep `lead_stage_change` as the automation trigger event name, even though the actual column is `status` (not `lead_stage`). The trigger event is a business concept stored in `automation_sequences.trigger_event` TEXT column.
**Why:** Renaming to `lead_status_change` would break existing data in production. The name is well-understood and only used as a string constant, never as a DB column filter.

---

### Email templates: stored per-tenant with starter gallery
**Date:** 2026-03-12
**Decision:** Email templates are stored in a per-tenant `email_templates` table, with a set of built-in starter templates served from Python constants (not DB). The SequenceBuilder loads both and presents them in a unified picker.
**Why:** Business owners need reusable templates but shouldn't be forced to create from scratch. Starter templates provide instant value without DB seeding. Per-tenant storage allows customization while starter templates are always available.

---

### Appointment reminders: background loop, not sequence-based
**Date:** 2026-03-12
**Decision:** Appointment reminders use a dedicated `send_appointment_reminders()` function in the automation loop, not the sequence/execution system. Reminders are tracked via tags in the appointment's `notes` field.
**Why:** Sequence-based reminders trigger relative to enrollment time, but reminders need to fire relative to appointment start time. A dedicated function queries appointments in specific time windows (24h and 1h before) and sends directly. Using notes tags for dedup avoids a new DB table while being reliable.

---

### Multi-language: prompt-based, not detection-based
**Date:** 2026-03-12
**Decision:** Multi-language support is implemented by instructing Claude to match the visitor's language in the system prompt, rather than running language detection on the input.
**Why:** Claude inherently understands the language being used and can respond in kind. Adding a separate detection step (langdetect, etc.) adds complexity and latency for no benefit since Claude handles it natively.

---

### Widget offline mode: config-driven with contact form fallback
**Date:** 2026-03-12
**Decision:** Widget offline mode is controlled by an `is_online` boolean in `widget_configs`. When offline, the widget JS hides the chat input and shows a contact form (name, email, phone, message). Submissions create a lead via `POST /api/v1/widget/offline-contact`. The toggle is in the WidgetPage settings UI.
**Why:** Small businesses need control over when their widget is active. After hours or during vacations, a contact form captures leads without the AI generating responses. The toggle is instant (no page reload), and the widget checks status on load via the existing config endpoint.

---

### Dashboard notifications: query-time aggregation, no notifications table
**Date:** 2026-03-12
**Decision:** The notifications center aggregates data at query time from `leads`, `chat_messages`, `appointments`, and `activity_log` — there is no dedicated `notifications` table. The bell polls every 60s and shows new leads (24h), conversations, today's appointments, and recent activity.
**Why:** A separate notifications table would need triggers/workers to populate. Query-time aggregation is simpler and always reflects the latest state. For the current scale (small businesses with <100 leads/day), the queries are fast enough. If perf becomes an issue, we can add materialized views or a notifications table later.

---

### Lead auto-tagging: AI extraction during lead capture
**Date:** 2026-03-12
**Decision:** Auto-tags are extracted from conversation transcripts using a Claude API call during `_capture_leads_from_session()`. Tags are stored as a `TEXT[]` column on the leads table with a GIN index. Extraction runs in the background task (not in the chat response path) so it doesn't affect latency. Max 5 tags per lead, max 40 chars each.
**Why:** Tags like "interested in: kitchen remodel" or "budget: high" give business owners instant context without reading the full conversation. Using Claude for extraction (rather than keyword matching) captures nuanced intent. Running in the background task means zero latency impact on the chat widget. TEXT[] with GIN index enables efficient PostgreSQL array queries for future tag-based filtering.

---

### Recurring appointments: parent-child model
**Date:** 2026-03-12
**Decision:** Recurring appointments use a parent-child model. The original appointment becomes the "parent" with `recurrence_rule` and `recurrence_end_date` set. Future instances are generated immediately as separate appointment rows with `recurrence_parent_id` pointing to the parent. Each instance is independently editable (can be cancelled, rescheduled, completed individually).
**Why:** Generating all instances upfront (vs. lazy generation) keeps the calendar view simple — no special rendering logic needed, all appointments exist as normal rows. Independent instances mean cancelling one occurrence doesn't affect the series. The DB double-booking EXCLUDE constraint naturally prevents conflicts. CASCADE delete on `recurrence_parent_id` means deleting the parent cleans up all instances.

---

### Lead merge: keep-and-absorb pattern
**Date:** 2026-03-12
**Decision:** Lead merge uses a "keep-and-absorb" pattern: one lead is kept (primary), the other is absorbed (fills in missing fields, unions tags, keeps higher score) and then deleted. Related records (appointments, activity_log, client_notes) are reassigned to the kept lead via UPDATE. Duplicates detected by exact email or phone match.
**Why:** Simple and reversible (activity log records the merge). Reassigning related records preserves history. Filling missing fields means no data is lost. Union of tags captures all context from both leads.

---

### AgentNexLiFy as complete business operating system
**Decision:** Phone answering, missed call text-back, contractor bids, client portal, review responding, and business autopilot are all built as integrated modules, not separate products.
**Why:** Every module shares the same customer data. A missed call becomes a text conversation becomes a lead becomes an appointment becomes a service record becomes a review request. The data flows in a circle. This is impossible if they're separate products. The more modules a customer uses, the more their business depends on the platform — churn approaches zero.
**Implication:** All modules share: tenant system, auth, leads table, appointments table, conversation engine (widget + SMS + voice all use the same AI backend). The chat/AI engine becomes a universal interface — customers interact via widget, SMS, or phone and it all funnels into the same dashboard. New channel type field on conversations: 'widget' | 'sms' | 'voice'.

---

### All-in-one platform, not separate products
**Decision:** Reputation management, outreach, content, SEO, and job board are built as modules within AgentNexLiFy, not as separate products.
**Why:** Same customer base. One sale, one login, one subscription. Reduces churn because the platform becomes the business's operational backbone. Compound workflows create deep moats — a customer won't leave if their reviews, outreach, content, SEO, and hiring all live here.
**Implication:** Each module shares the tenant system, auth, and dashboard shell. Modules can be gated by pricing tier. Data flows between modules (e.g., completed appointment triggers review request, lead capture triggers outreach sequence, content studio feeds GBP posts).

---

_Add new decisions when significant architectural choices are made._
