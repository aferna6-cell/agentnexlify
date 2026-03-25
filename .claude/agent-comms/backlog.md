# AgentNexLiFy Work Backlog

_The continuous loop reads this file every cycle and works top to bottom within each section. Add tasks anytime — the loop picks them up automatically._

_Last updated: 2026-03-23_

---

## Features — CTO-Researched Competitive Features (2026-03-25, BUILD AFTER SITE FIXES)

_Priority order: streaming > voice > quoting > review autopilot > agency > business brain_

- [ ] **[CTO-RESEARCHED] Widget Streaming Responses with Claude SSE** — SSE streaming for chat widget so users see tokens in real-time. Use Claude streaming API with `thinking.display: "omitted"`. Target: first visible token in <500ms. Files: widget chat components, backend chat.py, claude_service.py.
- [ ] **[CTO-RESEARCHED] AI Voice Channel (Vapi/Retell Integration)** — AI phone answering using same knowledge base as chat widget. Calls forwarded after 3 rings, transcribed, logged in dashboard alongside chat. Create voice_service.py, voice.py router, VoiceCallLog/VoiceSettings UI.
- [ ] **[CTO-RESEARCHED] Instant Quote Engine for Service Businesses** — AI-powered quoting in chat widget. Customer describes problem, AI asks qualifying questions, generates ballpark estimate from configured pricing. Create quote_engine.py, ServiceCatalog UI, QuoteSettings, QuoteDisplay widget component.
- [ ] **[CTO-RESEARCHED] Review Response Autopilot** — One-click AI-generated review responses matching business voice. Negative reviews get empathetic handling, positive get grateful tone. Enhance ReviewManagement UI, review_response_service.py.
- [ ] **[CTO-RESEARCHED] Agency/Reseller Multi-Tenant Architecture** — Database schema and API for agency/reseller accounts. Platform > Agency > Business hierarchy. Wholesale pricing. Create agency.py model/router/service.
- [ ] **[CTO-RESEARCHED] Business Brain (Unified AI Knowledge Context)** — Vector store per tenant with automatic ingestion from all interactions. Every interaction feeds knowledge graph. Create knowledge_service.py, embedding_service.py, knowledge_entry model.

## Features — Tier 0: Quo-Inspired Competitive Features (BUILD FIRST)

_Inspired by Quo (formerly OpenPhone) — an AI-powered business phone system serving 90K+ businesses. These features differentiate us from every other chatbot widget. Adapted for our chat-first platform._

### AI Conversation Tags (Auto-Categorization)

_Every chat and call conversation is auto-categorized by AI into business-meaningful tags: "New Lead", "Pricing Question", "Complaint", "Appointment Request", "Urgent", "Follow-up Needed". Business owners can create custom tags. Dashboard filters by tag._

**Why this matters:** Quo auto-tags every call so managers get instant insights without manual logging. We should do the same for every chat conversation. This is different from our existing lead auto-tagging (which extracts freeform tags like "interested in: kitchen remodel") — this is preset business categories applied to conversations.

**What we already have:** Lead auto-tagging (freeform, done), conversation manual tagging (done). What's missing: AI auto-categorization of conversations into preset business categories, custom tag definitions per tenant, tag distribution analytics.

- [x] **Migration: tenant_tag_definitions table** — DONE (migration 032, 2026-03-14). Needs manual application in Supabase.
- [x] **AI auto-categorization in chat pipeline** — DONE (widget.py, runs every 5th message as background task, 2026-03-14)
- [x] **Custom tag management UI** — DONE (SettingsPage.jsx, color picker, system/custom badges, enable/disable, 2026-03-14)
- [x] **Tag filtering on ConversationsPage** — DONE (ConversationsPage.jsx, dropdown with counts, colored tag pills, 2026-03-14)
- [x] **Tag distribution analytics** — DONE (AnalyticsPage.jsx, Recharts bar chart with per-tag colors, 2026-03-14)

### AI Action Item Extraction

_After every conversation (chat or call), AI extracts actionable items: "Customer wants a quote for kitchen remodel by Friday", "Schedule follow-up call for Tuesday", "Send menu PDF". These appear as tasks on the dashboard._

**Why this matters:** Quo extracts action items from every call transcript. Business owners forget follow-ups — this catches everything. Turns passive conversation history into an active to-do list.

**What we already have:** Nothing. Activity log tracks what happened, but doesn't extract what needs to happen next.

- [x] **Migration: action_items table** — DONE (migration 033, 2026-03-14). Needs manual application in Supabase.
- [x] **AI extraction in chat pipeline** — DONE (widget.py, runs every 8th message as background task, 2026-03-14)
- [x] **Action items dashboard widget** — DONE Cycle 31. ActionItemsPage + dashboard summary endpoint.
- [x] **Action items page** — DONE Cycle 31. Full page with filters, status/priority, assign, bulk actions (723-line ActionItemsPage.jsx).
- [x] **Action item notifications** — DONE Cycle 31. Notification bell includes action items via /notifications aggregation.

### Shared Team Inbox

_Multiple team members can see and respond to the same conversations. Internal notes (customer doesn't see). Assign conversations to specific team members. Show who is currently handling what._

**Why this matters:** Quo's shared inbox is their #1 collaboration feature. Currently our team members can see conversations but can't take ownership, leave internal notes, or see who's handling what. Real businesses need handoff between team members.

**What we already have:** Team members (done), lead assignment (done), conversation list (done). What's missing: conversation assignment, internal notes on conversations, real-time presence (who's handling what), team member reply to conversations.

- [x] **Migration: conversation assignment + internal notes** — DONE (migration 034, 2026-03-14). Needs manual application in Supabase.
- [x] **Conversation assignment endpoint** — DONE (PUT /api/v1/inbox/{tenant_id}/conversations/{id}/assign, 2026-03-14)
- [x] **Internal notes endpoints** — DONE (POST/GET/DELETE via /api/v1/inbox, 2026-03-14)
- [x] **Team inbox UI** — DONE (ConversationsPage upgraded: assignment dropdown, internal notes panel, "My/All" filter, 2026-03-14). Partial — presence badges not yet integrated.
- [x] **Team member reply to conversation** — DONE (POST /api/v1/inbox/{tenant_id}/conversations/{id}/reply, inserts into chat_messages + conversations JSONB, 2026-03-14)
- [x] **Presence indicators** — DONE (backend: migration 035, PUT/GET /api/v1/inbox/{tenant_id}/presence, 2026-03-14). Frontend presence display not yet integrated.

### Visual Chat Flow Builder

_Drag-and-drop builder for customizing the chat widget's conversation flow. "If customer asks about pricing -> show pricing card. If customer wants appointment -> show booking form. If after hours -> collect info and promise callback."_

**Why this matters:** Quo has a visual call flow builder for phone routing. Our equivalent: a visual chat flow builder that lets business owners customize their widget's behavior without touching code. This is a massive differentiator — no other chat widget platform offers this for small businesses.

**What we already have:** Widget config (greeting, colors, position). The AI handles all routing via system prompt. What's missing: visual builder for defining custom flows, conditional logic, and special actions.

- [x] **Migration: chat_flows table** — DONE (migration 038, 2026-03-14)
- [x] **Chat flow engine in widget backend** — done 2026-03-14. Widget checks active flow, evaluates conditions, falls back to AI. Cycle 38.
- [x] **Visual flow builder page** — done 2026-03-15. ChatFlowBuilderPage with @xyflow/react drag-and-drop editor, 6 node types, node editor panel, template creation. Cycle 40.
- [x] **Preset flow templates** — DONE (3 templates: General Business, Restaurant, Contractor, stored in backend with one-click create, 2026-03-14)
- [x] **Flow analytics** — DONE 2026-03-15 Cycle 63. GET /analytics endpoint with daily usage, per-node stats, improvement suggestions. Activity tracking on flow usage.

### Analytics Dashboard Upgrade

_Call volume, chat volume, response time, missed opportunities, lead conversion rate, AI tag distribution, per-agent metrics, busiest hours heat map._

**Why this matters:** Quo's analytics show call patterns, missed call rates, and per-agent performance. Our current analytics are basic — we need the metrics that help business owners make decisions.

**What we already have:** Basic stats (lead count, conversation count, appointment count). Email open tracking. Review analytics. What's missing: response time tracking, missed opportunity detection, conversion funnel, busiest hours, per-team-member metrics, heat map.

- [x] **Migration: response_metrics table** — DONE (migration 037, 2026-03-14)
- [x] **Response time tracking** — DONE (widget.py records metrics on first exchange, analytics endpoint at GET /response-times, 2026-03-14)
- [x] **Analytics page redesign** — DONE (response time trend chart, lead conversion funnel, busiest hours heat map, 2026-03-14)
- [x] **Missed opportunity detection** — DONE (GET /missed-opportunities with 3 signal types, cached, 2026-03-14)

### Snippets / Quick Replies

_Pre-written response templates for common questions. Business owner creates them, team members send with one click. AI can also suggest which snippet to use._

**Why this matters:** Quo has "Snippets" — saved replies that send complete messages with one click. We have email templates for sequences, but nothing for live conversations. Team members answering chats need quick access to standard responses.

**What we already have:** Email templates (for automation sequences). What's missing: quick reply snippets for live chat/SMS conversations, AI snippet suggestions.

- [x] **Migration: snippets table** — DONE (migration 036, 2026-03-14)
- [x] **Snippets CRUD endpoints** — DONE (backend/routers/snippets.py, 2026-03-14)
- [x] **Snippets management page** — DONE (SnippetsPage.jsx with category tabs, search, shortcuts, 2026-03-14)
- [x] **Snippet picker in team inbox** — DONE (ConversationsPage: lightning bolt button + "/" shortcut trigger, search, category badges, 2026-03-14)
- [x] **AI snippet suggestion** — DONE (POST /api/v1/snippets/{tenant_id}/suggest, uses Claude to match conversation context to best snippet, 2026-03-14)

### AI Contact Suggestions (Enhanced Lead Capture)

_When the chatbot talks to someone, extract their name, phone, email, business need from the conversation. Auto-suggest adding them as a lead. Auto-populate lead fields from conversation context._

**Why this matters:** Quo auto-identifies contact details in conversations and suggests adding/updating contacts. Our lead capture already extracts some info, but it's one-shot — it doesn't continuously watch for new details mentioned later in the conversation, and it doesn't suggest updates to existing leads.

**What we already have:** Lead auto-capture from conversations (done). Lead merge/dedup (done). What's missing: continuous extraction throughout conversation (not just first capture), suggest updates to existing leads, auto-populate service interest and notes from conversation context.

- [x] **Enhanced lead extraction — continuous mode** — DONE (already runs on every message, now also extracts service_interest via keyword matching, 2026-03-14)
- [x] **Lead update suggestions** — DONE 2026-03-15. Conflicting data creates pending suggestions via activity_log. Backend GET/POST endpoints. Cycle 48.
- [x] **Auto-populate service interest + notes** — DONE 2026-03-15. areas_of_interest + conversation_summary auto-populated on lead create/update. Fixed schema mismatch (service_interest→areas_of_interest). Cycle 47.
- [x] **Dashboard: lead suggestion review panel** — DONE 2026-03-15. Purple banner on LeadsPage with Approve/Dismiss per suggestion. Cycle 48.

### AI Call Transcription & Summaries

_After every AI-answered call, generate a transcript and AI summary with action items. Store in the conversation thread. Time-stamped transcript with jump-to-moment capability._

**Why this matters:** Quo auto-transcribes and summarizes every call with action items. We have the AI Answering Service module planned but haven't specified the transcription and summary pipeline in detail. This enriches that module.

**Note:** This extends our existing "AI Answering Service" module (already in Tier 2 of the backlog). Adding these items to that module's task list rather than duplicating.

- [x] **Call transcription pipeline** — DONE 2026-03-15 Cycle 79. Twilio transcription callback stores transcript in calls.transcript JSONB.
- [x] **AI call summary generation** — DONE 2026-03-15 Cycle 79. Claude generates summary + sentiment + action items from transcript.
- [x] **Transcript viewer UI** — DONE 2026-03-15 Cycle 79. CallsPage detail modal with chat-log style transcript, summary, sentiment badge.
- [x] **Action items from calls → action_items table** — DONE 2026-03-15 Cycle 79. Call action items inserted into action_items table with priority "high".

### MCP Integration

_Allow business owners to connect AgentNexLiFy to Claude or ChatGPT via MCP so they can manage their business communications from their AI assistant._

**Why this matters:** Quo offers MCP integration with Claude and ChatGPT. Business owners can ask "What calls did I miss today?" from their AI assistant. This is a power-user feature but positions us as forward-thinking.

**What we already have:** Open API endpoints. Webhooks. What's missing: an MCP server that exposes our API as tools for AI assistants.

- [x] **MCP server scaffold** — DONE 2026-03-15 Cycle 54. backend/mcp_server.py using FastMCP SDK. Auth via widget API key. Run standalone or mount.
- [x] **MCP tool definitions** — DONE 2026-03-15 Cycle 54. 6 tools: list_recent_leads, list_today_appointments, get_unread_conversations, get_action_items, get_analytics_summary, reply_to_conversation.
- [x] **MCP setup guide** — DONE 2026-03-15 Cycle 58. MCPSetupPage with Claude Desktop config, API key copy, tool list, example prompts.
- [x] **MCP authentication** — DONE 2026-03-15 Cycle 65. Migration 041 adds mcp_api_key + mcp_enabled. POST/DELETE /mcp-key endpoints. MCP server validates mcp_ keys.

---

## Features — Tier 1: Game Changers (COMPLETED)

_Previously Tier 0. Website scraping and restaurant orders are now complete._

### Auto-Scrape Customer Website on Signup

_When a business signs up and provides their website URL, we immediately crawl their site and feed the content to their AI agent. The chatbot knows their business from minute one — no manual FAQ entry needed._

- [x] **Cloudflare /crawl API integration** — done 2026-03-12. Backend service `website_crawler.py` wrapping Cloudflare Browser Rendering /crawl API. Config vars for CLOUDFLARE_ACCOUNT_ID/TOKEN.
- [x] **Website URL field on signup/settings** — done 2026-03-12. Migration 028 adds website_url to tenants. Settings page has Website URL field. Backend allows website_url in settings update.
- [x] **Crawl pipeline** — done 2026-03-12. Cloudflare crawl with 20-page limit, markdown format. Stores raw pages as JSONB + extracted_text in website_content table. Migration 028.
- [x] **AI knowledge base auto-population** — done 2026-03-12. Crawled website content auto-injected into chat widget system prompt (truncated to 8KB). AI knows the business immediately from website content.
- [x] **Crawl status UI** — done 2026-03-12. Settings page shows crawl status: scanning/completed/failed with page count and error messages. Color-coded status indicators.
- [x] **Re-crawl button** — done 2026-03-12. "Scan Website" button on Settings page triggers re-crawl. Overwrites previous crawl record.
- [x] **Fallback for no website** — done 2026-03-13. Settings page shows guidance to FAQ manager + business page when no website URL. Crawl endpoint auto-falls back to hosted business page URL if available. SSRF protection added.

### Restaurant Order Taking

_The chat widget can take food orders for restaurants — browse the menu, build an order, collect delivery/pickup info, and send the order to the business owner._

- [x] **Menu management page** — done 2026-03-13. Migration 029 creates menu_items table. Backend CRUD in backend/routers/menu.py with auth. Frontend MenuPage with category grouping, add/edit modal, toggle availability. Sidebar shows Menu tab only for restaurant business types.
- [x] **Menu auto-import from website crawl** — done 2026-03-13. Backend POST /menu/{tenant_id}/import-from-website endpoint. Claude API extracts menu items from crawled website content (up to 15KB). Auto-populates menu_items table with up to 100 items. Frontend "Import from Website" button on MenuPage.
- [x] **Order-taking chat flow** — done 2026-03-13. Widget system prompt enhanced with menu data for restaurant tenants. Menu items loaded from DB, grouped by category with prices. AI instructed to take orders conversationally and collect customer info. Orders created via POST /orders endpoint.
- [x] **Orders table + management** — done 2026-03-13. Migration 030 creates orders table (tenant_id, lead_id, session_id, customer info, items_json, pricing, order_type, status, notes). Backend CRUD in backend/routers/orders.py with auth. Status management (new→confirmed→preparing→ready→delivered/cancelled). Stats endpoint.
- [x] **Orders dashboard page** — done 2026-03-13. OrdersPage.jsx with stats cards, status filter, order list with status progression buttons (new→confirmed→preparing→ready→delivered), detail modal with items/pricing/customer info. 30s auto-refresh. Sidebar Orders tab gated by restaurant businessType.
- [x] **Order notification to owner** — done 2026-03-13. When order created from chat: SMS to owner with order summary (items, total, type). Email with full itemized details. Webhook event `order.created` fired for Zapier.
- [x] **Menu in widget** — done 2026-03-13. Widget config endpoint returns menu_items for restaurant tenants. Widget JS renders "View Menu" button in header + expandable menu panel with items grouped by category, prices, descriptions. HTML-escaped. Panel toggles alongside booking panel.
- [x] **Order confirmation to customer** — done 2026-03-13. SMS confirmation sent to customer with order summary, total, and business phone number. Triggered from chat order extraction background task.
- [x] **Business type detection** — done 2026-03-13. Business type added to JWT claims + MeResponse. Settings page dropdown with 14 business type options. Sidebar filters nav items by businessType (Menu tab only for restaurant). No migration needed — business_type column already exists.

---

## Features — Tier 2: "I need this to pay you money"
_These are the features a customer needs before they'll upgrade from free._

- [x] **Email notifications for new leads** — done 2026-03-12. Added `_send_new_lead_email_notification()` in widget.py, wired into both auto-capture and manual submit paths.
- [x] **Conversation export** — done 2026-03-12. Added "Export Transcript" button to ConversationsPage that downloads conversation as .txt file.
- [x] **Lead import via CSV** — done 2026-03-12. Backend: POST /api/v1/leads/{tenant_id}/import with UploadFile. Frontend: Import CSV button on LeadsPage with result banner. Dedup by email, max 500 rows, fires webhooks.
- [x] **Email template editor** — done 2026-03-12. Reusable template library (backend CRUD + migration 014) with 6 starter templates. SequenceBuilder enhanced with template picker, formatting toolbar, variable insertion, and live HTML preview panel. Templates can be saved from steps and reused across sequences.

## Features — Tier 3: "This would make my life easier"
_These make the product sticky — once they use these, they won't leave._

- [x] **Quick reply / follow-up from dashboard** — done 2026-03-12. Backend: POST /api/v1/leads/{tenant_id}/{lead_id}/email. Frontend: inline email compose in LeadDetailDrawer with subject/message fields. Auto-updates lead status from "new" to "contacted".
- [x] **Appointment reminders** — done 2026-03-12. Background function `send_appointment_reminders()` runs every 60s in the automation loop. Sends email + SMS at 24h and 1h before appointments. Dedup via notes field tags. No new migration needed.
- [x] **Business hours awareness in AI** — done 2026-03-12. Injected business hours + current open/closed status into chat system prompt. AI now knows schedule and can tell visitors when the business is open/closed.
- [x] **Multi-language support** — done 2026-03-12. Added instruction to system prompt: "ALWAYS respond in the same language the visitor uses." Claude handles detection natively — no separate detection library needed.
- [x] **Widget offline message** — done 2026-03-12. Migration 015 adds is_online/offline_message to widget_configs. Backend: toggle endpoint + offline contact form submission. Widget JS: detects offline status, shows contact form. Frontend: online/offline toggle on WidgetPage.
- [x] **Dashboard notifications center** — done 2026-03-12. Backend: GET /api/v1/notifications/{tenant_id} aggregates leads/conversations/appointments/activity. Frontend: NotificationBell component with dropdown, badge count, 60s polling.

## Features — Tier 4: "This makes me look professional"
_These differentiate from competitors and justify higher-tier pricing._

- [x] **Review/rating request** — Already complete. Template in sequences.py with appointment_completed trigger. Resolves {{review_link}} from tenant.google_review_link. Configurable in Settings. In TemplateGallery.
- [x] **Recurring appointment support** — done 2026-03-12. Migration 017 adds recurrence columns. Backend: POST /{tenant_id}/{appointment_id}/recur generates series. Frontend: Calendar edit modal with "Make Recurring" UI (weekly/biweekly/monthly + end date).
- [x] **Auto-tagging leads** — done 2026-03-12. Migration 016 adds tags TEXT[] to leads. Claude extracts tags from conversations during lead capture. Tags shown in LeadsPage table and LeadDetailDrawer.
- [x] **Conversation tagging** — done 2026-03-12. Migration 018 adds tags TEXT[] to conversations. Backend: PUT tags endpoint. Frontend: tag pills on sidebar, filter dropdown, inline add/remove.
- [x] **Lead merge** — done 2026-03-12. Backend: GET /duplicates finds matches by email/phone, POST /merge does keep-and-absorb merge. Frontend: "Find Duplicates" button on LeadsPage with merge modal.
- [x] **Widget file/image upload** — done 2026-03-12. Backend: POST /api/v1/widget/upload with multipart form, validates type/size, stores in Supabase Storage chat-attachments bucket. Widget JS: paperclip button, inline image preview, file download links. Both widget copies synced.

## Features — Tier 5: "I want the full platform"
_Operations-tier features that justify the premium plan._

- [x] **Zapier integration polish** — done 2026-03-12. Added automation.sms_sent to SUPPORTED_EVENTS. Enriched appointment.cancelled webhook with customer details. Updated all sample payloads to match actual field names. Added public GET /schema/events endpoint with event descriptions + sample payloads for Zapier setup. Conversation.message payload corrected to user_message/assistant_message fields.
- [x] **Team permissions enforcement** — done 2026-03-12. Applied require_role("owner", "admin") to all write endpoints in webhooks.py (create/update/delete/toggle/test), sequences.py (create/update/delete/toggle/template/campaign), and automations.py (toggle/config). Members and viewers can read but not modify. Settings and billing were already protected.
- [x] **Lead assignment** — done 2026-03-12. Migration 026 adds assigned_to UUID FK to leads. Backend: PUT /assign endpoint with team member validation + activity logging, GET filter by assigned_to. Frontend: assign dropdown in LeadDetailDrawer, assignee filter on LeadsPage.
- [x] **Conversation AI tuning** — done 2026-03-12. Migration 027 creates ai_feedback table. Widget: thumbs up/down buttons on every AI response. Backend: POST /feedback (widget), GET/DELETE /feedback (dashboard). Thumbs-down corrections auto-injected into system prompt (last 20). Dashboard: AI Feedback section on SettingsPage shows ratings with dismiss.
- [x] **Bulk SMS campaigns** — Already complete. Send Campaign modal on Automations page supports SMS channel. Backend sequences.py send_campaign handles SMS with Twilio, rate limiting, unsubscribe exclusion, phone validation. Max 500 per blast.
- [x] **Stripe subscription management in dashboard** — done 2026-03-12. Backend: POST /billing/change-plan (Stripe subscription modify with proration), POST /billing/cancel (cancel at period end). Frontend: BillingPage shows Switch Plan buttons for active subscribers, inline cancel with confirmation, cancellation status message. Free users still go through Stripe Checkout for initial subscription.

## Features — Module: Reputation Manager
_Aggregate reviews, AI-draft responses, auto-request reviews. Same dashboard, new tab._

- [x] **Review aggregation backend** — done 2026-03-12. Migration 019 creates reviews table. CRUD endpoints in backend/routers/reviews.py with filters, dedup by external_review_id.
- [x] **Reviews dashboard page** — done 2026-03-12. ReviewsPage.jsx with stats cards (avg rating, total, responded, unresponded), platform/rating/status filters, review list with detail modal.
- [x] **AI review response drafting** — done 2026-03-12. POST /{tenant_id}/{review_id}/ai-draft endpoint. Claude generates tone-matched responses (professional/friendly/casual). Owner edits in modal before saving.
- [x] **Auto review request after appointment** — done 2026-03-12. Migration 020 adds review_request_config (JSONB) to tenants + review_request_sent_at to appointments. Background scan in automation loop sends email/SMS after configurable delay. Settings UI on SettingsPage.
- [x] **Review analytics** — done 2026-03-12. Rating distribution bar chart + monthly avg rating/response rate trend line chart using Recharts. Toggleable analytics panel on ReviewsPage.
- [x] **Google Business Profile OAuth** — DONE 2026-03-15 Cycle 80. Full OAuth flow in gbp.py (auth URL, callback, token storage, status, disconnect, profile fetch). Awaiting Google API credentials.

## Features — Module: Smart Outreach
_AI-powered follow-up sequences and lead nurturing from the dashboard._

- [x] **Outreach sequence builder** — Already built as Automations page + SequenceBuilder component. Supports trigger-based email/SMS sequences with step editor, template picker, and variable insertion.
- [x] **AI email writer** — Already built as `ai_email` action type in automation_engine.py. Claude generates personalized emails from conversation context + FAQ entries.
- [x] **Sequence execution engine** — Already built as `process_pending_steps()` in automation_engine.py. Processes due steps every 60s, supports email/ai_email/sms action types, logs delivery status.
- [x] **Lead re-engagement campaigns** — done 2026-03-12. Backend: POST /campaigns/send with filters (status, score, date range). Frontend: "Send Campaign" modal on Automations page with channel/subject/body/filters. Excludes unsubscribed leads. Max 500 per blast.
- [x] **Outreach analytics** — done 2026-03-12. Migration 022 creates email_events table. Tracking pixel injected in every outgoing email. Open tracking endpoint (GET /track/open). Stats shown on Automations page (opens today, total opens). Sequence stats endpoint extended with open counts.
- [x] **Unsubscribe handling** — done 2026-03-12. Migration 021 adds unsubscribed/unsubscribed_at to leads. HMAC-signed unsubscribe links in every automated email. Public unsubscribe endpoint returns HTML confirmation. Automation engine skips unsubscribed leads. List-Unsubscribe header included. Frontend shows unsubscribe badge on lead detail.

## Features — Module: Content Studio
_Turn one piece of content into posts for every platform._

- [x] **Content input page** — done 2026-03-12. Migration 023 creates content_items table. Backend CRUD in backend/routers/content.py. Frontend ContentStudioPage with create modal (text/description/file upload), list view, detail panel. Sidebar link + lazy-loaded routing.
- [x] **AI content repurposer** — done 2026-03-12. Backend POST /{tenant_id}/{content_id}/repurpose endpoint. Claude generates 6 platform versions (LinkedIn, Facebook, Instagram, GBP, email newsletter, Twitter/X) in a single call with delimiter-based parsing. Frontend: "Generate AI Versions" button on detail panel with loading state, per-platform copy buttons. Regenerate support. Takes the source content and generates platform-specific versions: LinkedIn post (professional tone, 150-300 words), Facebook post (casual, with emoji), Instagram caption (short, hashtags), Google Business Profile update (local SEO optimized), email newsletter snippet, Twitter/X thread (short punchy posts). Each version follows platform best practices for length, tone, and formatting.
- [x] **Content preview and edit** — done 2026-03-12. All generated versions shown side by side with Edit/Copy buttons per platform. Inline textarea editing with Save/Cancel. Edits saved via PATCH to platform_versions JSONB. Active edit highlighted with accent border.
- [x] **Content calendar** — done 2026-03-12. Migration 025 adds scheduled_for DATE column. Calendar grid view with month navigation, content items shown on their scheduled dates. Schedule date picker on detail panel with unschedule button. List/Calendar view toggle. Scheduled stat card added.
- [x] **Direct publishing (phase 2)** — DONE 2026-03-15 Cycle 80. POST /api/v1/gbp/{tenant_id}/post endpoint scaffolded (needs location ID discovery). Other platforms future.
- [x] **Content library** — done 2026-03-12. Search input filters content by title. Status filter dropdown. Combined with list view for browsable/searchable library.

## Features — Module: Local SEO Tools
_Google Business Profile optimization and local ranking intelligence._

- [x] **GBP connection** — DONE 2026-03-15 Cycle 80. OAuth flow in gbp.py. Awaiting Google API credentials.
- [x] **Profile completeness score** — DONE 2026-03-15 Cycle 69. SEO profile analysis with 0-100 score, missing fields, recommendations.
- [x] **Auto-post to GBP** — DONE 2026-03-15 Cycle 80. POST endpoint scaffolded. Needs location ID after OAuth live.
- [x] **Local keyword suggestions** — DONE 2026-03-15 Cycle 69. Claude generates keywords based on business_type + city. Stored in seo_profiles.
- [x] **Review velocity tracker** — DONE 2026-03-15 Cycle 76. Response stats endpoint tracks review/response rates over time.
- [x] **Local SEO dashboard widget** — DONE 2026-03-15 Cycle 69. GET /dashboard-widget returns score + top recommendations.

## Features — Module: Job Board (Add-on)
_For businesses that need to hire. SMS-first, no resume required._

- [x] **Job posting page** — done 2026-03-13. Migration 031 creates jobs + job_applications tables. Backend CRUD in backend/routers/jobs.py with auth. Frontend JobsPage with create/edit modal, job list with status toggle, application management. Sidebar "Job Board" tab for owner/admin.
- [x] **Public job page** — done 2026-03-13. GET /api/v1/jobs/public/{tenant_id}/listings returns active jobs with business info. No auth required.
- [x] **SMS-first application** — done 2026-03-13. POST /api/v1/jobs/public/{tenant_id}/{job_id}/apply accepts name + phone + message. SMS confirmation to applicant. SMS notification to owner. No resume, no account needed.
- [x] **Applicant management** — done 2026-03-13. JobsPage shows applications per job with status management (new/contacted/interviewed/hired/rejected). Notes field. Status update endpoint.
- [x] **AI job description writer** — done 2026-03-13. POST /api/v1/jobs/{tenant_id}/ai-write endpoint. Claude generates structured job posting from plain language description. Frontend "AI Write" button on JobsPage.
- [x] **Job widget integration** — done 2026-03-13. Active jobs injected into widget system prompt. AI mentions open positions when relevant to conversation.

## Features — Module: AI Answering Service
_AI answers phone calls, takes messages, books appointments, texts the owner a summary. Powered by Twilio Voice + Claude._

- [x] **Twilio Voice webhook endpoint** — DONE 2026-03-15 Cycle 68. POST /voice/incoming returns TwiML greeting + record. POST /voice/recording-complete stores call + notifies owner.
- [x] **AI voice conversation handler** — DONE 2026-03-15 Cycle 76. Twilio <Gather> + <Say> loop with Claude AI responses. 3-round conversation max.
- [x] **Call summary + owner notification** — DONE 2026-03-15 Cycle 68. SMS notification to owner with caller info. Summary placeholder for v1 (transcription deferred).
- [x] **Call log dashboard page** — DONE 2026-03-15 Cycle 68. CallsPage with stats, call list, detail modal, recording links.
- [x] **Business phone number provisioning** — DONE 2026-03-15 Cycle 77. POST /api/v1/phone/{tenant_id}/provision, GET /available, DELETE /release via Twilio API.
- [x] **Call-to-appointment pipeline** — DONE 2026-03-15. Leads auto-created from caller phone. Voice AI can collect booking info conversationally.

## Features — Module: Missed Call Text-Back
_When a call goes to voicemail, auto-text the caller with an AI agent that handles the conversation via SMS._

- [x] **Missed call detection** — DONE 2026-03-15 Cycle 60. POST /api/v1/twilio/missed-call webhook. Auto-detects no-answer/busy/failed calls.
- [x] **Auto text-back message** — DONE 2026-03-15 Cycle 60. Auto-sends "{business_name} missed your call" text within seconds. AI handles SMS replies via /api/v1/twilio/sms-reply.
- [x] **SMS conversation threading** — DONE 2026-03-15 Cycle 60. Messages stored in chat_messages with session_id=sms_{phone}. Visible in ConversationsPage alongside widget chats.
- [x] **Lead capture from SMS** — DONE 2026-03-15 Cycle 60. Lead auto-created on missed call with phone number. SMS AI replies use same chat engine that extracts lead info.
- [x] **Configurable text-back settings** — DONE 2026-03-15 Cycle 61. SettingsPage: toggle, custom message, quiet hours. Backend respects all settings.
- [x] **Missed call analytics** — DONE 2026-03-15 Cycles 61+77. Dashboard stat card + per-day breakdown in AnalyticsPage.

## Features — Module: Contractor Bid Manager
_AI generates professional estimates/proposals from a job description. Track bid status._

- [x] **Bid creation flow** — DONE 2026-03-15 Cycle 67. AI generates bids from plain language descriptions via Claude. Full CRUD.
- [x] **Bid template system** — DONE 2026-03-15 Cycle 67. Templates with default_items JSONB. Create/list/delete.
- [x] **PDF bid generation** — DONE 2026-03-15 Cycle 75. HTML invoice with print-friendly CSS served via /{bid_id}/pdf endpoint.
- [x] **Bid tracking** — DONE 2026-03-15 Cycle 67. Status pipeline (draft→sent→viewed→accepted/rejected/expired). Stats: total, win rate, avg value, pipeline value.
- [x] **Bid-to-lead connection** — DONE 2026-03-15 Cycle 67. Bids have lead_id FK. Can be linked on creation.
- [x] **Quick bid from chat** — DONE 2026-03-15 Cycle 70. AI collects job details conversationally, outputs BID_REQUEST marker, creates action item.

## Features — Module: Client Portal
_Customers get a link to their portal showing invoices, job photos, warranty, and a rebook button._

- [x] **Client portal page** — DONE 2026-03-15 Cycle 68. Public GET /portal/{token} returns business info, customer info, service records.
- [x] **Service record system** — DONE 2026-03-15 Cycle 68. Full CRUD with lead_id, photos_json, documents_json, invoice_amount.
- [x] **Photo upload for job documentation** — DONE 2026-03-15 Cycle 75. POST /{record_id}/upload with Supabase Storage.
- [x] **Invoice attachment** — DONE 2026-03-15 Cycle 68. invoice_amount field on service_records. PDF upload deferred.
- [x] **Rebook button** — DONE 2026-03-15 Cycle 75. Portal response includes widget_api_key + api_base. Public page has "Book Again" button.
- [x] **Automated portal link delivery** — DONE 2026-03-15 Cycle 73. Auto-emails portal link to customer after appointment marked completed.

## Features — Module: AI Review Responder
_Chrome extension that drafts review responses on Google/Yelp with one click._

- [x] **Chrome extension scaffold** — DONE 2026-03-15 Cycle 72. Manifest v3, popup UI, content scripts for Google Maps + Yelp.
- [x] **AI response generation** — DONE 2026-03-15 Cycle 72. Uses widget chat API to generate review responses via Claude.
- [x] **Response customization** — DONE 2026-03-15 Cycle 72. Popup shows draft, copy button, regenerate button.
- [x] **Business context sync** — DONE 2026-03-15 Cycle 72. Connects via widget API key, stores in chrome.storage.
- [x] **Response history** — DONE 2026-03-15 Cycle 76. GET /response-stats endpoint with rate, avg time, monthly counts.
- [x] **Review alert integration** — DONE 2026-03-15 Cycle 76. check_new_reviews() in automation loop sends SMS alerts for new reviews.

## Features — Module: Local Business Autopilot
_Done-for-you digital presence: website + GBP + widget + reviews + booking in one subscription._

- [x] **Autopilot onboarding wizard** — DONE 2026-03-15 Cycle 77. POST /onboarding/{tenant_id}/complete + GET /status. Auto-creates hours, FAQs, triggers crawl.
- [x] **Auto-generated business page** — DONE 2026-03-15 Cycle 77. Claude generates hero text, about section, services, FAQs during onboarding.
- [x] **GBP optimization recommendations** — DONE 2026-03-15 Cycle 69. Local SEO profile analysis with completeness score + recommendations.
- [x] **Auto-configured widget** — DONE 2026-03-15 Cycle 77. Widget auto-created on signup, onboarding wizard configures hours + FAQs.
- [x] **Monthly performance report** — DONE 2026-03-15 Cycle 70. Auto-email with conversations/leads/appointments/reviews to autopilot tenants every 28 days.
- [x] **Autopilot pricing tier** — DONE 2026-03-15 Cycle 77. $299/month plan in Stripe config + BillingPage + SMS unlimited.

## Bugs — Known Issues

_Check docs/dev-knowledge/bug-patterns.md for documented bugs. Add any new ones here._

### CTO Site Review (2026-03-25) — CRITICAL

- [ ] **[CTO-SITE-REVIEW] Stripe checkout links are TEST MODE** — Pricing page "Get Started" buttons for Growth ($249), Professional ($499), and Enterprise ($899) link to `buy.stripe.com/test_*` URLs. Revenue pipeline broken. Fix: implement server-side Stripe Checkout Session creation via `/api/v1/auth/billing/checkout`. Done when: clicking "Get Started" creates a real Stripe checkout session.
- [ ] **[CTO-SITE-REVIEW] No "Forgot Password" on login page** — Login page has no password reset link. Business owners who forget passwords are locked out. Create ForgotPassword page, backend reset token endpoint (via Resend), reset tokens expire after 1 hour.
- [ ] **[CTO-SITE-REVIEW] Social media links in footer are dead (#)** — Twitter/X and LinkedIn links point to `href="#"`. Remove until real profiles exist.
- [ ] **[CTO-SITE-REVIEW] Privacy Policy "do not" rendering** — Verify negation statements are unambiguous in all rendering contexts.

### CTO Site Review (2026-03-25) — HIGH

- [ ] **[CTO-SITE-REVIEW] "Book a Demo" goes to generic contact form** — Hero CTA should open a real scheduling interface (Cal.com/Calendly embed or our booking feature).
- [ ] **[CTO-SITE-REVIEW] No chat widget on our own website** — We sell a chat widget but don't use it on agentnexlify.com. Embed our widget as product demo + lead capture.
- [ ] **[CTO-SITE-REVIEW] "Only 10 Spots Remaining" on ALL tiers is fake scarcity** — Replace with honest "Setup fee waived for early customers" messaging.
- [ ] **[CTO-SITE-REVIEW] Signup industry dropdown missing key verticals** — Only 10 options. Add HVAC, Landscaping, Cleaning, Electrical, Roofing, Pest Control, Moving, Photography, Accounting, Veterinary, Chiropractic, Tutoring (20+ total).
- [ ] **[CTO-SITE-REVIEW] No testimonials or social proof on landing page** — Zero testimonials, logos, case studies, or metrics. Add social proof section.
- [ ] **[CTO-SITE-REVIEW] Demo section is static mockups** — Make clickable/interactive or embed live widget demo.
- [ ] **[CTO-SITE-REVIEW] Contact page is too barebones** — Add expected response time, chat widget embed, direct email, business hours.
- [ ] **[CTO-SITE-REVIEW] No Google OAuth on signup** — Adding "Sign up with Google" would reduce friction.

### Other Bugs

- [ ] **Audit Claude API calls for Sonnet 4.6 model string** — Verify all Claude API calls use `claude-sonnet-4-6` for fast responses and `claude-opus-4-6` for complex tasks.

### Resolved

- [x] Widget not capturing phone numbers with country codes (international format) — fixed 2026-03-12
- [x] Dashboard analytics may show wrong timezone for appointment times — fixed 2026-03-12
- [x] Test signup with an email that already exists — NOT A BUG, returns 409 correctly (investigated 2026-03-15)
- [x] Test what happens when Claude API is slow or down — FIXED: added 30s timeout to all 10 Anthropic calls (2026-03-15 Cycle 52)
- [x] Test what happens when Supabase is paused — PARTIALLY FIXED: health check now returns "degraded" (2026-03-15 Cycle 52)
- [x] Verify automation sequence execution runs on a schedule — NOT A BUG, runs correctly as asyncio task in main.py (confirmed 2026-03-15)

## Tests — Coverage Gaps

### CTO-Mandated Tests (2026-03-25)

- [ ] **SSE Streaming Integration Tests** — Happy path streaming, connection drop recovery, API failure fallback, concurrent stream handling. File: `tests/test_chat_streaming.py`.
- [ ] **Voice Channel E2E Test Suite** — Inbound call > AI greeting > question answering > appointment booking > call logging > lead creation. File: `tests/test_voice_integration.py`.
- [ ] **Multi-Tenant Isolation Regression Suite** — Two test tenants, verify tenant A cannot see tenant B's conversations, leads, appointments, settings, analytics. Must run on every PR. File: `tests/test_multi_tenant_isolation.py`.

### Existing

- [x] Test signup flow with duplicate email — done 2026-03-12
- [x] Test chat endpoint with empty message body — covered in lead extraction tests 2026-03-12
- [x] Test lead capture with partial info (name but no email) — done 2026-03-12
- [x] Test appointment booking with overlapping time slots — done 2026-03-12 (12 tests)
- [x] Test webhook delivery and retry logic — done 2026-03-12 (18 tests)
- [x] Test Stripe webhook signature verification — done 2026-03-12 (7 tests)
- [x] Test widget CORS from external domain — DONE 2026-03-15 Cycle 59 (3 CORS tests)
- [x] Test automation sequence execution order — DONE 2026-03-15 Cycle 59 (2 sequence tests)
- [x] Test login flow: valid login, wrong password, non-existent email — DONE 2026-03-15 Cycle 52 (4 tests)
- [x] Test chat endpoint edge cases: very long message, invalid API key, empty message — DONE 2026-03-15 Cycle 52 (3 tests)
- [x] Test lead capture: malformed email, international phone formats — DONE 2026-03-15 Cycle 52 (3 tests)
- [x] Test appointments: create, past date, list, status update, cancel — DONE 2026-03-15 Cycle 55 (5 tests)
- [x] Test business page: valid slug, non-existent slug, slug with special characters — DONE 2026-03-15 Cycle 55 (3 tests)
- [x] Test CORS: request from allowed origin, request from disallowed origin — DONE 2026-03-15 Cycle 59
- [x] Test rate limiting: verified decorators applied on all public endpoints — DONE 2026-03-15 Cycle 59 (2 tests)
- [x] Test Google Calendar OAuth: status, disconnect, connected — DONE 2026-03-15 Cycle 80 (3 tests)
- [x] Test team invites: validated invite token returns member info — DONE 2026-03-15 Cycle 55
- [ ] **Test invoicing endpoints** — CRUD, Stripe Payment Link creation, send invoice via email/SMS, payment reminder dedup, status transitions (draft→sent→paid→overdue)
- [ ] **Test pipeline endpoints** — Stage CRUD, board view, lead stage movement, default stage seeding, deal value aggregation, won/lost analytics
- [ ] **Test form builder public submission** — Public form submit with valid/invalid data, lead auto-creation from submission, required field validation, form not found (404)
- [ ] **Test document e-signature flow** — Create document from template, send for signature, public signing endpoint with valid/invalid/expired token, signature data storage
- [ ] **Test marketing campaign sending** — Campaign create, audience filtering (status/temperature/tags), send with Resend+Twilio, unsubscribe exclusion, max 500 recipient cap
- [ ] **Test missed call text-back** — Missed call webhook, auto-text sending, quiet hours enforcement, SMS reply threading, lead auto-creation from caller phone
- [ ] **Test AI action item extraction** — Extraction from chat messages, priority assignment, due date parsing, assignment to team members, status transitions (open→done)

## Content — Marketing & Docs

- [x] Welcome email for new signups — done 2026-03-12
- [x] "How to embed the widget" help article — done 2026-03-12
- [x] **Help article: "How to configure your AI assistant"** — DONE 2026-03-15 Cycle 42
- [x] **Help article: "Understanding your analytics dashboard"** — DONE 2026-03-15 Cycle 42
- [x] **Help article: "Managing your leads"** — DONE 2026-03-15 Cycle 57
- [x] **Help article: "Setting up appointment booking"** — DONE 2026-03-15 Cycle 57
- [x] **Onboarding email sequence** — DONE 2026-03-15 Cycles 43-44. Day 0-14 emails + automated delivery system.
- [x] **Case study template** — DONE 2026-03-15 Cycle 64. Template with metrics table, quote slots, fill-in guide.
- [x] **Landing page A/B copy variants** — DONE 2026-03-15 Cycle 57. 3 variants: problem, outcome, social proof.
- [x] **Social media posts** — DONE 2026-03-15 Cycle 45. 10 LinkedIn + Facebook paired posts.
- [x] FAQ entries for common widget questions — DONE 2026-03-15 Cycle 63. 14 Q&A pairs covering all common widget topics.

## Features — Module: Marketing & SEO (Okara Competitive Response)
_Added 2026-03-17 to close competitive gaps with Okara AI's CMO product._

- [x] **SEO Audit Hub** — DONE 2026-03-17 Cycle 88. AI-powered website audit with scoring, categorized issues, recommendations. Reused existing website crawl data.
- [x] **GEO Visibility Tracking** — DONE 2026-03-17 Cycle 88. AI estimates brand visibility across ChatGPT, Claude, Perplexity, Gemini with per-platform scores.
- [x] **Keyword Rank Tracking** — DONE 2026-03-17 Cycle 88. Add/track keywords with AI-estimated difficulty, position, volume. Unique constraint per tenant+keyword.
- [x] **Social Media Post Management** — DONE 2026-03-17 Cycle 88. CRUD for posts across 5 platforms, calendar view, analytics. AI content generation + campaign generator.
- [x] **Marketing Campaigns** — DONE 2026-03-17 Cycle 88. Email/SMS blast campaigns with audience targeting (status, temperature, tags). Real Resend + Twilio sending.
- [x] **AI Marketing Content Writer** — DONE 2026-03-17 Cycle 88. AI generates platform-optimized social posts and campaign emails with tone/type controls.
- [x] **Pricing Restructure** — DONE 2026-03-17 Cycle 88. Growth $249, Professional $499, Enterprise $899. Marketing/SEO features included per tier.
- [ ] **Social media platform OAuth** — Connect to Facebook/Twitter/LinkedIn APIs for direct posting (currently create-and-copy)
- [ ] **Real SERP data integration** — Connect to SEMrush/Ahrefs API for actual keyword position data
- [x] **Competitor analysis dashboard** — DONE 2026-03-22 Cycle 167. AI-powered comparison with score cards, gaps, advantages, recommendations
- [x] **Automated social media posting scheduler** — DONE 2026-03-22 Cycle 162. Background jobs auto-publish scheduled posts + auto-send scheduled campaigns every 5 min.

## Features — Tier 6: GoHighLevel/Jobber Competitive Response (BUILD NEXT)

_Inspired by GoHighLevel, Jobber, ServiceTitan, HubSpot, Podium. These close the biggest competitive gaps._

### Invoicing & Text-to-Pay
- [x] **Migration: invoices table** — DONE 2026-03-18 Cycle 91. Migration 051 applied to live Supabase.
- [x] **Backend: invoices router** — DONE 2026-03-17 Cycle 91. 869 lines, full CRUD + Stripe Payment Link + send via SMS/email.
- [x] **Frontend: InvoicesPage** — DONE 2026-03-17 Cycle 91. 1030 lines, create/send/track invoices.
- [x] **Wire bids → invoices** — DONE 2026-03-18 Cycle 92. Status validation + duplicate prevention guard.
- [x] **Payment reminders** — DONE 2026-03-18 Cycle 92. Auto-send email+SMS for overdue/due-tomorrow, dedup per day.

### Sales Pipeline / Kanban Board
- [x] **Migration: pipeline_stages table** — DONE 2026-03-18 Cycle 91. Migration 052 applied to live Supabase.
- [x] **Backend: pipeline endpoints** — DONE 2026-03-17 Cycle 91. 524 lines, stage CRUD + board + analytics.
- [x] **Frontend: Pipeline board** — DONE 2026-03-17 Cycle 91. 674 lines, Kanban with deal values.
- [x] **Default pipelines** — DONE 2026-03-18 Cycle 92. 6 default stages auto-seeded on first access.

### AI Business Insights (Weekly Intelligence Brief)
- [x] **Backend: AI insights service** — DONE 2026-03-18 Cycle 92. Weekly Claude analysis of 7-day metrics (runs Mondays for paid tenants).
- [x] **Email delivery** — DONE 2026-03-18 Cycle 92. Weekly "Business Intelligence Brief" with metrics table + AI insights.
- [x] **Dashboard widget** — DONE 2026-03-18 Cycle 92. AIInsightsWidget with key metrics + AI analysis bullets.

### Smart Lists (Dynamic Lead Segments)
- [x] **Migration: smart_lists table** — DONE 2026-03-18 Cycle 93. Migration 053 applied to live Supabase.
- [x] **Backend: smart list engine** — DONE 2026-03-18 Cycle 93. Filter engine, CRUD, CSV export, count refresh.
- [x] **Frontend: SmartListsPage** — DONE 2026-03-18 Cycle 93. Rule builder UI, lead table, export.

### Form & Survey Builder
- [x] **Migration: forms + form_submissions tables** — DONE 2026-03-18 Cycle 93. Migration 054 applied to live Supabase.
- [x] **Backend: form CRUD + public submit** — DONE 2026-03-18 Cycle 93. Auto-creates leads from submissions.
- [x] **Frontend: FormBuilderPage** — DONE 2026-03-18 Cycle 93. Field builder, live preview, embed code.

### Documents & E-Signatures
- [x] **Migration: documents table** — DONE 2026-03-19 Cycle 112. Migration 061: documents + document_templates tables.
- [x] **Backend: document rendering + signature** — DONE 2026-03-19 Cycle 112. Full CRUD, template system, send for signature, public signing endpoints.
- [x] **Frontend: document builder + signature pad** — DONE 2026-03-19 Cycle 113. DocumentsPage with create/send/track, template picker, status filters.

## Features — Dental/Healthcare Simulation Gaps (2026-03-19)

_Discovered via dental office customer simulation. Applicable to all healthcare business types._

- [x] **Dental-aware appointment reminders** — DONE 2026-03-21 Cycle 117. Business-type-aware "bring" items in 24h reminders for 9 business types.
- [x] **More dental FAQs on signup** — DONE 2026-03-19 Cycle 115. 4 new dental FAQs added (cancellation, payment plans, first visit, cosmetic).
- [x] **Rebook automation** — DONE 2026-03-21 Cycle 117. Auto-sends rebook suggestion 24-48h after appointment completion. Dental: 180d, salon: 42d, medical: 365d.
- [x] **Patient intake form preset** — DONE 2026-03-21 Cycle 118. 3 presets: dental intake (13 fields), medical intake (11 fields), contractor estimate (8 fields).
- [x] **Insurance fields in leads** — DONE 2026-03-21 Cycle 119. Migration 062: insurance_carrier, insurance_member_id, insurance_group on leads.
- [x] **HIPAA compliance messaging** — DONE 2026-03-21 Cycle 118. AI system prompt gets healthcare privacy instructions for dental/medical business types.
- [x] **Service-based slot duration** — DONE 2026-03-21 Cycle 125. Migration 063: service_types table with name, duration_minutes, price. CRUD + public endpoint.

## Features — Researched Competitive Opportunities (2026-03-21)

- [x] [RESEARCHED] **Industry-specific pipeline presets** — DONE Cycles 121+124. 6 industry presets + 9 type aliases covering all 14 business types.
- [x] [RESEARCHED] **AI conversation summary on lead card** — DONE 2026-03-21 Cycle 123. Summary subtitle on LeadsPage + AI generate-summary endpoint.
- [ ] [RESEARCHED] **Two-way email sync** — When business owner replies to a lead via their regular email, capture it in the conversation thread. Competitors all have this.
- [x] [RESEARCHED] **Lead source tracking** — DONE 2026-03-21 Cycle 122. Source column already exists (migration 001). Now set correctly: widget, booking, missed_call, csv_import, manual.
- [x] [RESEARCHED] **Zapier trigger for form submissions** — ALREADY DONE. form.submitted webhook event already fires + now documented in schema.
- [x] [RESEARCHED] **White-label client login** — DONE 2026-03-22 Cycle 163. Migration 065 (client_accounts), register via portal token, login via email+password+slug, client JWT, rich portal dashboard with appointments/invoices/documents.
- [x] [RESEARCHED] **AI-to-human handoff** — DONE 2026-03-22 Cycle 161. AI detects user request for human, tags conversation "handoff", notifies team, skips Claude on subsequent messages, shows team replies.
- [x] [RESEARCHED] **Lead source analytics dashboard** — DONE 2026-03-21 Cycle 134. Horizontal bar chart on AnalyticsPage with color-coded sources.
- [x] [RESEARCHED] **Post-appointment care instructions** — DONE 2026-03-21 Cycle 135. Aftercare templates for 5 business types, dental has procedure-specific instructions.

## Features — Tier 7: Growth & Retention (2026-03-23)

_Features that make a non-technical small business owner pay $199/mo and never leave. Focused on proving ROI, reducing daily friction, and becoming the single tool they open every morning._

### Revenue-Driving Features

- [ ] **ROI Dashboard — "Your AI earned you $X this month"** — Dedicated dashboard card that calculates estimated revenue attributed to the platform: leads captured x avg deal value, appointments booked x avg service price, invoices paid. Business owners need to see a dollar amount that exceeds their subscription cost. Pull from leads (converted), appointments (completed), invoices (paid). Show month-over-month trend. This is the single most important retention metric — if they see $3,000 earned vs $199 paid, they never cancel.

- [ ] **Automated "We miss you" win-back campaigns** — When a lead goes cold (no activity for 14/30/60 days), auto-trigger a personalized re-engagement email or SMS. AI writes the message based on the lead's original conversation context and interests. Configurable per tenant with delay thresholds. This recovers revenue that would otherwise be lost — a plumber who quoted a kitchen remodel 3 weeks ago gets a "Still thinking about that kitchen remodel?" text.

- [ ] **Referral program — "Refer a friend, get a month free"** — Migration: referral_codes table (tenant_id, code, referred_tenant_id, reward_status). Tenants generate a unique referral link from BillingPage. When a new tenant signs up via referral and subscribes to a paid plan, both referrer and referee get one month credit. Dashboard shows referral stats. Viral growth loop that costs nothing until it works.

- [ ] **Upsell prompts based on usage** — When a free-tier tenant hits usage milestones (10 leads, 5 appointments, first missed call), show a contextual banner: "You captured 10 leads this week. Upgrade to Growth to auto-follow-up with all of them." Triggered from backend usage counters, displayed as dismissable banners on dashboard. Non-annoying, value-based nudges tied to moments the owner already feels the platform's value.

- [ ] **Google Review link auto-prompt after invoice paid** — When an invoice is marked as paid (Stripe webhook or manual), auto-send an SMS/email asking for a Google review. Delay configurable (default 2 hours). Uses existing review request infrastructure but triggered by payment instead of appointment completion. Businesses that get paid are at peak customer satisfaction — capture that moment.

### Retention Features — Make It the First App They Open

- [ ] **Daily morning digest email** — "Good morning, here's your day." Sent at 7am in the tenant's timezone. Includes: today's appointments with customer names, overdue action items, new leads overnight, unread conversations, yesterday's key stats (leads, conversations, revenue). Keeps the business owner engaged even when they forget to open the dashboard. Configurable: daily/weekly/off.

- [ ] **Mobile-friendly quick actions from email** — Every notification email (new lead, missed call, new review) includes one-tap action buttons that work on mobile: "Call Back" (tel: link), "Reply" (deep link to conversation), "Approve Bid" (link to bid page). Business owners are on their phone between jobs — let them act without opening the dashboard. Uses HTML email buttons with deep links to the frontend.

- [ ] **Streak tracker — "You've responded to leads within 5 minutes for 12 days straight"** — Gamification widget on dashboard homepage. Tracks response time streaks, lead follow-up streaks, review response streaks. Shows current streak + best streak. Subtle but effective — business owners become competitive with themselves. Fires a congratulatory notification at milestones (7 days, 30 days, 100 days).

- [ ] **"Set it and forget it" automation presets by business type** — One-click automation setup: "Plumber Starter Pack" creates 5 automations (new lead follow-up, appointment reminder, review request, rebook reminder, missed call text-back) pre-configured for the business type. Currently each automation must be built manually. Non-technical owners never build automations — give them a button that sets up everything. Leverage existing business_type + automation infrastructure.

### Performance Optimizations

- [ ] **Add database indexes for recent high-volume tables** — Add composite indexes on: invoices (tenant_id, status, created_at), social_posts (tenant_id, status, scheduled_for), marketing_campaigns (tenant_id, status), form_submissions (form_id, created_at), action_items (tenant_id, status). These tables have grown since launch and queries are scanning without indexes.

- [ ] **Paginate conversations and orders endpoints** — ConversationsPage and OrdersPage currently load all records. Add offset/limit pagination like LeadsPage already has. Restaurants with 500+ orders and businesses with 1000+ conversations will hit performance walls.

- [ ] **Debounce dashboard API calls on page load** — Dashboard homepage fires 6+ parallel API calls on mount (stats, insights, action items, notifications, leads, appointments). Add a single /api/v1/dashboard/{tenant_id}/summary endpoint that returns all dashboard data in one call. Reduces round trips from 6 to 1. Frontend renders progressively as data arrives.

### Error Handling Improvements

- [ ] **Graceful degradation when Twilio is unreachable** — If Twilio SMS/voice fails (network error, auth expired, insufficient funds), catch the error, log it, and show a user-visible alert on the dashboard: "SMS delivery failed — check your Twilio balance." Currently failures are silently swallowed in background tasks. Add a tenant_alerts system for surfacing operational issues.

- [ ] **Retry failed webhook deliveries with exponential backoff** — Webhook delivery currently fires once and logs success/failure. Add retry logic: 3 attempts with 1min/5min/30min delays. Store retry_count and next_retry_at on webhook_logs. Process retries in the automation loop. Business owners relying on Zapier integrations lose data when their Zap endpoint is temporarily down.

- [ ] **User-facing error messages for Claude API failures** — When Claude API returns 429 (rate limit), 500 (server error), or timeout, show a specific user-friendly message instead of generic "Something went wrong." In chat widget: "Our AI is thinking hard — please try again in a moment." In dashboard AI features: "AI analysis temporarily unavailable — your data is safe." Log the specific error for debugging.

### Security Hardening

- [ ] **Add CSRF protection to all state-changing endpoints** — Dashboard frontend should send a CSRF token with every POST/PUT/DELETE. Backend validates it. Currently relies on JWT auth alone, but CSRF attacks can still exploit an authenticated session if the user visits a malicious site while logged in. Use double-submit cookie pattern compatible with SPA architecture.

- [ ] **Audit log for sensitive operations** — Log all billing changes, team member additions/removals, API key regenerations, password changes, and plan changes to a new audit_log table. Include actor (tenant_id + team_member_id), action, timestamp, IP address. Accessible from Settings page for owner role only. Required for SOC 2 readiness and builds enterprise trust.

### Mobile Responsiveness

- [ ] **Responsive dashboard sidebar — collapsible on mobile** — Dashboard sidebar currently does not collapse on small screens, pushing content off-viewport. Add a hamburger menu toggle on screens < 768px. Sidebar slides in as an overlay. Auto-close on navigation. Business owners check their dashboard on their phone between appointments — this is table stakes.

- [ ] **Touch-friendly pipeline Kanban board** — PipelinePage Kanban drag-and-drop does not work on touch devices. Add touch event handlers (touchstart/touchmove/touchend) or use a library that supports both pointer types. Contractors and sales people manage their pipeline from their phone on job sites.

### Accessibility Improvements

- [ ] **Add ARIA labels and keyboard navigation to all dashboard pages** — Audit all interactive elements (buttons, modals, dropdowns, tabs) for missing aria-label, aria-describedby, and role attributes. Add keyboard navigation (Tab, Enter, Escape) to modals, dropdown menus, and the sidebar. Screen reader users should be able to navigate the full dashboard. Start with the 5 most-used pages: Dashboard, Leads, Conversations, Calendar, Settings.

- [ ] **Color contrast audit for dark theme** — Several dashboard elements (muted text, disabled buttons, placeholder text) may not meet WCAG AA contrast ratio (4.5:1 for normal text, 3:1 for large text). Audit all text/background combinations. Fix any that fall below threshold. Affects readability for all users, not just those with visual impairments.

---

## Optimization

- [x] Add rate limiting to all public endpoints — DONE 2026-03-15 Cycle 46. All public endpoints now rate-limited via slowapi.
- [x] Add request logging middleware — DONE (already implemented, JSON structured with tenant_id + duration + request_id)
- [x] Optimize database queries — DONE 2026-03-15 Cycle 49. Added idx_leads_client_created. chat_messages and appointments already indexed.
- [x] Add caching for tenant/widget configuration — DONE 2026-03-15 Cycle 49. 5-min TTL cache for widget config, tenant, FAQ, business hours, corrections, website content.
- [x] Lazy load the chat widget script — DONE 2026-03-15 Cycle 49. Added async attribute to all embed code locations.
- [x] Set up scheduled job for automation step processing — DONE (in-process asyncio loop in main.py, runs every 60s with worker stagger)
- [x] Add pagination to /leads endpoint — DONE 2026-03-15 Cycle 56. Backend pagination + frontend Previous/Next controls + page counter.

---

_The continuous loop works through this backlog using the work hierarchy: Features → Bugs → Tests → Content → Optimization. Add tasks anytime. Mark tasks `[x]` when complete._

## Features — Researched Competitive Opportunities (2026-03-22)

- [x] [RESEARCHED] **QR code generator for widget + review links** — Generate QR codes on the dashboard that open the chat widget or Google review page when scanned. Podium uses QR codes heavily for in-store review collection. Physical businesses (restaurants, salons, contractors) can print and display them.
- [x] [RESEARCHED] **Competitor analysis dashboard** — DONE 2026-03-22 Cycle 167. Enter competitor names, get AI comparison of SEO scores, strengths, gaps, recommendations of SEO scores, review ratings, and visibility. Uses existing AI audit engine to analyze competitors. Fully buildable without external APIs.

## Features — Tier 7: Small Business Daily Operations (2026-03-24)

_Think like a plumber, dentist, salon owner, or restaurant manager. What do they need every day?_

- [x] **Appointment waitlist management** — DONE 2026-03-24. Migration 066, backend CRUD, public join endpoint, notify via email/SMS, frontend WaitlistPage.
- [x] **Lead scoring configuration** — DONE 2026-03-24. Migration 067, per-tenant customizable weights, auto-seed defaults, frontend ScoringConfigPage with sliders.
- [x] **Bulk lead status update** — DONE 2026-03-24. Checkboxes in table view, bulk action bar with stage change, assign, delete.
- [x] **Appointment confirmation via SMS/email** — DONE 2026-03-24. Auto-sends email + SMS confirmation on booking via booking.py.
- [x] **Customer birthday automation** — DONE 2026-03-24. send_birthday_greetings() in automation engine. Fixed operator precedence bug.
- [x] **Dashboard quick actions widget** — DONE 2026-03-24. Quick Book + Add Lead modals, Send Campaign navigation.
- [x] **Lead activity timeline on detail drawer** — DONE 2026-03-24. Backend endpoint aggregates activity_log + appointments + email_events. Visual timeline in LeadDetailDrawer.
- [x] **Recurring invoice generation** — DONE 2026-03-24. process_recurring_invoices() in automation loop (30min tier).
- [ ] **Appointment no-show tracking** — Mark appointments as "no-show" and track no-show rate per lead and overall. Helps businesses identify unreliable customers.
- [x] **Email template preview with sample data** — DONE 2026-03-24. resolveTemplateVars() with highlighted sample values in SequenceBuilder.
- [ ] **Conversation search** — Search across all conversations by keyword. Currently conversations can only be filtered by tags, not searched by content.
- [x] **Lead notes quick-add from conversations** — DONE 2026-03-24. Lead Note button on ConversationsPage with inline textarea.
- [x] **Webhook retry mechanism** — DONE 2026-03-24. Exponential backoff: 3 retries at 5s, 15s, 60s.
- [ ] **Dashboard mobile responsive fixes** — Audit all dashboard pages for mobile responsiveness. Many pages are built desktop-first with fixed widths.
- [x] **Appointment type selection in booking page** — DONE 2026-03-24. Service type radio selector on public booking page.
- [ ] **Lead import from Google Contacts** — Import leads from Google Contacts CSV export format. Map Google Contacts fields to lead fields automatically.
- [x] **Auto-archive old conversations** — DONE 2026-03-24. Background task in 30-min tier, archives conversations inactive >30 days.
- [x] **Invoice payment webhook notification** — DONE 2026-03-24. Stripe checkout.session.completed handler for invoice payments.
- [ ] **AI chatbot knowledge base panel** — Show a "Knowledge Sources" panel on SettingsPage showing what the AI knows: FAQ count, website pages crawled, feedback corrections count.
- [x] **Team member activity log** — DONE 2026-03-24. TeamActivityPage + GET /team/{tenant_id}/activity endpoint.

## Features — Tier 8: Production Hardening & Growth (2026-03-24)

_Think like a business owner who is live in production with real customers. What breaks? What's missing?_

- [x] [P1] [fix]: Appointment double-booking race condition — DONE 2026-03-25. Pre-insert overlap check + graceful DB constraint handling. Returns 409.
- [x] [P1] [fix]: Widget session cleanup — DONE 2026-03-25. prune_stale_widget_sessions() in 30-min automation tier.
- [x] [P1] [fix]: Invoice number uniqueness — DONE 2026-03-25. Migration 068. Retry 3x on conflict.
- [x] [P2] [feat]: Appointment reschedule page — DONE 2026-03-25. HMAC-signed reschedule links in confirmation emails.
- [ ] [P2] [feat]: Lead deduplication on import — CSV import should check for existing leads by email/phone before creating duplicates | Files: backend/routers/leads.py | Done when: CSV import skips or merges duplicates with a count summary
- [x] [P2] [feat]: Bulk invoice send — DONE 2026-03-25. Checkbox selection, max 50 per request.
- [x] [P2] [feat]: Dashboard KPI cards — DONE 2026-03-25. Week-over-week delta badges.
- [x] [P3] [feat]: Lead export to CSV — DONE 2026-03-25. Export button on LeadsPage with filters.
- [x] [P3] [feat]: Appointment calendar sync link — DONE 2026-03-25. iCal feed endpoint.
- [ ] [P3] [feat]: Client portal appointment self-service — Let clients cancel or reschedule appointments from their portal | Files: backend/routers/client_portal.py, frontend/src/pages/ClientDashboardPage.jsx | Done when: portal shows cancel/reschedule buttons
- [ ] [P2] [test]: End-to-end appointment booking flow — Test public booking page submit -> appointment created -> confirmation email sent -> lead linked | Files: tests/ | Done when: integration test covers full flow
- [ ] [P2] [test]: Invoice payment flow — Test Stripe webhook handler correctly marks invoice paid and fires webhook event | Files: tests/ | Done when: mock Stripe event properly updates invoice
- [ ] [P2] [test]: Lead CRUD with permissions — Test owner, admin, member, viewer can/cannot create/update/delete leads | Files: tests/ | Done when: all 4 role levels tested
- [ ] [P3] [test]: Birthday greeting dedup — Test that same lead doesn't get two birthday emails in one year | Files: tests/ | Done when: second call returns 0 sent
- [ ] [P3] [test]: Recurring invoice generation — Test process_recurring_invoices creates child invoice and advances next_invoice_date | Files: tests/ | Done when: parent's next_invoice_date is advanced after processing
- [ ] [P2] [fix]: Conversation channel display on mobile — Channel badges (Chat/SMS) overflow on narrow screens | Files: frontend/src/pages/ConversationsPage.jsx | Done when: badges wrap properly on 375px width
- [ ] [P3] [feat]: Webhook delivery dashboard — Show recent webhook deliveries with status (success/failed/retrying) per webhook | Files: backend/routers/webhooks.py, frontend/src/pages/WebhooksPage.jsx | Done when: webhook detail view shows delivery log
- [ ] [P3] [feat]: AI conversation summary on conversation list — Show a one-line AI summary next to each conversation in the list | Files: backend/routers/auth.py, frontend/src/pages/ConversationsPage.jsx | Done when: summary appears under lead name
- [ ] [P4] [chore]: Create requirements.txt from installed packages — Track all Python dependencies for deployment reproducibility | Files: requirements.txt | Done when: pip freeze output is committed
- [ ] [P4] [chore]: Add loading skeleton to TeamActivityPage — Currently shows nothing while loading | Files: frontend/src/pages/TeamActivityPage.jsx | Done when: SkeletonLoader shows during load

## Features — Tier 9: Retention & Revenue Optimization (2026-03-25)

_Think like a business owner who is paying $249/mo. What makes them stay? What makes them upgrade?_

- [ ] [P1] [fix]: Stale automation executions — Executions stuck in 'running' for >24h should be marked 'failed' with reason | Files: backend/services/automation_engine.py | Done when: stuck executions auto-fail after 24h
- [ ] [P1] [fix]: Email bounce handling — Resend webhook for bounces should mark lead's email as invalid and skip future sends | Files: backend/routers/stripe_webhooks.py, backend/services/email_sender.py | Done when: bounced emails set a flag and automations skip them
- [ ] [P1] [fix]: Chat widget reconnection — Widget loses connection after laptop sleep/resume and doesn't recover | Files: widget/agentnexlify-widget.js | Done when: widget auto-reconnects and resumes session after network loss
- [ ] [P2] [feat]: Lead pipeline stage automations — Auto-trigger actions when a lead moves between pipeline stages (send email, create task, notify team) | Files: backend/routers/pipeline.py, backend/services/automation_engine.py | Done when: stage change fires configured actions
- [ ] [P2] [feat]: Appointment type-based pricing display — Show service price next to appointment type on booking page | Files: backend/routers/booking_page.py | Done when: public booking page shows "$XX" next to each service option
- [ ] [P2] [feat]: Dashboard calendar view — Full calendar view of appointments on the dashboard with month/week/day toggles | Files: frontend/src/pages/Dashboard/CalendarView.jsx | Done when: interactive calendar shows appointments with click-to-detail
- [ ] [P2] [feat]: Conversation assignment auto-notification — When a conversation is assigned to a team member, email/SMS them | Files: backend/routers/conversation_inbox.py | Done when: assigned member gets email notification with conversation link
- [ ] [P2] [feat]: Revenue dashboard — Monthly revenue tracking from paid invoices, MRR chart, pipeline value | Files: backend/routers/analytics.py, frontend/src/pages/AnalyticsPage.jsx | Done when: revenue section on analytics page with chart
- [ ] [P3] [feat]: Lead activity email digest — Daily/weekly email to business owner summarizing new leads, hot leads, missed calls | Files: backend/services/automation_engine.py | Done when: configurable digest email goes out on schedule
- [ ] [P3] [feat]: Client portal messaging — Let clients send messages through their portal that appear in conversations | Files: backend/routers/client_portal.py | Done when: client can type a message and it appears in dashboard inbox
- [ ] [P3] [feat]: Invoice late fee auto-calculation — Auto-add late fee to overdue invoices based on configurable percentage | Files: backend/services/automation_engine.py, backend/routers/invoices.py | Done when: overdue invoices auto-recalculate with late fee
- [ ] [P2] [test]: Appointment reschedule flow — Test signed URL generation, page render, slot selection, reschedule submit, cancel | Files: tests/ | Done when: full reschedule flow covered
- [ ] [P2] [test]: Bulk invoice send — Test sending 5 invoices, verify status updates, handle mixed success/failure | Files: tests/ | Done when: bulk send returns correct sent/failed counts
- [ ] [P2] [test]: KPI delta calculation — Test week-over-week comparison with known data, zero previous week, equal weeks | Files: tests/ | Done when: delta percentages verified for edge cases
- [ ] [P3] [test]: iCal feed format — Test that generated .ics file validates and imports into Google Calendar | Files: tests/ | Done when: iCal output parses correctly
- [ ] [P3] [test]: Lead CSV export — Test that exported CSV contains correct columns, handles special characters, respects filters | Files: tests/ | Done when: CSV output matches filtered lead data
- [ ] [P2] [fix]: Appointment status transitions — No validation that status changes follow valid paths (e.g. can't go from cancelled to confirmed) | Files: backend/services/booking.py | Done when: invalid transitions return 400 error
- [ ] [P3] [feat]: Smart lead scoring recalculation — Trigger lead score recalculation when lead data changes (new note, new message, appointment completed) | Files: backend/services/lead_scoring.py | Done when: score updates automatically on relevant events
- [ ] [P4] [chore]: Consolidate duplicate error handling patterns — Many routers have identical try/except blocks for Supabase queries | Files: backend/utils/db_helpers.py | Done when: shared helper reduces duplicate error handling by 50%
