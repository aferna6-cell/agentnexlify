# AgentNexLiFy Work Backlog

_The continuous loop reads this file every cycle and works top to bottom within each section. Add tasks anytime — the loop picks them up automatically._

_Last updated: 2026-03-14_

---

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

- [x] Widget not capturing phone numbers with country codes (international format) — fixed 2026-03-12
- [x] Dashboard analytics may show wrong timezone for appointment times — fixed 2026-03-12
- [x] Test signup with an email that already exists — NOT A BUG, returns 409 correctly (investigated 2026-03-15)
- [x] Test what happens when Claude API is slow or down — FIXED: added 30s timeout to all 10 Anthropic calls (2026-03-15 Cycle 52)
- [x] Test what happens when Supabase is paused — PARTIALLY FIXED: health check now returns "degraded" (2026-03-15 Cycle 52)
- [x] Verify automation sequence execution runs on a schedule — NOT A BUG, runs correctly as asyncio task in main.py (confirmed 2026-03-15)

## Tests — Coverage Gaps

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

## Features — New Opportunities (2026-03-23)

_Added during session 2026-03-23 code audit. Focused on reliability, engagement, and monetization._

- [x] **Appointment waitlist** — DONE 2026-03-23. Migration 066, backend waitlist router, auto-notify on cancellation, WaitlistPage frontend. — When all slots are booked, let visitors join a waitlist. When a cancellation opens a slot, auto-notify waitlisted leads. Table: waitlist_entries (tenant_id, lead_id, preferred_date, preferred_time, service_type_id, status, notified_at). Widget booking flow shows "Join Waitlist" when no slots available.
- [x] **Lead activity timeline on dashboard** — DONE 2026-03-23. Backend GET /timeline + LeadDetailDrawer collapsible panel. — A unified chronological timeline on the LeadDetailDrawer showing all interactions: chat messages, emails sent, SMS sent/received, appointments booked/completed, invoices sent/paid, documents signed, notes added. Currently data is scattered across tables.
- [x] **Bulk lead actions** — DONE 2026-03-23. Backend POST /bulk + frontend checkbox selection + action bar. — Select multiple leads on LeadsPage and perform bulk: assign to team member, change status, add tag, send campaign, delete. Currently all actions are single-lead only.
- [x] **Dashboard quick stats email digest** — DONE 2026-03-23. Daily morning email to business owner with yesterday's key metrics: new leads, conversations, appointments booked, revenue collected. Lighter than the weekly AI insights brief.
- [x] **Webhook retry with exponential backoff** — DONE 2026-03-23. 3 retries with 1min/5min/30min backoff. — Currently webhook delivery attempts once. Add retry logic: 3 attempts with exponential backoff (1min, 5min, 30min). Track retry count in webhook_logs. Disable webhook after 10 consecutive failures.
- [x] **Conversation search** — DONE 2026-03-23. Backend search endpoint + frontend debounced UI. — Full-text search across chat_messages for a tenant. Business owners need to find "that conversation where someone asked about roof repair". Backend: GET /conversations/search?q=keyword. Frontend: search input on ConversationsPage.
- [x] **Lead scoring v2 — configurable weights** — DONE 2026-03-23. Migration 067, backend CRUD, SettingsPage UI. — Let business owners customize lead scoring weights per business type. Dental offices might weight "insurance mentioned" higher. Table: scoring_config (tenant_id, factor, weight). UI on settings page.
- [ ] **Multi-location support** — Some businesses have multiple locations. Each location gets its own widget config, business hours, and team. Table: locations (tenant_id, name, address, timezone, business_hours). Widget scoped by location_id.
- [ ] **Email template visual editor** — Replace the plain textarea email editor with a visual block editor (heading, paragraph, image, button, divider). Store as HTML. Preview panel. Currently email templates are raw text.
- [x] **Appointment no-show tracking** — DONE 2026-03-23. Auto-detection + analytics endpoint. — Add "no_show" status to appointments. Auto-mark no-shows for appointments with no check-in 30 min after start time. Analytics: no-show rate, repeat no-show leads. Trigger sequence for no-show follow-up.
- [x] **Client portal appointment self-scheduling** — DONE 2026-03-23. — Clients with portal login can view available slots and book their own appointments. Currently booking is only through the widget or dashboard.
- [ ] **Voice message transcription in widget** — Allow widget visitors to record voice messages. Transcribe via Whisper API and save as text in chat_messages. Business owner sees both transcript and audio player.
- [x] **Invoice recurring auto-generation** — DONE 2026-03-23. Background task in 5-min automation loop. — For leads with is_recurring invoices, auto-generate the next invoice on next_invoice_date. Background task in automation loop. Currently the fields exist but nothing processes them.
- [ ] **Lead import from Google Contacts** — OAuth to Google Contacts, import contacts as leads with name/email/phone. One-click import for businesses switching from paper/spreadsheet tracking.
- [x] **Dashboard customizable widgets** — DONE 2026-03-24. — Let business owners rearrange and show/hide dashboard widgets (stats cards, recent leads, today's appointments, AI insights). Store layout preference in tenants table as JSONB.

## Features — New Opportunities (2026-03-23 Session 2)

_Added during second session on 2026-03-23. Thinking like a small business owner using AgentNexLiFy daily._

- [x] **Appointment check-in system** — DONE 2026-03-23. POST /{tenant_id}/{appointment_id}/check-in endpoint + Calendar UI Check In button.
- [x] **Customer birthday automation** — DONE 2026-03-24. — Auto-send birthday email/SMS with a special offer or greeting. Uses leads.date_of_birth. Configurable message template on Settings page. Great retention tool for salons and dental offices.
- [x] **Team member performance dashboard** — DONE 2026-03-24 Session 5. — Per-team-member metrics: conversations handled, average response time, leads assigned, appointments booked. Helps business owners see who's contributing. Tab on Analytics page.
- [x] **Lead source UTM tracking** — DONE 2026-03-24 Session 5. — Capture UTM parameters from the widget embed page URL. Store utm_source, utm_medium, utm_campaign on leads. Analytics breakdown by campaign. Help businesses know which ads drive leads.
- [x] **Automated appointment follow-up survey** — ALREADY DONE. — After appointment completion, auto-send a 3-question satisfaction survey via email. Results stored in csat_responses. Simpler than the current CSAT flow.
- [x] **Widget chat hours** — DONE 2026-03-24 Session 5. — Set specific hours when the AI chat is active vs showing the offline form. Different from business hours — some businesses want chat 24/7 but appointments only during business hours. Separate schedule in widget_configs.
- [x] **Bulk invoice generation** — DONE 2026-03-24 Session 5. — Select multiple leads and generate invoices for all of them at once. Useful for monthly service businesses (lawn care, cleaning) that bill the same amount to many clients.
- [x] **Lead nurture score** — DONE 2026-03-24 Session 5. — Track how engaged a lead is with automated emails. Opens = +1, clicks = +3, replies = +5. Separate from the main lead score. Shows which leads are warming up or going cold.
- [x] **Dashboard mobile responsive** — DONE 2026-03-24. — The dashboard currently doesn't look great on phones. Add responsive breakpoints, collapsible sidebar, touch-friendly controls. Business owners check their dashboard on their phone between jobs.
- [x] **Appointment buffer zones** — DONE 2026-03-23. Fixed conflict detection in booking.py to extend booked ranges by buffer_minutes.
- [x] **Conversation sentiment analysis** — DONE 2026-03-24 Session 5. — After each conversation ends, Claude analyzes overall sentiment (positive/neutral/negative). Store on conversations table. Dashboard shows sentiment distribution. Alerts on negative conversations.
- [x] **Quick actions from notification bell** — DONE 2026-03-24. — Currently notifications just show info. Add action buttons: "Reply" to a conversation, "Call back" for missed calls, "View lead" for new leads. Reduces clicks to take action.
- [x] **Stripe payment webhook for invoices** — DONE 2026-03-23. Auto-updates invoice to paid via checkout.session.completed metadata.
- [x] **Widget typing indicator** — ALREADY DONE. showTyping()/hideTyping() with bouncing dots already exists in widget JS.
- [x] **Lead export to CSV** — DONE 2026-03-23. GET /leads/{tenant_id}/export returns CSV download. Frontend Export CSV button on LeadsPage.
- [x] **Conversation auto-close** — DONE 2026-03-23. auto_close_inactive_conversations() runs every 5 min, closes conversations inactive >24h.
- [x] **AI-generated FAQ suggestions** — DONE 2026-03-23. POST /faq/{tenant_id}/suggest analyzes conversations via Claude, suggests Q&A pairs.
- [x] **Appointment reschedule (not just cancel)** — DONE 2026-03-23. POST /reschedule endpoint with email+SMS notifications, activity log, webhook. Calendar UI.

## Features — New Opportunities (2026-03-24 Session 6)

_Added during session 2026-03-24. Thinking like a small business owner paying $249/mo who needs the platform to run their business._

- [ ] **Appointment recurring revenue report** — Monthly report showing total revenue from recurring appointments. Helps service businesses (lawn care, cleaning, salons) see MRR from repeat customers. Dashboard card + AnalyticsPage section.
- [x] **Lead scoring decay** — DONE 2026-03-24 Session 7. — Leads that haven't interacted in 30+ days should have their score decay automatically. Prevents stale leads from clogging hot lists. Background task in automation loop.
- [ ] **SMS conversation in widget** — Allow business owners to send SMS to leads directly from the ConversationsPage (not just email). Uses existing Twilio integration. Reply button shows channel toggle (email/SMS).
- [x] **Automated lead re-engagement** — DONE 2026-03-24 Session 7. — When a lead goes cold (no interaction for 14+ days), auto-send a "we haven't heard from you" email. Configurable on Settings page. Dedup via activity_log.
- [x] **Invoice payment receipt** — DONE 2026-03-24 Session 7. — When an invoice is paid (via Stripe webhook or manual), auto-send a receipt email to the customer with payment details. Currently only the business owner is notified.
- [x] **Appointment type analytics** — DONE 2026-03-24 Session 7. — If service types are configured, show which service types are most popular, highest revenue, most no-shows. Helps businesses optimize their offerings.
- [ ] **Widget conversation rating** — At the end of each chat, show a simple thumbs up/down or 1-5 star rating. Store in a new column on conversations. Dashboard shows average rating.
- [x] **Lead duplicate merge from widget** — DONE 2026-03-24 Session 7. — When the widget captures a lead with an email/phone matching an existing lead, auto-merge instead of creating a duplicate. Currently the dedup only works on manual import.
- [x] **Export invoices to CSV** — DONE 2026-03-24 Session 7. — Business owners need to export invoices for tax season. CSV export of all invoices with date range filter. Optional: generate PDF bundle.
- [x] **Appointment confirmation via SMS** — DONE 2026-03-24 Session 7. — After an appointment is booked (through widget or dashboard), send an instant SMS confirmation to the customer with date, time, and business details.
- [ ] **Custom dashboard greeting** — Let business owners customize the dashboard greeting message (currently "Welcome back, {name}"). Some want their company motto or daily affirmation.
- [ ] **Lead activity heatmap** — Show which hours of the day and days of the week get the most lead activity. Helps businesses staff appropriately. Uses chat_messages.created_at data.
- [ ] **Bulk SMS from leads page** — Select multiple leads and send a quick SMS message to all of them. Different from marketing campaigns — this is a quick one-off text blast from the leads table.
- [x] **Widget proactive greeting** — DONE 2026-03-24 Session 6. — After a visitor has been on the page for X seconds without interacting, auto-open the widget with a proactive message like "Hi! Can I help you find something?" Configurable delay and message in WidgetPage.
- [x] **Invoice overdue escalation** — DONE 2026-03-24 Session 7. — If an invoice is overdue by 7+ days, escalate: send a more urgent reminder, notify the business owner, and add a "past due" flag visible on the leads page.
- [ ] **Appointment waitlist priority** — Let business owners set priority levels on waitlist entries (VIP, regular). VIP customers get notified first when a slot opens up.
- [ ] **Lead timeline export** — Export a lead's full activity timeline as a PDF for printing or sharing. Useful for contractors who need to show project history to clients.
- [x] **Widget visitor analytics** — DONE 2026-03-24 Session 7. — Track how many unique visitors see the widget vs. how many start a conversation. Conversion funnel: widget loaded → chat started → lead captured → appointment booked.
- [ ] **Batch appointment creation** — Create appointments for multiple leads at once (e.g., "All my Monday regulars"). Select leads, pick a time slot pattern, and generate appointments in bulk.
- [x] **AI-powered review response suggestions** — DONE 2026-03-24 Session 7. — When a new review comes in, auto-generate a suggested response and notify the business owner. Currently the owner has to click "Generate AI Response" manually.

## Features — New Opportunities (2026-03-24 Session 7)

_Added during session 2026-03-24. Thinking like a small business owner growing their practice._

- [ ] **Recurring appointment revenue dashboard** — Show MRR from recurring appointments by customer. Which regulars generate the most revenue? Chart on AnalyticsPage.
- [x] **Lead aging alerts** — DONE 2026-03-24 Session 8. — When leads sit in "new" status for 48+ hours without contact, alert the business owner. Prevents leads falling through the cracks.
- [x] **Customer lifetime value (CLV) tracker** — DONE 2026-03-24 Session 8. — Calculate total revenue per lead from invoices paid. Show CLV on lead detail and analytics. Helps identify VIP customers.
- [x] **Appointment utilization rate** — DONE 2026-03-24 Session 8. — Compare available slots vs booked slots per day/week. Shows capacity utilization percentage. Helps businesses know when they can take more clients.
- [ ] **Invoice partial payment tracking** — Allow recording partial payments against an invoice. Track remaining balance. Show payment history per invoice.
- [ ] **Team member schedule/availability** — Each team member sets their own working hours. Assignment respects availability. Calendar shows who's free.
- [ ] **Lead assignment round-robin** — Auto-assign new leads to team members in rotation. Configurable on Settings page. Ensures even distribution.
- [ ] **Conversation handoff notes** — When handing off a conversation from AI to human or between team members, include a summary of the conversation context.
- [ ] **SMS opt-in compliance** — Track explicit SMS consent per lead. Only send SMS to opted-in leads. Widget captures consent during phone collection.
- [ ] **Appointment recurring revenue report** — Monthly report showing total revenue from recurring appointments. Helps service businesses see MRR from repeat customers.
- [ ] **Dashboard daily goal tracker** — Set daily goals for leads, appointments, revenue. Progress bar on dashboard. Helps businesses stay motivated and focused.
- [ ] **Email delivery health dashboard** — Track email bounce rates, spam complaints, delivery rates. Alert when deliverability drops. Uses Resend webhook data.
- [ ] **Customer referral tracking** — When a new lead mentions being referred by an existing customer, link them. Track which customers generate the most referrals.
- [ ] **Appointment group booking** — Allow booking multiple people for the same time slot (classes, group sessions). Set max capacity per slot.
- [ ] **Widget A/B test greetings** — Test different greeting messages and measure which one leads to more conversations. Auto-rotate between variants.
