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

### Frontend async error handling must be visible
**Date:** 2026-03-12
**Decision:** Promise chains in dashboard/frontend code must either surface the error to the user, log it with context, or include a short comment explaining why silence is intentional. Empty `.catch(() => {})` and silent `.catch(() => null)` blocks are treated as drift unless explicitly justified.
**Why:** Multiple March 12 UI changes were cleanup passes for hidden failures in save/delete/refresh flows. Silent promise catches make production issues invisible to both operators and users, which slows down debugging and makes health checks look cleaner than reality.
**Enforcement:** `scripts/daily/health-check.sh` now reports `silent_frontend_catch_count`, and daily routines should flag increases.

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

### Reputation Manager: manual-first, API-later
**Date:** 2026-03-12
**Decision:** Reviews are initially added manually (dashboard form) or via future API integrations. The reviews table has `external_review_id` and `platform` fields to support dedup when API integration (Google Business Profile OAuth) is added later. AI draft responses use Claude with business context (name, type) and configurable tone.
**Why:** Google Business Profile OAuth requires app verification which takes weeks. Manual entry provides immediate value — business owners can manage their reviews now while we work on the API integration. The schema is designed for both paths.

---

### Auto review requests: background scan, not event-driven
**Date:** 2026-03-12
**Decision:** Review requests after appointment completion use the same periodic background scan pattern as appointment reminders. `send_pending_review_requests()` runs in the 60s automation loop, checks completed appointments where `review_request_sent_at` is null, respects the configured delay, and sends email/SMS with the tenant's google_review_link.
**Why:** Event-driven scheduling (e.g., scheduling a delayed task when status changes to "completed") adds complexity and requires a task queue or scheduler. The periodic scan pattern is already proven for appointment reminders, handles retries naturally, and works across multiple Uvicorn workers without coordination.

---

### Unsubscribe: HMAC-signed links, no login required
**Date:** 2026-03-12
**Decision:** Unsubscribe links use HMAC-SHA256 signatures (`lead_id` + `api_secret_key`) rather than requiring authentication. The endpoint is public (GET request, returns HTML confirmation). Every automated email includes both a visible unsubscribe link in the footer and a `List-Unsubscribe` header for email clients.
**Why:** CAN-SPAM requires a one-click unsubscribe mechanism. Recipients won't have accounts to log in. HMAC signatures prevent abuse (can't enumerate lead IDs). The `api_secret_key` is per-deployment, so URLs from one deployment don't work on another.

---

### Lead re-engagement campaigns: one-time blast, not sequences
**Date:** 2026-03-12
**Decision:** Campaign blasts are a separate endpoint (`POST /campaigns/send`) from trigger-based sequences. Campaigns query leads with filters (status, score, date range), exclude unsubscribed leads, and send immediately. Max 500 leads per blast to prevent abuse.
**Why:** Sequences are trigger-based (event → delayed steps). Campaigns are action-based (select segment → send now). Different UX, different backend logic. Campaigns reuse `send_email()` and `send_sms()` but don't create executions or logs in the automation tables.

---

### Widget file upload: Supabase Storage, no new migration
**Date:** 2026-03-12
**Decision:** Widget file uploads use Supabase Storage (bucket: `chat-attachments`) instead of a database table. Files stored at `{tenant_id}/{session_id}/{uuid}.{ext}`. Public URLs returned directly from Supabase. Allowed types: images, PDF, Word docs. Max 5 MB. No new migration needed since Supabase Storage is configured separately from PostgreSQL tables.
**Why:** File storage in a database BLOB column is wasteful and slow. Supabase Storage provides CDN-backed public URLs, handles large files efficiently, and scopes by path prefix for easy cleanup. The widget JS shows images inline and other files as download links.

---

### Content Studio: source content → AI repurpose → platform posts
**Date:** 2026-03-12
**Decision:** Content Studio uses a `content_items` table to store source content. Each item has a `source_type` (text/description/file), the raw `source_content`, and a `platform_versions` JSONB field that holds generated per-platform versions keyed by platform name. Status flows: draft → generated → scheduled → published. The AI repurposer (task 2) will populate `platform_versions` from the source content.
**Why:** Storing source and generated versions in the same row keeps them linked. JSONB for platform_versions is flexible — new platforms can be added without schema changes. The draft→generated→published flow gives tenants control over what goes out.

---

### Cloudflare /crawl for website scraping
**Decision:** Use Cloudflare's Browser Rendering /crawl endpoint to automatically scrape customer websites on signup.
**Why:** Launched March 10, 2026. One API call crawls an entire site and returns content as Markdown. Free tier: 5 jobs/day, 100 pages/job. No browser management, no Puppeteer, no infrastructure. Perfect for our use case — we need to crawl one site per signup, extract business info, and feed it to the AI.
**Implication:** Requires a Cloudflare account with Browser Rendering enabled. API token stored as env var. Crawls are async (POST to start, GET to poll). Results cached in website_content table. Content fed to AI knowledge base via Claude API summarization.

---

### Restaurant ordering as vertical feature
**Decision:** Build full restaurant order-taking as a first-class feature, not an afterthought.
**Why:** Restaurants are one of our primary target verticals. Order-taking through the chat widget is a massive differentiator — most chatbot platforms can answer questions but can't take orders. This turns the widget from a lead capture tool into a revenue-generating tool for the restaurant.
**Implication:** Menu management, order processing, and order notifications are restaurant-specific features gated behind business type selection. The menu can be auto-imported from the website crawl, reducing setup friction. Orders flow through the same dashboard as leads and conversations.

### Content repurposer — single Claude call for all platforms
**Decision:** Generate all 6 platform versions (LinkedIn, Facebook, Instagram, GBP, email, Twitter/X) in a single Claude API call rather than 6 separate calls.
**Why:** 6 separate calls would be 6x the latency and cost. Claude handles multi-output well with delimiter-based parsing. Fallback parsing (positional split) handles cases where the model doesn't follow delimiter format exactly.
**Implication:** Response parsing must be robust — primary parser checks for `===PLATFORM===` delimiters, fallback splits by the delimiter and assigns positionally. Platform specs are defined as a dict constant for easy extension.

### Team role enforcement — dependency-based, not middleware
**Decision:** Use FastAPI's `require_role()` dependency factory rather than global middleware for role-based access control.
**Why:** Dependency-based enforcement is explicit per-endpoint, allowing different role requirements per route. Middleware would require pattern-matching on URLs which is fragile. The `require_role()` function wraps `_get_current_tenant()`, so it's a drop-in replacement.
**Implication:** When adding new write endpoints, always use `require_role("owner", "admin")` instead of `_get_current_tenant()`. Read endpoints can remain with `_get_current_tenant()` since all roles should be able to view data. The role hierarchy is: owner > admin > member > viewer.

### Website crawl pipeline — Cloudflare Browser Rendering + sync execution
**Decision:** Use Cloudflare Browser Rendering `/crawl` API for website scanning. The crawl executes synchronously in the POST endpoint (up to 120s timeout), storing results in `website_content` table. Crawled content is injected into the AI system prompt (truncated to 8KB).
**Why:** Async polling adds complexity for v1. The Cloudflare API handles JavaScript rendering, which is needed for modern websites. The 120s httpx timeout covers most sites. Storing raw pages as JSONB allows re-processing later without re-crawling.
**Implication:** The crawl endpoint will block for up to 2 minutes on slow sites. The frontend shows "Scanning..." state during this time. If Cloudflare credentials aren't configured, the crawl fails gracefully with a helpful message pointing users to manual FAQ entry. Website content is cached in DB — not re-fetched on every chat message.

---

### Order extraction from chat — HTML comment marker pattern
**Decision:** When the AI confirms a restaurant order, it appends a hidden `<!--ORDER_JSON:{...}-->` marker to its response. The backend extracts this JSON, strips the marker from the user-visible text, and processes the order as a background task (DB insert + SMS/email notifications to owner + SMS confirmation to customer).
**Why:** Tool-use would require changing the entire chat API structure. Post-hoc regex scanning of natural language is fragile. The HTML comment marker is invisible in the widget (even if rendered raw), reliably parseable, and the AI follows the format consistently. Order creation + notifications run as background tasks so chat response isn't delayed.
**Implication:** MAX_TOKENS increased to 700 to accommodate the JSON block. If the AI doesn't output the marker (malformed, truncated), the order is lost — but the conversation still records what was discussed so the owner can manually create it. The `order.created` webhook event is fired for Zapier integrations.

---

### Competitor analysis: Quo (formerly OpenPhone)
**Date:** 2026-03-13
**What they do:** AI-powered business phone system. $105M funded. 90K+ businesses. Key features: Sona AI voice agent, call transcription/summaries, AI call tags, auto-replies, shared inbox, visual call flow builder, analytics, CRM integrations.
**What we're taking:** AI conversation tags, action item extraction, shared team inbox, visual chat flow builder, analytics upgrade, snippets/quick replies, AI contact suggestions, call transcription & summaries (extending our AI Answering Service module), MCP integration. Adapted for our chat-first (not phone-first) platform.
**Our advantage:** We're chat-first + website widget + lead capture + appointment booking + CRM in one. Quo is phone-first and charges $15-35/user/month. We can offer more for less because our AI handles chat AND voice AND SMS in one widget. Quo requires separate CRM (HubSpot/Salesforce) — we have CRM built in. Quo's visual call flow builder routes phone calls — our visual chat flow builder routes chat conversations (lower barrier, no phone hardware needed).
**What we're NOT taking:** Phone number provisioning (we already plan this in the AI Answering Service module), Sona AI voice agent (we have our own voice module planned), CRM integrations (we ARE the CRM — no need to sync to HubSpot/Salesforce for our target market).

---

### Chat flow engine: prompt injection, not hard-coded routing
**Date:** 2026-03-14
**Decision:** The chat flow engine works by injecting flow instructions into the AI system prompt, not by implementing a hard-coded state machine that intercepts messages. When a tenant has an active flow, the flow's nodes and edges are translated into natural language instructions appended to the system prompt.
**Why:** A hard-coded flow engine would need to track conversation state, evaluate conditions, and handle edge cases — all of which the AI already handles naturally. By translating the flow into instructions, we get the benefits of structured conversation flow while keeping the AI's ability to handle unexpected questions. The AI can deviate from the flow when appropriate (e.g., answering an urgent question mid-flow) and return to it naturally.
**Implication:** Flow "conditions" are keyword-based triggers in the prompt, not regex evaluations. The AI interprets them flexibly. Flow "actions" like "show booking" become instructions to offer appointment booking. This means flows guide behavior rather than enforce it strictly — acceptable for v1, may need tightening if customers want strict routing.

### AI snippet suggestion: index-based response, not semantic search
**Date:** 2026-03-14
**Decision:** The snippet suggestion endpoint sends all snippets (up to 20) to Claude along with the conversation context and asks it to return the index number of the best match. No vector database, no embeddings, no semantic search.
**Why:** With <100 snippets per tenant, sending the full list to Claude is fast and cheap (one API call with ~2K tokens). Vector search would require embedding infrastructure and wouldn't be significantly better at this scale. The Claude-based approach understands nuance (e.g., a "We're closed on Sundays" snippet matching a "Do you work weekends?" question) that keyword matching would miss.

### Response time tracking: per-first-exchange, not per-message
**Date:** 2026-03-14
**Decision:** Response time is measured once per conversation — the time between the first user message and the first assistant response. Subsequent messages are not tracked for response time.
**Why:** For AI-powered chat, every message gets an instant response. The meaningful metric is how quickly the AI responds to the initial contact. For team replies, the response time would be from the customer's message to the team member's reply, but this requires tracking which messages are from team members vs AI — deferred to a future iteration.

### Widget config TTL cache: per-worker, 5-minute expiry
**Date:** 2026-03-15
**Decision:** Widget config, tenant data, FAQ entries, business hours, AI corrections, and website content are cached in-memory with a 5-minute TTL. The cache is per-worker (4 Uvicorn workers = 4 separate caches).
**Why:** The widget config endpoint is the hottest path — called on every page view. FAQ/hours/corrections are loaded on every chat message but rarely change. A 5-minute TTL means changes propagate within 5 minutes (acceptable for config data). Per-worker cache avoids shared state complexity.
**Implication:** Config changes (widget settings, FAQ updates, feedback corrections) take up to 5 minutes to take effect. If a user reports "I changed my greeting but it didn't update", wait 5 minutes. The cache auto-evicts after TTL — no manual invalidation needed.

### Lead update suggestions: activity_log, not separate table
**Date:** 2026-03-15
**Decision:** AI-generated lead update suggestions (when new info conflicts with existing lead data) are stored in the `activity_log` table with `activity_type = "lead_suggestion"` and proposed changes in `metadata.suggestions`. No separate table.
**Why:** Avoids a migration for a lightweight feature. activity_log already has tenant_id, lead_id, metadata JSONB. Suggestions are ephemeral — approved or dismissed, then deleted. The volume is low (only on conflicting data, not every extraction).
**Implication:** Suggestions appear alongside other activity items. The GET /suggestions endpoint filters by activity_type. If suggestion volume grows, consider a dedicated table.

### Onboarding emails: time-window queries, not event-driven
**Date:** 2026-03-15
**Decision:** Onboarding drip emails use time-window queries on `tenants.created_at` (e.g., created 23-26 hours ago → Day 1 email). Deduplication via activity_log entries.
**Why:** Event-driven would require a new event system or Stripe-style webhook pipeline. Time-window is simple and runs in the existing automation loop. The 3-hour window (e.g., 23-26h) tolerates clock drift and loop intervals. activity_log dedup prevents re-sends across worker restarts.

### MCP server: widget API key auth, not separate tokens (v1)
**Date:** 2026-03-15
**Decision:** The MCP server accepts both widget API keys (anx_*) and dedicated MCP keys (mcp_*). V1 launched with widget keys for simplicity; dedicated MCP keys were added in the same session.
**Why:** Shipping fast with existing auth was more important than perfect security. Widget keys are already per-tenant and rate-limited. MCP keys add a second auth path with explicit opt-in (mcp_enabled flag).

### AI voice handler: Twilio Gather/Say loop, not Media Streams
**Date:** 2026-03-15
**Decision:** The AI phone answering service uses Twilio's `<Gather input="speech">` → `<Say>` loop (3 rounds max) rather than Twilio Media Streams for real-time bidirectional audio.
**Why:** Media Streams requires WebSocket handling, audio chunking, and a streaming-capable AI model. The Gather/Say approach works with standard HTTP webhooks and the existing sync Claude API. Latency is higher (~3-5s per turn) but acceptable for v1. Can upgrade to Media Streams + streaming Claude in a future iteration.

### PDF bids: HTML invoice, not weasyprint/reportlab
**Date:** 2026-03-15
**Decision:** Bid PDFs are generated as styled HTML documents with print-friendly CSS, served with a download content-disposition header. The browser's "Print to PDF" handles the actual PDF creation.
**Why:** Adding weasyprint or reportlab as dependencies would increase Docker image size by 100MB+ and require system-level packages (cairo, pango). The HTML approach is zero-dependency, looks professional, and lets the user customize before printing. Can add server-side PDF generation later if needed.

### GBP OAuth: scaffold built, awaiting credentials
**Date:** 2026-03-15
**Decision:** The Google Business Profile OAuth flow is fully implemented (auth URL generation, callback token exchange, profile fetch, post scaffold) but non-functional until Google API credentials are configured.
**Why:** Building the code now means the feature is "one config change away" from working. When Google API approval comes through, we just add the client_id and client_secret to env vars — no code changes needed.

### Background automation: 9 tasks in one loop, staggered workers
**Date:** 2026-03-15
**Decision:** All 9 background automation tasks (sequences, reminders, reviews, onboarding, monthly reports, portal links, missed calls, review alerts, no-response) run in a single asyncio loop with 60-second intervals and 0-30s random worker stagger.
**Why:** Simple to operate (one loop, one log stream), each task has its own try/except so failures are isolated, and the stagger reduces duplicate execution across 4 Railway workers. Individual tasks are idempotent (dedup checks). If any task becomes too slow, it can be extracted to its own loop or Railway cron job.

### Public embeddable pages: server-rendered HTML from FastAPI
**Date:** 2026-03-20
**Decision:** Public embeddable content (booking page, public forms) is rendered as self-contained HTML responses from FastAPI endpoints, not as React routes. The HTML includes inline CSS and vanilla JS — no external dependencies.
**Why:** Embeddable content loaded in iframes on third-party websites can't depend on our React app or build system. Self-contained HTML with inline styles ensures the embed works regardless of the host page's CSS or JS. The booking page (booking_page.py) and forms embed (forms.py /embed) both follow this pattern.

### Pipeline board: backend-driven stages, not frontend constants
**Date:** 2026-03-20
**Decision:** The Pipeline page fetches stages from `GET /pipeline/{tenantId}/board` instead of using hardcoded stage constants. The backend seeds default stages on first access and supports custom stages per tenant.
**Why:** Hardcoded frontend stages ("new", "contacted", "quoted", "won", "lost") didn't match backend defaults ("New Lead", "Contacted", "Qualified", "Proposal Sent", "Won", "Lost"), causing lead grouping failures. Making the frontend dynamic enables future per-tenant pipeline customization.

### Conversation lookup: dual-key resolution (UUID + session_id)
**Date:** 2026-03-20
**Decision:** The `_find_conversation()` helper in conversation_inbox.py tries UUID lookup first, then falls back to session_id + client_id. This accommodates both internal callers (using UUID) and the frontend (which tracks conversations by session_id).
**Why:** The ConversationsPage stores and passes `session_id` as the conversation identifier, but the backend originally expected the UUID primary key. Rather than changing the frontend (which would require the conversations list to include the UUID alongside session_id and a refactor of all state management), the backend now accepts either.

### Emergency detection in lead scoring — force "hot" temperature
**Date:** 2026-03-19
**Decision:** Added `_EMERGENCY_KEYWORDS` list separate from `_URGENCY_KEYWORDS`. Emergency keywords (leak, flood, broken, etc.) add +15 to intent score AND force `lead_temperature = "hot"` regardless of total score. This is a product-level decision: a lead saying "my pipe burst" should always be treated as hot even if they haven't provided contact info yet.
**Why:** Service businesses (plumbers, HVAC, electricians) need emergency leads flagged immediately. The standard scoring algorithm might rate a brand-new lead with emergency language as "warm" (low engagement score), but the business owner needs to see it immediately.

### One-click review request — immediate send, no delay
**Date:** 2026-03-19
**Decision:** The `POST /reviews/{tenant_id}/request-review/{lead_id}` endpoint sends review requests immediately (no delay_hours check). This is intentional: the automated `send_pending_review_requests` function respects the configured delay, but the manual one-click action represents explicit user intent and should fire instantly.
**Why:** When a business owner clicks "Request Review" on a lead, they've already decided it's the right time. Adding a delay would be confusing.

### Business-type-aware reminder extras
**Date:** 2026-03-21
**Decision:** Appointment reminders include business-type-specific "bring" items via a `_REMINDER_EXTRAS` dict in automation_engine.py. Only 24h reminders get the extras (1h is too late to prepare). Dental root canal/surgery adds "arrange a ride home" dynamically based on notes content.
**Why:** Generic reminders ("your appointment is tomorrow") miss the chance to reduce no-shows. A dental patient who forgets their insurance card wastes 15 minutes at the front desk.

### Form presets — one-click industry forms
**Date:** 2026-03-21
**Decision:** Form presets are hardcoded in `_FORM_PRESETS` dict in forms.py rather than stored in a separate database table. Each preset defines name, description, fields, and success_message. The `POST /presets/{preset_key}` endpoint creates a real form from the preset.
**Why:** Presets rarely change and don't need per-tenant customization of the template itself. Storing them in code avoids a migration and keeps the system simple. Business owners customize after creation.

### HIPAA-aware AI system prompt for healthcare
**Date:** 2026-03-21
**Decision:** For dental/medical business types, the widget AI system prompt includes a HEALTHCARE PRIVACY block that instructs the AI to handle health information professionally, not store or repeat medical details, and recommend patients complete a health history form. This is a system prompt instruction, not a hard filter.
**Why:** Healthcare businesses need basic privacy awareness in their AI. A full HIPAA compliance implementation would require audit trails, BAAs, and encryption — but prompt-level instructions handle the most common issue: AI casually repeating sensitive health info.

### api.js split into domain modules — COMPLETED
**Date:** 2026-03-21 (started), 2026-03-22 (completed)
**Decision:** Split the 1347-line monolithic `api.js` into 35 domain modules in `frontend/src/utils/api/`. The monolith has been deleted. All 257 API functions now live in domain-specific files. A barrel `index.js` re-exports everything for backwards compatibility.
**Why:** api.js was the #1 merge conflict hotspot. Domain modules isolate changes so invoice changes don't conflict with document changes. Bundle improved -18.3% (113.8 → 93 kB) via better tree-shaking.
**Modules (35):** leads, invoices, documents, pipeline, reviews, content, appointments, webhooks, team, social, campaigns, jobs, bids, forms, conversations, analytics, automations, menu, seo, calls, portal, smart-lists, dashboard, faq, widget-config, crm, action-items, inbox, snippets, tags, chat-flows, business-page, integrations, phone, misc + _client (shared).
**Pattern:** Each module imports `request` from `./_client.js` and exports named functions. New API functions go in the appropriate domain module. The barrel `index.js` re-exports all modules.

### Scheduled content auto-execution via automation loop
**Date:** 2026-03-22
**Decision:** Social media posts and marketing campaigns with `scheduled_for <= now()` are automatically processed by two new functions in the main.py automation loop (`_process_scheduled_posts`, `_process_scheduled_campaigns`). Posts get status updated to 'published'. Campaigns go through the same send flow as manual sends. Both run every 5 minutes (tick % 5).
**Why:** Previously, scheduling was UI-only — setting `scheduled_for` just stored a timestamp but nothing ever checked it. Users had to manually click Send/Publish. The automation loop already runs dozens of background tasks on tiered schedules, so this fits the existing pattern. When platform OAuth is added later, `_process_scheduled_posts` is the hook point for actual API publishing.

### White-label client login — portal tokens as proof of identity
**Date:** 2026-03-22
**Decision:** Clients register for a login using their existing portal token as proof they're a real customer. The portal token (magic link) validates their identity once, then they create email+password credentials stored in `client_accounts`. Login is scoped by `business_slug` so clients of different businesses have separate namespaces. Client JWTs use `scope: "client"` to distinguish from tenant JWTs. The `/client/me` endpoint returns a richer dataset than the public portal (includes appointments, invoices, documents in addition to service records).
**Why:** Magic links are one-time use and inconvenient for repeat access. Clients need persistent login to check appointments, pay invoices, and sign documents. Using the portal token for registration avoids needing a separate verification flow. The business_slug scoping ensures email uniqueness is per-business, not global.

### Competitor analysis — AI-estimated scores, no external APIs
**Date:** 2026-03-22
**Decision:** Competitor analysis uses Claude to estimate SEO scores and compare businesses rather than pulling real data from SEMrush/Ahrefs APIs. The endpoint accepts up to 5 competitor names, fetches the tenant's existing SEO audit score for context, and asks Claude to provide estimated scores, strengths, weaknesses, threat levels, gaps, advantages, and recommendations. JSON response format with markdown fence stripping.
**Why:** External SEO APIs cost per-query and require API keys most small businesses won't have. Claude's general knowledge provides useful directional analysis. If real SERP data is added later (backlog item), it can supplement the AI analysis rather than replace it.

### API call consistency — all page components should use API utility modules
**Date:** 2026-03-22
**Decision:** Frontend pages must use the centralized API utility functions from `frontend/src/utils/api/` rather than raw `fetch()` calls. Exception: endpoints returning non-JSON responses (blobs, streams) may use raw fetch since the `request()` client always parses JSON.
**Why:** Raw fetch scattered across pages duplicates the base URL, auth header, and error handling logic. Using the API utils ensures consistent error handling via `ApiError`, avoids hardcoded URLs, and makes it easy to add auth token refresh or request interceptors later.

_Add new decisions when significant architectural choices are made._
