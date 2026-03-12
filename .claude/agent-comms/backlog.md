# AgentNexLiFy Work Backlog

_The continuous loop reads this file every cycle and works top to bottom within each section. Add tasks anytime — the loop picks them up automatically._

_Last updated: 2026-03-12_

---

## Features — Tier 1: "I need this to pay you money"
_These are the features a customer needs before they'll upgrade from free._

- [x] **Email notifications for new leads** — done 2026-03-12. Added `_send_new_lead_email_notification()` in widget.py, wired into both auto-capture and manual submit paths.
- [x] **Conversation export** — done 2026-03-12. Added "Export Transcript" button to ConversationsPage that downloads conversation as .txt file.
- [x] **Lead import via CSV** — done 2026-03-12. Backend: POST /api/v1/leads/{tenant_id}/import with UploadFile. Frontend: Import CSV button on LeadsPage with result banner. Dedup by email, max 500 rows, fires webhooks.
- [x] **Email template editor** — done 2026-03-12. Reusable template library (backend CRUD + migration 014) with 6 starter templates. SequenceBuilder enhanced with template picker, formatting toolbar, variable insertion, and live HTML preview panel. Templates can be saved from steps and reused across sequences.

## Features — Tier 2: "This would make my life easier"
_These make the product sticky — once they use these, they won't leave._

- [x] **Quick reply / follow-up from dashboard** — done 2026-03-12. Backend: POST /api/v1/leads/{tenant_id}/{lead_id}/email. Frontend: inline email compose in LeadDetailDrawer with subject/message fields. Auto-updates lead status from "new" to "contacted".
- [x] **Appointment reminders** — done 2026-03-12. Background function `send_appointment_reminders()` runs every 60s in the automation loop. Sends email + SMS at 24h and 1h before appointments. Dedup via notes field tags. No new migration needed.
- [x] **Business hours awareness in AI** — done 2026-03-12. Injected business hours + current open/closed status into chat system prompt. AI now knows schedule and can tell visitors when the business is open/closed.
- [x] **Multi-language support** — done 2026-03-12. Added instruction to system prompt: "ALWAYS respond in the same language the visitor uses." Claude handles detection natively — no separate detection library needed.
- [x] **Widget offline message** — done 2026-03-12. Migration 015 adds is_online/offline_message to widget_configs. Backend: toggle endpoint + offline contact form submission. Widget JS: detects offline status, shows contact form. Frontend: online/offline toggle on WidgetPage.
- [x] **Dashboard notifications center** — done 2026-03-12. Backend: GET /api/v1/notifications/{tenant_id} aggregates leads/conversations/appointments/activity. Frontend: NotificationBell component with dropdown, badge count, 60s polling.

## Features — Tier 3: "This makes me look professional"
_These differentiate from competitors and justify higher-tier pricing._

- [x] **Review/rating request** — Already complete. Template in sequences.py with appointment_completed trigger. Resolves {{review_link}} from tenant.google_review_link. Configurable in Settings. In TemplateGallery.
- [x] **Recurring appointment support** — done 2026-03-12. Migration 017 adds recurrence columns. Backend: POST /{tenant_id}/{appointment_id}/recur generates series. Frontend: Calendar edit modal with "Make Recurring" UI (weekly/biweekly/monthly + end date).
- [x] **Auto-tagging leads** — done 2026-03-12. Migration 016 adds tags TEXT[] to leads. Claude extracts tags from conversations during lead capture. Tags shown in LeadsPage table and LeadDetailDrawer.
- [x] **Conversation tagging** — done 2026-03-12. Migration 018 adds tags TEXT[] to conversations. Backend: PUT tags endpoint. Frontend: tag pills on sidebar, filter dropdown, inline add/remove.
- [x] **Lead merge** — done 2026-03-12. Backend: GET /duplicates finds matches by email/phone, POST /merge does keep-and-absorb merge. Frontend: "Find Duplicates" button on LeadsPage with merge modal.
- [x] **Widget file/image upload** — done 2026-03-12. Backend: POST /api/v1/widget/upload with multipart form, validates type/size, stores in Supabase Storage chat-attachments bucket. Widget JS: paperclip button, inline image preview, file download links. Both widget copies synced.

## Features — Tier 4: "I want the full platform"
_Operations-tier features that justify the premium plan._

- [ ] **Zapier integration polish** — Ensure the webhook payloads include all useful fields (lead name, email, phone, conversation summary, appointment details). Document the webhook schema. Build 2-3 example Zaps (lead → Google Sheet, appointment → Google Calendar, new conversation → Slack notification).
- [ ] **Team permissions enforcement** — Team roles (owner/admin/member/viewer) exist in the DB and sidebar, but role-based access isn't fully enforced on backend endpoints. Add middleware that checks role before allowing writes to settings, billing, team management.
- [ ] **Lead assignment** — Assign leads to specific team members. Notify them. Track who's working which lead. Add assigned_to column to leads, filter views per agent.
- [ ] **Conversation AI tuning** — Let the business owner rate AI responses (thumbs up/down) and provide corrections. Store ratings, use feedback to refine system prompts per tenant over time.
- [ ] **Bulk SMS campaigns** — Let business owners send a text to all their leads or a filtered segment ("all leads from last 30 days who haven't booked"). Requires careful Twilio compliance (opt-in, STOP handling).
- [ ] **Stripe subscription management in dashboard** — Upgrade/downgrade/cancel directly from BillingPage without leaving to Stripe portal. The portal link exists but inline management is smoother. (Carried from previous backlog.)

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

- [ ] **Content input page** — Dashboard page where tenant pastes a blog post, writes a description of a recent job/project, or uploads a text file. This is the "source content."
- [ ] **AI content repurposer** — Takes the source content and generates platform-specific versions: LinkedIn post (professional tone, 150-300 words), Facebook post (casual, with emoji), Instagram caption (short, hashtags), Google Business Profile update (local SEO optimized), email newsletter snippet, Twitter/X thread (short punchy posts). Each version follows platform best practices for length, tone, and formatting.
- [ ] **Content preview and edit** — Show all generated versions side by side. Tenant can edit any of them before publishing.
- [ ] **Content calendar** — Simple calendar view showing scheduled posts. Tenant can schedule content for future dates.
- [ ] **Direct publishing (phase 2)** — Connect to Google Business Profile API to post updates directly. Other platforms (LinkedIn, Facebook) require their own OAuth flows — mark as future.
- [ ] **Content library** — Save generated content for reuse. Searchable by date, platform, topic.

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

- [ ] **Job posting page** — Tenant creates a job post from the dashboard: title, description, pay range, schedule, location, required skills (tags, not resume). Stored in a new `jobs` table.
- [ ] **Public job page** — Jobs are visible at agentnexlify.com/jobs/{slug} or embedded on the tenant's business page. Simple, mobile-first design. No account required to view.
- [ ] **SMS-first application** — Applicant clicks "Apply" and enters name, phone, and a short message. They get an SMS confirmation. The business owner gets an SMS notification with the applicant's info. No resume upload, no account creation — trades workers don't use those.
- [ ] **Applicant management** — Dashboard page showing applicants per job. Mark as: new, contacted, interviewed, hired, rejected. Add notes.
- [ ] **AI job description writer** — Tenant describes the role in plain language ("I need someone to help with junk removal 3 days a week"), AI generates a proper job posting optimized for the role.
- [ ] **Job widget integration** — The chat widget can mention open jobs when relevant. If someone chats "are you hiring?" the AI knows about open positions and can direct them to apply.

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

- [ ] **Missed call detection** — Twilio webhook detects when a call isn't answered (goes to voicemail or rings out). Triggers the text-back flow.
- [ ] **Auto text-back message** — Sends an SMS within 30 seconds: "Hi! Sorry we missed your call at [Business Name]. How can we help?" The AI then handles the SMS conversation using the same chat engine that powers the widget.
- [ ] **SMS conversation threading** — Track the SMS conversation in a new `sms_conversations` table (or extend chat_sessions with a channel type: 'widget' | 'sms' | 'call'). All messages appear in the dashboard alongside widget conversations.
- [ ] **Lead capture from SMS** — When the caller provides their name/email/need via text, create a lead. Same extraction logic as the widget.
- [ ] **Configurable text-back settings** — Dashboard toggle: enable/disable, customize the greeting message, set quiet hours (don't text at 2am), set max texts per conversation.
- [ ] **Missed call analytics** — Dashboard widget showing: calls missed per day, text-back response rate, leads captured from missed calls. This data alone justifies the subscription — "You missed 23 calls this month. We captured 18 of them via text."

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
- [ ] Test signup with an email that already exists — does it show a helpful error or crash?
- [ ] Test what happens when Claude API is slow or down — does the widget hang or show an error?
- [ ] Test what happens when Supabase is paused (free tier) — does the app show a helpful error or just break?
- [ ] Verify automation sequence execution runs on a schedule — the engine exists but needs a scheduled job runner (cron or Railway cron) to call process_pending_steps()

## Tests — Coverage Gaps

- [x] Test signup flow with duplicate email — done 2026-03-12
- [x] Test chat endpoint with empty message body — covered in lead extraction tests 2026-03-12
- [x] Test lead capture with partial info (name but no email) — done 2026-03-12
- [x] Test appointment booking with overlapping time slots — done 2026-03-12 (12 tests)
- [x] Test webhook delivery and retry logic — done 2026-03-12 (18 tests)
- [x] Test Stripe webhook signature verification — done 2026-03-12 (7 tests)
- [ ] Test widget CORS from external domain (carried from previous backlog)
- [ ] Test automation sequence execution order (carried from previous backlog)
- [ ] Test login flow: valid login, wrong password, non-existent email, expired token
- [ ] Test chat endpoint edge cases: very long message, rapid consecutive messages, invalid tenant_id, invalid session_id
- [ ] Test lead capture: malformed email, international phone formats
- [ ] Test appointments: past date booking, timezone handling across DST boundaries
- [ ] Test business page: valid slug, non-existent slug, slug with special characters
- [ ] Test CORS: request from allowed origin, request from disallowed origin
- [ ] Test rate limiting: if it exists, verify it works. If not, consider adding it.
- [ ] Test Google Calendar OAuth: expired token refresh, disconnected account behavior
- [ ] Test team invites: expired invite token, already-accepted invite, invalid role

## Content — Marketing & Docs

- [x] Welcome email for new signups — done 2026-03-12
- [x] "How to embed the widget" help article — done 2026-03-12
- [ ] **Help article: "How to configure your AI assistant"** — step-by-step guide for adding FAQs, business info, and training the AI
- [ ] **Help article: "Understanding your analytics dashboard"** — what each metric means
- [ ] **Help article: "Managing your leads"** — how to use the pipeline, export, follow up
- [ ] **Help article: "Setting up appointment booking"** — how the calendar integration works, business hours, Google Calendar sync
- [ ] **Onboarding email sequence:**
  - Day 0: Welcome + getting started (already written)
  - Day 1: "Configure your AI" — prompt them to add business info and FAQs
  - Day 3: "Your first conversation" — tips for getting the most out of the widget
  - Day 7: "How's it going?" — check in, link to upgrade if they're getting value
  - Day 14: "You're missing out" — highlight features on paid tiers
- [ ] **Case study template** — after first real customer succeeds, fill this in with their story
- [ ] **Landing page A/B copy variants** — 3 different hero headlines to test
- [ ] **Social media posts** — 10 posts for LinkedIn and Facebook targeting small business owners. Focus on pain points (missed leads, after-hours inquiries, no-shows) not features.
- [ ] FAQ entries for common widget questions (carried from previous backlog)

## Optimization

- [ ] Add rate limiting to all public endpoints (prevent abuse of /api/v1/widget/chat, /biz/{slug})
- [ ] Add request logging middleware (track API usage per tenant for billing/quota enforcement)
- [ ] Optimize database queries — add indexes on commonly queried columns (leads.client_id + created_at, chat_messages.tenant_id + session_id, appointments.tenant_id + start_time)
- [ ] Add caching for tenant/widget configuration (the widget loads tenant config on every page view via /api/v1/widget/config/{api_key} — cache with 5-min TTL)
- [ ] Lazy load the chat widget script (don't block the customer's page load — async + defer)
- [ ] Set up scheduled job for automation step processing (Railway cron or background worker to call process_pending_steps() every minute)

---

_The continuous loop works through this backlog using the work hierarchy: Features → Bugs → Tests → Content → Optimization. Add tasks anytime. Mark tasks `[x]` when complete._
