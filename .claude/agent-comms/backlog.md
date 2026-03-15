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
- [ ] **Action items dashboard widget** — Card on main dashboard showing pending action items sorted by due date. Quick "Mark Done" and "Dismiss" buttons. Click to see full conversation context.
- [ ] **Action items page** — Full page view with filters: status, priority, assigned_to, date range. Assign to team members. Bulk mark done/dismiss.
- [ ] **Action item notifications** — Include overdue action items in the notification bell aggregation. "You have 3 overdue action items."

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
- [ ] **Flow analytics** — Track which nodes get triggered most. Show drop-off points. "80% of visitors hit the pricing node but only 20% book — consider adding a discount offer."

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

- [ ] **Call transcription pipeline** — Use Twilio's built-in recording transcription (or Whisper API for higher quality). Store timestamped transcript in the calls table `transcript` JSONB field (array of {timestamp, speaker, text} objects).
- [ ] **AI call summary generation** — After transcription, call Claude to generate: (1) one-paragraph summary, (2) action items extracted, (3) caller sentiment (positive/neutral/negative), (4) suggested follow-up. Store as `summary` JSONB on calls table.
- [ ] **Transcript viewer UI** — Call detail page shows timestamped transcript with clickable timestamps (jump to audio moment if recording is available). Summary and action items shown in a sidebar panel.
- [ ] **Action items from calls → action_items table** — Feed extracted call action items into the same action_items table used for chat action items. Unified task list across channels.

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
- [ ] **Google Business Profile OAuth** — Let the tenant connect their GBP account so we can pull reviews and eventually post responses directly. Store OAuth tokens securely.

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
- [ ] **Direct publishing (phase 2)** — Connect to Google Business Profile API to post updates directly. Other platforms (LinkedIn, Facebook) require their own OAuth flows — mark as future.
- [x] **Content library** — done 2026-03-12. Search input filters content by title. Status filter dropdown. Combined with list view for browsable/searchable library.

## Features — Module: Local SEO Tools
_Google Business Profile optimization and local ranking intelligence._

- [ ] **GBP connection** — Reuse the Google Business Profile OAuth from the Reputation Manager module. Pull business info, hours, photos, posts, and Q&A.
- [ ] **Profile completeness score** — Analyze the tenant's GBP profile and score it (0-100%). Flag missing fields: description, hours, categories, photos, services, attributes. Give specific recommendations ("Add at least 10 photos — businesses with 10+ photos get 35% more clicks").
- [ ] **Auto-post to GBP** — Schedule weekly posts to GBP from the Content Studio. GBP posts expire after 7 days, so consistent posting is important for ranking. AI generates posts about the business's services, promotions, or seasonal content.
- [ ] **Local keyword suggestions** — Based on the business type and location, suggest keywords they should mention in their GBP description and posts. Example: a plumber in Clemson should mention "emergency plumber Clemson SC", "water heater repair Clemson".
- [ ] **Review velocity tracker** — Track how many reviews they're getting per month vs. competitors (if we can see competitor data via search APIs). More reviews = higher ranking.
- [ ] **Local SEO dashboard widget** — Summary card on the main dashboard: GBP score, review count, post frequency, top keywords.

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

- [ ] **Twilio Voice webhook endpoint** — New route that receives incoming calls via Twilio. Plays a greeting, then streams the caller's speech to Claude for real-time conversation. Store call records in a new `calls` table (id, tenant_id, caller_phone, transcript, summary, action_taken, duration, created_at). Create migration.
- [ ] **AI voice conversation handler** — Use Twilio Media Streams + Claude API to have a real-time phone conversation. The AI knows the business's name, hours, services (from tenant config). It can answer questions, take messages, and offer to book appointments.
- [ ] **Call summary + owner notification** — After each call, AI generates a one-paragraph summary. Send it to the business owner via SMS and/or email: "You missed a call from 555-1234. They asked about pricing for kitchen remodels. They want a callback tomorrow morning."
- [ ] **Call log dashboard page** — New "Calls" tab in the dashboard. Shows all calls with: time, caller number, duration, AI summary, action taken (message taken / appointment booked / question answered). Click to read full transcript.
- [ ] **Business phone number provisioning** — Let tenants get a dedicated business phone number through Twilio directly from the dashboard. Or they can forward their existing number to the Twilio number.
- [ ] **Call-to-appointment pipeline** — When the AI books an appointment during a call, it creates an entry in the appointments table and a lead in the leads table. The full call transcript is linked to the lead. Everything connects.

## Features — Module: Missed Call Text-Back
_When a call goes to voicemail, auto-text the caller with an AI agent that handles the conversation via SMS._

- [x] **Missed call detection** — DONE 2026-03-15 Cycle 60. POST /api/v1/twilio/missed-call webhook. Auto-detects no-answer/busy/failed calls.
- [x] **Auto text-back message** — DONE 2026-03-15 Cycle 60. Auto-sends "{business_name} missed your call" text within seconds. AI handles SMS replies via /api/v1/twilio/sms-reply.
- [x] **SMS conversation threading** — DONE 2026-03-15 Cycle 60. Messages stored in chat_messages with session_id=sms_{phone}. Visible in ConversationsPage alongside widget chats.
- [x] **Lead capture from SMS** — DONE 2026-03-15 Cycle 60. Lead auto-created on missed call with phone number. SMS AI replies use same chat engine that extracts lead info.
- [x] **Configurable text-back settings** — DONE 2026-03-15 Cycle 61. SettingsPage: toggle, custom message, quiet hours. Backend respects all settings.
- [x] **Missed call analytics** — DONE 2026-03-15 Cycle 61. Dashboard "Missed Calls This Week" stat card from activity_log. Per-day breakdown deferred to analytics page.

## Features — Module: Contractor Bid Manager
_AI generates professional estimates/proposals from a job description. Track bid status._

- [ ] **Bid creation flow** — Dashboard page where contractor describes the job in plain language ("3-bedroom house, need full interior paint, medium quality, Clemson SC"). AI generates a professional bid with: line items, quantities, unit prices, total, terms, warranty, timeline. Uses local pricing data where possible.
- [ ] **Bid template system** — Tenant creates reusable templates for their common jobs (e.g., "Standard Roof Replacement", "Basic Lawn Maintenance Package"). Each template has default line items that AI customizes per job.
- [ ] **PDF bid generation** — Generate a branded PDF with the business's logo, contact info, and the bid details. Professional enough to hand to a homeowner. Store in a new `bids` table (id, tenant_id, lead_id, title, items_json, total, status, pdf_url, created_at).
- [ ] **Bid tracking** — Track bid status: draft → sent → viewed → accepted → rejected → expired. Dashboard shows pipeline: how many bids out, win rate, average bid value.
- [ ] **Bid-to-lead connection** — Link bids to leads. When a customer from the chat widget asks for a quote, the conversation context flows into the bid (AI pre-fills based on what they discussed).
- [ ] **Quick bid from chat** — When the widget AI detects a quote request, it collects the job details conversationally, then generates a bid automatically. Owner reviews and sends from the dashboard.

## Features — Module: Client Portal
_Customers get a link to their portal showing invoices, job photos, warranty, and a rebook button._

- [ ] **Client portal page** — Public page at agentnexlify.com/client/{unique-token}. No login required — accessed via unique link sent to the client. Shows: business info, their service history, documents, and a rebook button.
- [ ] **Service record system** — New `service_records` table (id, tenant_id, lead_id, title, description, date, photos_json, documents_json, notes, created_at). Tenant creates a record after completing a job.
- [ ] **Photo upload for job documentation** — Tenant uploads before/after photos of completed work. Stored in Supabase Storage. Displayed in the client portal. This is gold for contractors — "here's what we did."
- [ ] **Invoice attachment** — Tenant can attach an invoice (PDF upload or simple line-item builder) to a service record. Client sees it in their portal.
- [ ] **Rebook button** — Client portal has a "Book Again" button that opens the chat widget pre-populated with their info. One-click rebooking for recurring services (cleaning, lawn care, HVAC maintenance).
- [ ] **Automated portal link delivery** — After marking a job complete, auto-send the client an SMS/email with their portal link: "Thanks for choosing [Business]! View your service details and rebook anytime: [link]"

## Features — Module: AI Review Responder
_Chrome extension that drafts review responses on Google/Yelp with one click._

- [ ] **Chrome extension scaffold** — Build a Chrome extension (manifest v3) that detects when the user is on Google Maps reviews or Yelp business page. Adds a "Draft Response" button next to each review.
- [ ] **AI response generation** — When clicked, sends the review text + star rating + business context to the AgentNexLiFy API. Claude generates a professional, personalized response. Tone matches the rating: warm and grateful for 5-star, empathetic and solution-oriented for 1-star.
- [ ] **Response customization** — Extension shows the draft in an editable popup. Owner tweaks it if needed, then clicks "Copy" to paste into the reply box. One-click workflow.
- [ ] **Business context sync** — Extension connects to the owner's AgentNexLiFy account (API key or OAuth). Pulls their business name, services, and tone preferences so responses are on-brand.
- [ ] **Response history** — Track which reviews have been responded to. Show stats in the AgentNexLiFy dashboard: total reviews, response rate, average response time.
- [ ] **Review alert integration** — Tie into the Reputation Manager module: when a new review is detected, send a notification with a direct link to respond. The extension makes responding take 10 seconds instead of 5 minutes.

## Features — Module: Local Business Autopilot
_Done-for-you digital presence: website + GBP + widget + reviews + booking in one subscription._

- [ ] **Autopilot onboarding wizard** — New onboarding flow specifically for the Autopilot tier. Collects: business name, type, address, phone, hours, services, photos. Uses this to auto-generate everything else.
- [ ] **Auto-generated business page** — Uses the hosted business page feature (already built) but enhanced: AI writes the page content (hero text, about section, services, FAQs) from the onboarding info. Professional enough to be their only web presence.
- [ ] **GBP optimization recommendations** — Based on their Google Business Profile (connected via OAuth), generate a checklist: "Add 5 more photos", "Update your description to include [keywords]", "Add these 3 services". Score their profile completeness.
- [ ] **Auto-configured widget** — Widget is pre-configured with their business info from onboarding. AI already knows their hours, services, and can book appointments on day one. No manual setup.
- [ ] **Monthly performance report** — Auto-generated email sent on the 1st of each month: conversations this month, leads captured, appointments booked, reviews received, website visits. Makes the value tangible so they never cancel.
- [ ] **Autopilot pricing tier** — Create a new premium pricing tier ($149-199/month) that bundles: hosted page + widget + review management + missed call text-back + monthly report. Position as "We handle your entire online presence."

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
- [ ] Test Google Calendar OAuth: expired token refresh, disconnected account behavior
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
