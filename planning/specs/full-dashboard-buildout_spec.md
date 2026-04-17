# Full Dashboard Buildout — Feature Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit, fix, and complete all AgentNexLiFy tenant dashboard pages so every sidebar item is functional, connected to live data, and revenue-ready.

**Architecture:** Multi-tenant FastAPI backend on Railway + React/Vite dashboard on Vercel + Supabase (PostgreSQL). Every query is scoped by `tenant_id` or `client_id`. All pages follow the existing dark-theme dashboard pattern.

**Tech Stack:** FastAPI (Python 3.11), React/Vite, Tailwind-style CSS, Recharts, Supabase, Anthropic Claude API (claude-sonnet-4-6), Stripe, Resend, Twilio.

**Written:** 2026-03-31 | **Author:** Claude Code (counseling Aidan's spec prompt)

---

## Reality Check — Current Codebase State

Before diving into phases, here is what the codebase audit found. Many pages from the original spec **already exist** as React components and FastAPI routers. The phases below are organized around what actually needs work, not what was aspirationally described.

| Item | Frontend Page | Backend Router | Status |
|---|---|---|---|
| Dashboard | `Dashboard/index.jsx` | – | ✅ Working |
| Conversations | `ConversationsPage.jsx` | `conversation_inbox.py` | ✅ Working |
| Analytics | `AnalyticsPage.jsx` | `analytics.py` | ✅ Exists, needs audit |
| Clients/Leads | `LeadsPage.jsx` | `leads.py`, `clients.py` | ✅ Exists, needs audit |
| Pipeline | `PipelinePage.jsx` | `pipeline.py` | ✅ Exists, needs audit |
| Smart Lists | `SmartListsPage.jsx` | `smart_lists.py` | ✅ Exists, needs audit |
| Client Portal | `ClientPortalPage.jsx` | `client_portal.py` | ✅ Exists, needs audit |
| Calls | `CallsPage.jsx` | `calls.py` | ✅ Exists, needs audit |
| Chat Flows | `ChatFlowBuilderPage.jsx` | `chat_flows.py` | ✅ Exists, needs audit |
| Widget Config | `WidgetPage.jsx` | `widget_config.py` | ✅ Exists, needs audit |
| Snippets | `SnippetsPage.jsx` | `snippets.py` | ✅ Exists |
| FAQ Manager | `FaqManagerPage.jsx` | – | ✅ Exists |
| Campaigns | `MarketingCampaignsPage.jsx` | `marketing_campaigns.py` | ✅ Exists, needs audit |
| Sequences | `Automations/index.jsx` | `sequences.py`, `automations.py` | ✅ Exists, needs audit |
| Appointments | `Calendar.jsx` | `appointments.py` | ✅ Exists, needs audit |
| Invoices | `InvoicesPage.jsx` | `invoices.py` | ✅ Exists, needs audit |
| Reviews | `ReviewsPage.jsx` | `reviews.py` | ✅ Exists, needs audit |
| SEO | `LocalSEOPage.jsx` | `local_seo.py` | ✅ Exists, needs audit |
| Team | `TeamPage.jsx` | `team.py` | ✅ Exists |
| Billing | `BillingPage.jsx` | `billing.py` | ✅ Exists |
| Business Page | `BusinessPageSettings.jsx` | `business_page.py` | ✅ Exists |
| Integrations | `IntegrationsPage.jsx` | `integrations.py` | ✅ Exists |
| MCP Setup | `MCPSetupPage.jsx` | – | ✅ Exists |
| Settings | `SettingsPage.jsx` | – | ✅ Exists |

**Conclusion:** The platform is architecturally complete. The work is: (1) fix genuine bugs blocking data flow, (2) audit each page for broken queries/empty states/missing features, (3) fill specific feature gaps identified per-page below.

---

## Phase A: Critical Fixes

These must ship before anything else — they are the data backbone that all other pages depend on.

### A1: Lead Capture Verification & `lead_captured` Signal

**Problem:**
- `lead_captured` is hardcoded to `False` in every `WidgetChatResponse` (see `backend/routers/widget_chat.py` line ~516, comment: "Actual capture runs in background task").
- The background task `_capture_leads_from_session` DOES run and DOES create leads — but the API response always returns `False`, so any downstream logic (email notifications, widget UX triggers, webhook events) that reads `lead_captured` never fires.
- The live MTOptions tenant has 88 widget conversations and 0 leads in the dashboard. Root cause: visitors may not have shared contact info, OR the background task is silently failing (Supabase insert errors swallowed). Need visibility.

**Solution (backend):**
1. Add a `lead_detected` flag to `_capture_leads_from_session` — scan the CURRENT message (not just history) synchronously before returning the response, using the existing `EMAIL_RE` and `PHONE_RE` patterns in `widget_helpers.py`.
2. Return `lead_captured=True` if an email or phone is detected in the inbound message OR was detected in any prior message in the session.
3. Add Supabase logging: on background task lead creation failure, write to an `error_log` table (or use Supabase's own logging). Never silently swallow.

**Solution (monitoring):**
1. Add a `/api/v1/leads/debug/{tenant_id}` endpoint (auth-gated) that returns: total leads, leads created in last 7 days, last lead creation timestamp. Used by the dashboard to show "Lead capture: active/inactive" indicator.

**Files to change:**
- `backend/routers/widget_helpers.py` — add synchronous contact detection before background task
- `backend/routers/widget_chat.py` — pass detection result to `WidgetChatResponse(lead_captured=...)`
- `backend/models/schemas.py` — verify `WidgetChatResponse.lead_captured` field exists

**Database changes:** None required.

**API changes:**
- `POST /api/v1/widget/chat` response: `lead_captured` field becomes dynamic (true when email/phone detected)

**Acceptance criteria:**
- [ ] When a widget visitor types their email in any message, the API response returns `lead_captured: true`
- [ ] A lead record is created in Supabase `leads` table with `client_id = tenant_id`
- [ ] The Leads page shows the new lead within 30 seconds
- [ ] If no contact info shared, `lead_captured: false` — no lead created

---

### A2: Analytics Data Accuracy Audit

**Problem:**
- The original spec described a FK mismatch between `conversations.client_id` → `clients` table. **This has since been fixed** — `analytics.py` now counts unique `session_id`s from `chat_messages` directly, bypassing the conversations FK.
- HOWEVER: The dashboard's "Overview" cards still show 0 for all metrics for the MTOptions tenant. The issue is likely the `tenant_id` used in the JWT vs the actual `id` in the `tenants` table — needs verification.

**Solution:**
1. Add a test endpoint: `GET /api/v1/analytics/{tenant_id}/health` — returns the raw counts for conversations, leads, and appointments for that tenant. Used to quickly diagnose which table has data and which is empty.
2. Audit the `OverviewCards.jsx` — verify it is calling `fetchAnalyticsOverview` with the correct `tenant_id` from the JWT.
3. Verify the `period` default (30d) includes the 88 existing conversations (check `created_at` timestamps).

**Files to change:**
- `backend/routers/analytics.py` — add `/health` debug endpoint
- `frontend/src/pages/Dashboard/OverviewCards.jsx` — audit tenant_id usage

**Acceptance criteria:**
- [ ] Dashboard overview cards show non-zero conversation count for MTOptions
- [ ] Analytics page charts render with real data

---

### A3: Widget Markdown Rendering (Already Fixed)

**Status: RESOLVED.** The widget already implements `_renderMd()` and `_inlineMd()` in `widget/agentnexlify-widget.js` (lines 931–973). Bold, italic, links, and lists render correctly. Assistant messages use `div.innerHTML = _renderMd(text)`.

**Action:** No code changes needed. Verify via manual test with a response containing `**bold**` text.

**Acceptance criteria:**
- [ ] Test widget response containing `**$139.95/month**` — renders as bold, not raw asterisks
- [ ] No XSS vector: HTML entities are escaped before inline formatting is applied

---

## Phase B: Core CRM + Communications Audit

### New Database Tables for Phase B

No new tables required — all CRM tables already exist (see schema in CLAUDE.md). Phase B is about ensuring existing tables are queried correctly and pages are functional.

---

### B1: Analytics Page (`/analytics`)

**Route:** `/analytics` → `AnalyticsPage.jsx`
**Backend:** `GET /api/v1/analytics/{tenant_id}/overview|conversations|leads|response-times|widget`

**Current state:** Page exists with charts (LineChart, AreaChart, BarChart via Recharts). Calls multiple analytics API endpoints.

**Gaps to fix:**
- **Top Questions Asked:** Currently no endpoint aggregates message content to extract common questions. Add a `GET /api/v1/analytics/{tenant_id}/top-questions` endpoint that uses `chat_messages` to extract and count user questions (simple word-frequency approach or AI-assisted clustering via Claude API).
- **Lead Conversion Funnel:** The funnel chart needs `total_visitors` (unique sessions in `chat_messages`) → `leads` (count in leads table) to compute a real funnel. Verify these numbers connect.
- **Peak Hours Heatmap:** Already exists in analytics.py. Verify it renders in the UI.
- **Export to CSV:** Add a "Download CSV" button that calls `GET /api/v1/analytics/{tenant_id}/export?period=30d` and streams a CSV of conversation/lead/appointment data.

**API endpoints to add:**
```
GET /api/v1/analytics/{tenant_id}/top-questions?period=30d
  → { questions: [{ text: str, count: int }] }

GET /api/v1/analytics/{tenant_id}/export?period=30d
  → CSV stream (Content-Disposition: attachment)
```

**Acceptance criteria:**
- [ ] All 4 stat cards show non-zero values for MTOptions
- [ ] Conversations-over-time chart renders a line with data points
- [ ] Lead funnel chart shows visitors → conversations → leads with %
- [ ] Export downloads a CSV with real rows

---

### B2: Clients / Leads Page (`/leads`)

**Route:** `/leads` → `LeadsPage.jsx`
**Backend:** `GET/POST/PATCH/DELETE /api/v1/leads/{tenant_id}/...`

**Current state:** Full table with sorting, filtering, search, lead detail drawer, bulk actions, CSV export/import, duplicate detection, merge. Looks complete.

**Gaps to fix:**
- **"Add Lead" manual form:** Verify the create-lead modal works (fields: name, email, phone, source, status).
- **Lead Detail Drawer:** Verify it loads conversation history, notes, pipeline stage, tags from `LeadDetailDrawer.jsx`.
- **Lead score display:** Verify `lead_score` and `lead_temperature` are populated (depends on A1 working).

**Acceptance criteria:**
- [ ] Table loads and shows all existing leads for the tenant
- [ ] Clicking a lead opens the detail drawer with full info
- [ ] "Add Lead" modal creates a lead visible in the table
- [ ] CSV export downloads a file with all lead columns

---

### B3: Pipeline Page (`/pipeline`)

**Route:** `/pipeline` → `PipelinePage.jsx`
**Backend:** `GET /api/v1/pipeline/{tenant_id}/board`, `PATCH /api/v1/pipeline/{tenant_id}/leads/{lead_id}/stage`

**Current state:** Kanban board with drag-free card moving (button-based move menu), temperature indicators, deal value display. Fallback stages defined if DB stages are empty.

**Gaps to fix:**
- **Stage totals:** Verify each column header shows the count and total deal value.
- **Drag-and-drop (stretch):** The current implementation uses a move-menu button. True drag-and-drop requires adding `@dnd-kit/core` or similar. Leave as button-based for V1.
- **Empty state:** If no leads in pipeline, show a helpful CTA ("Leads captured from your widget will appear here. Share your embed code to start capturing leads.")

**Acceptance criteria:**
- [ ] Pipeline loads with MTOptions data (or empty state CTA)
- [ ] Moving a lead between stages persists to DB and reflects immediately
- [ ] Stage headers show correct counts

---

### B4: Widget Config Page (`/widget`)

**Route:** `/widget` → `WidgetPage.jsx`
**Backend:** `GET/PATCH /api/v1/widget-config/{tenant_id}`

**Current state:** Page exists with color pickers, position selector, bot name, greeting message, embed code.

**Gaps to fix — TEASER BUBBLE:**
- The widget JS already has a `#anx-teaser` element (line 714 in widget JS). But the WidgetPage may not expose the teaser bubble message as a configurable field.
- Add `teaser_message` field to `widget_configs` table and `WidgetPage.jsx` form.
- Pass `teaser_message` in widget config API response so the widget JS can show it.

**Migration required:**
```sql
-- migrations/071_widget_teaser_message.sql
ALTER TABLE widget_configs ADD COLUMN IF NOT EXISTS teaser_message TEXT;
```

**Widget JS change:**
In `widget/agentnexlify-widget.js`, populate `#anx-teaser-text` with the `teaser_message` from config (already fetched via `/api/v1/widget/config`).

**Files to change:**
- `migrations/071_widget_teaser_message.sql` (new)
- `backend/routers/widget_config.py` — include `teaser_message` in GET/PATCH
- `frontend/src/pages/WidgetPage.jsx` — add Teaser Bubble section with input field
- `widget/agentnexlify-widget.js` — set `#anx-teaser-text` from config.teaser_message
- `frontend/public/widget/agentnexlify-widget.js` — keep in sync with widget/

**Acceptance criteria:**
- [ ] Widget config page has "Teaser Message" input field with live preview
- [ ] Saving teaser message persists to DB
- [ ] Widget JS shows teaser bubble with the configured message when widget is closed
- [ ] Teaser can be dismissed (X button already exists in widget JS)

---

### B5: FAQ Manager (`/faq`)

**Route:** `/faq` → `FaqManagerPage.jsx`
**Current state:** Likely a full CRUD interface for `faq_entries` table.

**Gaps to fix:**
- **"Test This FAQ" button:** Send the question to `POST /api/v1/widget/chat` with the tenant's API key and display the AI response inline. Verifies the FAQ is actually influencing AI output.
- **Bulk import from CSV:** Add a CSV upload button (columns: question, answer, category).

**Acceptance criteria:**
- [ ] Add/edit/delete FAQ entries
- [ ] Test button sends question to AI and shows response
- [ ] CSV import creates multiple FAQ entries in one operation

---

### B6: Snippets (`/snippets`)

**Route:** `/snippets` → `SnippetsPage.jsx`
**Current state:** CRUD for `snippets` table. Shortcuts usable in Conversations reply box.

**Acceptance criteria:**
- [ ] Create/edit/delete snippets with title, shortcut, body text
- [ ] Snippet shortcut (e.g. `/pricing`) works in Conversations reply box
- [ ] Page shows usage count per snippet

---

## Phase C: Marketing + Automations

### C1: Campaigns (`/campaigns`)

**Route:** `/campaigns` → `MarketingCampaignsPage.jsx`
**Backend:** `marketing_campaigns.py`

**Current state:** Page exists. Connects to `marketing_campaigns` and `campaign_sends` tables.

**Gaps to fix:**
- **Email editor:** Verify rich text / template body editor works and renders HTML in Resend.
- **SMS character counter:** 160-char limit indicator on SMS body field.
- **Audience selector:** "Send to Smart List" option — connect to `smart_lists` table.
- **Campaign stats:** Open rate, click rate should read from `campaign_sends` + `email_events` tables.

**New API endpoint:**
```
GET /api/v1/marketing-campaigns/{tenant_id}/{campaign_id}/stats
  → { sent: int, opened: int, clicked: int, open_rate: float, click_rate: float }
```

**Acceptance criteria:**
- [ ] Create email campaign with subject, body, audience, schedule
- [ ] Send immediately option fires Resend API for email campaigns
- [ ] Campaign history table shows open/click rates

---

### C2: Email Sequences (`/sequences` or `/automations`)

**Route:** `/automations` → `Automations/index.jsx`
**Backend:** `sequences.py`, `automations.py`

**Current state:** Dashboard has "Create Default Sequences" button. Automations section exists.

**Gaps to fix:**
- **Sequence builder UI:** The `Automations/SequenceBuilder.jsx` may be partially implemented. Verify it can create: trigger, email steps with delays.
- **Enrollment:** Auto-enroll new leads whose status matches trigger criteria.
- **Performance stats:** Per-step open rate from `email_events` table.

**Acceptance criteria:**
- [ ] Create a sequence with trigger (new_lead), email step, delay, second email
- [ ] New lead created from widget triggers sequence enrollment automatically
- [ ] Sequence detail shows step-by-step open/reply rates

---

### C3: Chat Flows (`/chat-flows`)

**Route:** `/chat-flows` → `ChatFlowBuilderPage.jsx`
**Backend:** `chat_flows.py` → `chat_flows` table (stores `flow_json` JSONB)

**Current state:** Visual builder page exists.

**V1 approach (text-based, no drag-and-drop):** A list of if/then rules:
- Trigger: keyword match in visitor message (e.g. "pricing", "appointment")
- Action: inject a specific response OR capture lead OR route to booking

**Gaps to fix:**
- Verify `flow_json` schema is well-defined and the widget reads active flows.
- In `widget_helpers.py`, `_build_flow_instructions()` already imports chat flows — verify it's injecting flow rules into the system prompt.

**Acceptance criteria:**
- [ ] Create a flow rule: "If visitor asks about pricing, respond with pricing card"
- [ ] Flow is active in the widget — AI follows the rule
- [ ] Multiple flows can be created per tenant, only active ones apply

---

## Phase D: Operations + Polish

### D1: Appointments / Calendar (`/calendar`)

**Route:** `/calendar` → `Calendar.jsx`, `/availability` → `Availability.jsx`
**Backend:** `appointments.py`, `widget_booking.py`, `booking_page.py`

**Current state:** Calendar view exists. Booking via widget exists (see `_process_bid_request_from_chat`).

**Gaps to fix:**
- **Google Calendar sync:** `integrations.py` handles OAuth tokens. Verify Google Calendar event creation runs on appointment creation.
- **Automated reminders:** No reminder logic exists. Add a cron job (or Railway scheduled task) that fires `send_email` (via Resend) and `sms` (via Twilio) 24h before appointment.
- **Booking link:** A public URL like `agentnexlify.com/book/{business_slug}` that shows available slots and lets visitors self-schedule.

**New API endpoint:**
```
POST /api/v1/appointments/{tenant_id}/reminders/trigger
  → triggers email+SMS reminder for all appointments in next 24h
```

**Acceptance criteria:**
- [ ] Calendar shows all appointments by day/week/month
- [ ] Create appointment from dashboard — shows in Google Calendar (if connected)
- [ ] Appointment reminder fires via email+SMS 24h before

---

### D2: Invoices (`/invoices`)

**Route:** `/invoices` → `InvoicesPage.jsx`
**Backend:** `invoices.py` → `invoices` table

**Current state:** Page exists. Includes bid/estimate flow (BidsPage.jsx).

**Gaps to fix:**
- **Send invoice via email:** Add "Send to Client" button — generates a payment link (Stripe PaymentIntent) and emails it via Resend.
- **Overdue detection:** Mark invoices as overdue when `due_date` passes and status is still `pending`.
- **Text-to-pay:** SMS the payment link to the client's phone.

**Acceptance criteria:**
- [ ] Invoice list shows all invoices with status (paid/pending/overdue)
- [ ] "Send Invoice" button emails the client a payment link
- [ ] Overdue invoices highlighted in red

---

### D3: Reviews (`/reviews`)

**Route:** `/reviews` → `ReviewsPage.jsx`
**Backend:** `reviews.py` → `reviews` table

**Current state:** Review management page exists. AI draft response feature likely present.

**Gaps to fix:**
- **Review request automation:** After appointment marked as "completed", auto-send SMS/email asking for a Google review (using the tenant's `google_review_link`).
- **Review response:** "Post Response" button should write response to `reviews.owner_response` and mark `responded=true`.

**New API endpoint:**
```
POST /api/v1/reviews/{tenant_id}/request
  body: { lead_id: str, channel: "sms" | "email" }
  → sends review request message to client
```

**Acceptance criteria:**
- [ ] Review list shows ratings, text, platform for all imported reviews
- [ ] AI-drafted response appears; tenant can edit and post
- [ ] Review request button sends SMS to client with Google review link

---

### D4: Local SEO (`/local-seo` or `/seo`)

**Route:** `/local-seo` → `LocalSEOPage.jsx`
**Backend:** `local_seo.py` → `seo_audits`, `geo_scores`, `keyword_rankings` tables

**Current state:** Full SEO audit page with scores, categories, issues.

**Keep V1 scope:** Don't add live crawling. Focus on:
- [ ] SEO audit scores display correctly
- [ ] Keyword ranking table shows with recommendations
- [ ] GEO score card shows AI visibility score

---

### D5: Documents (`/documents`)

**Route:** `/documents` → `DocumentsPage.jsx`
**Backend:** `documents.py` → `documents`, `document_templates` tables

**Current state:** Page exists. E-signature flow with `signing_token` and `portal_tokens`.

**Acceptance criteria:**
- [ ] Create document from template, assign to lead
- [ ] Send signing link to lead via email
- [ ] Document shows as "Signed" in list after completion

---

### D6: Remaining Settings Pages

These pages exist and are largely functional. Acceptance criteria is "loads without error and saves changes":

- [ ] **Team** (`/team`) — add/remove team members, set roles
- [ ] **Billing** (`/billing`) — shows plan, upgrade/downgrade via Stripe
- [ ] **Business Page** (`/business-page`) — edit public business landing page
- [ ] **Integrations** (`/integrations`) — connect Google Calendar, Twilio, Stripe
- [ ] **Settings** (`/settings`) — business name, timezone, notifications toggle

---

## Migration Plan

New migrations needed (use next number after 070):

```sql
-- migrations/071_widget_teaser_message.sql
ALTER TABLE widget_configs ADD COLUMN IF NOT EXISTS teaser_message TEXT;
COMMENT ON COLUMN widget_configs.teaser_message IS 'Text shown in teaser bubble when widget is minimized';
```

That's the only new migration needed. Everything else uses existing tables.

Apply via Supabase MCP:
```
mcp__supabase__apply_migration({ name: "071_widget_teaser_message", query: "..." })
```

Update `docs/dev-knowledge/schema-log.md` after applying.

---

## Dependency Graph

```
A1 (lead capture fix)
  └─→ B2 (Leads page shows real data)
  └─→ B3 (Pipeline has cards to move)
  └─→ C2 (Sequences can enroll new leads)
  └─→ D1 (Appointments linked to leads)
  └─→ D2 (Invoices linked to leads)
  └─→ D3 (Reviews linked to leads)

A2 (analytics accuracy)
  └─→ B1 (Analytics page shows real charts)
  └─→ Dashboard overview cards show non-zero values

B4 (teaser bubble)
  └─→ Depends only on widget_configs migration (071)
  └─→ Independent of all other phases

B1 (analytics page)
  └─→ Depends on A1 (need real leads for funnel chart)
  └─→ Depends on A2 (need accurate conversation counts)
```

---

## Implementation Order (Recommended)

1. **A1** — Lead capture audit + `lead_captured` fix (1-2 hours)
2. **A2** — Analytics accuracy verification (1 hour)
3. **B4** — Teaser bubble (2 hours, high user-facing value)
4. **B1** — Analytics page enhancements (half day)
5. **B2/B3** — Leads + Pipeline audit (half day)
6. **C1** — Campaigns send functionality (1 day)
7. **D1** — Appointment reminders cron (half day)
8. **D2** — Invoice send-via-email (half day)
9. **D3** — Review request automation (half day)
10. **C2** — Sequence enrollment trigger (1 day)

Total estimated scope: ~1 week of focused engineering.

---

## Key Conventions

- All new Python files: **NEVER** use `from __future__ import annotations`
- All DB queries: filter by `tenant_id` (or `client_id` for `leads` and `conversations`)
- All new API routes: use `Depends(_get_current_tenant)` + `verify_tenant(claims, tenant_id)`
- Widget JS changes: keep `widget/agentnexlify-widget.js` and `frontend/public/widget/agentnexlify-widget.js` identical
- After any migration: apply via Supabase MCP and update `docs/dev-knowledge/schema-log.md`
- Model IDs: `claude-sonnet-4-6` (chat), `claude-opus-4-7` (documents/analysis)
