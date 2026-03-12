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
- [ ] **Widget file/image upload** — Let visitors send screenshots or documents in chat. Requires file upload endpoint + S3/Supabase storage. (Carried from previous backlog.)

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

- [ ] **Review aggregation backend** — Build a service that connects to Google Business Profile API and pulls reviews for the tenant's business. Store reviews in a new `reviews` table (id, tenant_id, platform, author, rating, text, ai_response, responded, created_at). Create the migration file.
- [ ] **Reviews dashboard page** — New "Reviews" tab in the dashboard. Shows all reviews across platforms in one feed. Filter by platform, rating, responded/unresponded. Show average rating prominently.
- [ ] **AI review response drafting** — For each review, an "AI Draft Response" button that generates a professional, personalized response using Claude API. The tone should match the business (friendly for restaurants, professional for law firms). Owner can edit before posting.
- [ ] **Auto review request after appointment** — When an appointment is marked complete, automatically send an SMS or email to the customer asking them to leave a review. Include a direct link to Google/Yelp. Configurable: on/off, delay (immediately, 1 hour, 24 hours), which platform to link to.
- [ ] **Review analytics** — Average rating over time, response rate, sentiment trends. Simple charts on the Reviews page.
- [ ] **Google Business Profile OAuth** — Let the tenant connect their GBP account so we can pull reviews and eventually post responses directly. Store OAuth tokens securely.

## Features — Module: Smart Outreach
_AI-powered follow-up sequences and lead nurturing from the dashboard._

- [ ] **Outreach sequence builder** — Dashboard page where tenant creates email/SMS sequences triggered by lead events. Example: "When a new lead is captured → wait 1 hour → send welcome email → wait 2 days → send follow-up → wait 5 days → send offer." Visual builder or simple step list.
- [ ] **AI email writer** — When creating a sequence step, the tenant describes what they want ("follow up about their kitchen remodel quote") and AI drafts the email. Tenant can edit.
- [ ] **Sequence execution engine** — Backend service that processes scheduled sequence steps. Checks for due steps every few minutes (cron job or Supabase scheduled function). Sends via Resend (email) or Twilio (SMS). Logs delivery status.
- [ ] **Lead re-engagement campaigns** — Ability to select a group of leads (by stage, date range, or tag) and send a one-time blast email/SMS. AI drafts the message based on the segment.
- [ ] **Outreach analytics** — Open rates, reply rates, click rates (for emails with links). Show which sequences perform best. Dashboard widget.
- [ ] **Unsubscribe handling** — Every outreach email must include an unsubscribe link. Track unsubscribes. Never send to unsubscribed leads. This is legally required (CAN-SPAM).

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
