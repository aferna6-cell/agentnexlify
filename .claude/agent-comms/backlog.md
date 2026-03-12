# AgentNexLiFy Work Backlog

_The continuous loop reads this file every cycle and works top to bottom within each section. Add tasks anytime — the loop picks them up automatically._

_Last updated: 2026-03-12_

---

## Features — Tier 1: "I need this to pay you money"
_These are the features a customer needs before they'll upgrade from free._

- [x] **Email notifications for new leads** — done 2026-03-12. Added `_send_new_lead_email_notification()` in widget.py, wired into both auto-capture and manual submit paths.
- [ ] **Conversation export** — Let them download or print conversation transcripts. Some will want this for records. Add export button to ConversationsPage.
- [ ] **Lead import via CSV** — Upload leads in bulk. Every business switching from spreadsheets needs this. (Carried from previous backlog.)
- [ ] **Email template editor** — Visual editor for automation email steps. Currently templates are raw text. Business owners need a drag-and-drop or rich-text editor. (Carried from previous backlog.)

## Features — Tier 2: "This would make my life easier"
_These make the product sticky — once they use these, they won't leave._

- [ ] **Quick reply / follow-up from dashboard** — When viewing a lead in ClientProfile, let the owner send a quick email or SMS follow-up directly. SMS sending exists (sendSms) but isn't integrated into the lead detail view. Add inline compose.
- [ ] **Appointment reminders** — Auto-send SMS or email reminders to customers before their appointment (24h and 1h before). Automation sequences exist — create a pre-built "appointment reminder" automation that triggers on appointment_booked with timed steps.
- [ ] **Business hours awareness in AI** — The AI should know when the business is open/closed and respond accordingly ("We're currently closed but I can help you book for tomorrow"). Business hours config exists in the DB — inject it into the widget chat system prompt alongside FAQs.
- [ ] **Multi-language support** — Detect the customer's language and respond in it. Huge for service businesses in diverse areas. Add language detection in the widget chat endpoint and instruct Claude to respond in the detected language.
- [ ] **Widget offline message** — When the business is "offline" (if they want to control when the widget is active), show a contact form instead of live chat. Add an online/offline toggle to widget config and a fallback form in the widget JS.
- [ ] **Dashboard notifications center** — In-app notification bell showing: new leads, new conversations, appointments today, system alerts. Currently the dashboard is passive — you have to go looking. (Carried from previous backlog.)

## Features — Tier 3: "This makes me look professional"
_These differentiate from competitors and justify higher-tier pricing._

- [ ] **Review/rating request** — After a completed appointment, auto-send a request for a Google/Yelp review. Every small business wants more reviews. Google review link already exists in tenant settings — build an automation template that sends the link after appointment_completed.
- [ ] **Recurring appointment support** — For businesses with regular clients (hair salon, cleaning service, tutoring) — let them set up recurring bookings. Extend the appointments system with recurrence rules (weekly/biweekly/monthly).
- [ ] **Auto-tagging leads** — Based on conversation content, auto-tag leads (e.g., "interested in: kitchen remodel", "budget: high", "timeline: urgent"). Ask Claude to extract tags during lead capture and store them on the lead record.
- [ ] **Conversation tagging** — Tag/label conversations for organization. Add a tags field to conversations and filter UI. (Carried from previous backlog.)
- [ ] **Lead merge** — Combine duplicate leads into one record. Detect potential duplicates by email/phone and offer a merge UI. (Carried from previous backlog.)
- [ ] **Widget file/image upload** — Let visitors send screenshots or documents in chat. Requires file upload endpoint + S3/Supabase storage. (Carried from previous backlog.)

## Features — Tier 4: "I want the full platform"
_Operations-tier features that justify the premium plan._

- [ ] **Zapier integration polish** — Ensure the webhook payloads include all useful fields (lead name, email, phone, conversation summary, appointment details). Document the webhook schema. Build 2-3 example Zaps (lead → Google Sheet, appointment → Google Calendar, new conversation → Slack notification).
- [ ] **Team permissions enforcement** — Team roles (owner/admin/member/viewer) exist in the DB and sidebar, but role-based access isn't fully enforced on backend endpoints. Add middleware that checks role before allowing writes to settings, billing, team management.
- [ ] **Lead assignment** — Assign leads to specific team members. Notify them. Track who's working which lead. Add assigned_to column to leads, filter views per agent.
- [ ] **Conversation AI tuning** — Let the business owner rate AI responses (thumbs up/down) and provide corrections. Store ratings, use feedback to refine system prompts per tenant over time.
- [ ] **Bulk SMS campaigns** — Let business owners send a text to all their leads or a filtered segment ("all leads from last 30 days who haven't booked"). Requires careful Twilio compliance (opt-in, STOP handling).
- [ ] **Stripe subscription management in dashboard** — Upgrade/downgrade/cancel directly from BillingPage without leaving to Stripe portal. The portal link exists but inline management is smoother. (Carried from previous backlog.)

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
