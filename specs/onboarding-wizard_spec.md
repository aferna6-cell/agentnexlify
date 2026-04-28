# Feature: Self-Serve Onboarding Wizard

**Status:** Draft
**Author:** Aidan
**Date:** 2026-03-30
**Last revised:** 2026-04-01 (migration renumber; pre-existing issue status updates)
**Target:** 1-week build, 1 engineer

---

## Problem Statement

Every new tenant is provisioned manually: Aidan creates the Supabase record, writes the knowledge base by hand, configures the widget, generates the API key, and delivers the embed snippet — a process that takes 30–60 minutes per customer and can't scale beyond a handful of accounts. There is no self-serve path, so prospects can't convert without directly involving Aidan.

The goal is to let an SMB owner (or a sales partner on a screen-share) go from zero to a working AI chat widget on their website in under 5 minutes, with no developer involvement. A free tier means prospects can try the product before buying.

---

## Goals / Non-Goals

### Goals
- A multi-step wizard that guides the user from account creation to copy-pasteable embed code
- Collect business info, services, and FAQs via plain-English fields (no markdown required)
- Auto-generate a structured knowledge base from those answers using Claude (`claude-sonnet-4-6`)
- Widget customization step (brand color, bot name, greeting, position) with live preview
- Plan selection including a free tier — paid tiers redirect to Stripe Checkout
- Display the `<script>` embed tag with a copy button and installation instructions
- Works on mobile (SMB owners will use their phone)
- Multi-tenant isolation — each request is scoped to the authenticated tenant

### Non-Goals
- No team management or multi-user access during the wizard
- No custom domains or white-labeling
- No A/B testing or analytics configuration
- No complex branching logic or conditional wizard paths
- No email verification gate before the wizard starts — the user is already registered
- No changes to the existing `SignupPage.jsx` or `auth/register` endpoint — the wizard starts *after* registration

---

## User Flow

Registration (existing `SignupPage.jsx`) happens before the wizard. After `POST /api/v1/auth/register` succeeds and the JWT is stored, the user is redirected to `/onboarding` (the new wizard page) instead of `/dashboard`.

### Step 1 — Business Info
**What the user sees:** Form fields pre-filled from signup where possible.
- Business name (pre-filled from signup)
- Industry (pre-filled from signup, dropdown with 22 options)
- City / service area (pre-filled from signup)
- Phone number (optional, pre-filled if provided at signup)
- Website URL (optional, pre-filled if provided)
- Business hours: a simple Mon–Sun toggle grid with open/close times and timezone picker

**What happens:** Stored in local wizard state; submitted in Step 5 (single backend call).

---

### Step 2 — Services & FAQs
**What the user sees:**
- "What services do you offer?" — tag-input chip component, 3–10 items, with industry-specific suggestions pre-loaded (e.g., "Oil Change", "Tire Rotation" for auto shops)
- "What questions do your customers commonly ask?" — add up to 8 Q&A pairs via a + Add Question button
- Each Q&A pair has a question input and an answer textarea

**What happens:** Stored in local wizard state.

---

### Step 3 — Generate Knowledge Base
**What the user sees:** A "Generating your AI knowledge base…" loading screen (1–3 seconds). After the API call resolves, a read-only markdown preview is shown. A small "Edit" button reveals a plain textarea for power users.

**What happens:** Frontend calls `POST /api/v1/onboarding/{tenant_id}/generate-kb` with all data collected so far. Claude turns the answers into a structured markdown knowledge base (see Claude API Integration section). The generated text is stored in `widget_configs.knowledge_base`.

**Edge case:** If the API call fails, show an error banner with a Retry button. The wizard is not blocked — the user can proceed without a KB (they can add FAQs manually later).

---

### Step 4 — Customize Widget
**What the user sees:**
- Bot name (default: "{Business Name} Assistant")
- Primary color (hex color picker, default `#00BFFF`)
- Greeting message (textarea, max 200 chars)
- Position (bottom-right / bottom-left toggle)
- **Live preview panel** on the right side (or below on mobile): an iframe that loads the actual widget pointed at the tenant's real `api_key` with a `?preview=1` query param that suppresses lead capture for preview sessions

**What happens:** Widget config fields stored in local wizard state; committed in Step 5.

---

### Step 5 — Plan Selection
**What the user sees:**
- Four plan cards: Free (always available), Starter ($99/mo), Growth ($150/mo), Pro ($250/mo)
- Each card shows the 2–3 most relevant features for that plan
- A "Continue Free" CTA is always visible so users never feel forced to pay

**What happens:**
- Free: skip Stripe entirely, call `POST /api/v1/onboarding/{tenant_id}/complete` with all wizard data, redirect to Step 6
- Paid: call `POST /api/v1/auth/billing/checkout` to get a Stripe Checkout URL, redirect there. After payment, Stripe Checkout's `success_url` = `/onboarding/step/6?session_id={CHECKOUT_SESSION_ID}`, so the wizard resumes at the embed step.

**Note:** The existing `stripe_webhooks.py` already handles `checkout.session.completed` and updates `tenants.plan` — no changes needed there.

---

### Step 6 — Embed Code
**What the user sees:**
- A success banner: "Your AI assistant is live!"
- The embed snippet in a styled code block:
  ```html
  <script src="https://cdn.agentnexlify.com/widget/v1/agentnexlify-widget.js"
          data-api-key="anx_xxxx"
          async>
  </script>
  ```
- A "Copy Code" button that copies to clipboard
- Three-step installation guide (add before `</body>`, save, refresh)
- A "Go to Dashboard" button
- A "Test Your Widget" button that opens a live preview modal

**What happens:** The `api_key` is already stored from registration. This step just reads it from the JWT or wizard state and renders the snippet.

---

## Technical Design

### New API Endpoints

#### `POST /api/v1/onboarding/{tenant_id}/generate-kb`

Accepts the user's business answers and returns a structured markdown knowledge base generated by Claude. Also persists the KB to `widget_configs.knowledge_base`.

**Auth:** Bearer JWT (owner or admin)
**Rate limit:** 5/minute per tenant

**Request:**
```json
{
  "business_name": "Acme Plumbing",
  "industry": "plumbing",
  "city": "Austin, TX",
  "phone": "512-555-0100",
  "website_url": "https://acmeplumbing.com",
  "services": ["Drain Cleaning", "Water Heater Installation", "Leak Repair"],
  "faqs": [
    { "question": "Do you offer emergency service?", "answer": "Yes, 24/7." },
    { "question": "What areas do you serve?", "answer": "Greater Austin area." }
  ],
  "hours": {
    "timezone": "America/Chicago",
    "monday": { "open": "08:00", "close": "18:00" },
    "saturday": { "open": "09:00", "close": "14:00" },
    "sunday": null
  }
}
```

**Response:**
```json
{
  "knowledge_base": "# Acme Plumbing\n\n## About\n...\n\n## Services\n...",
  "generated": true
}
```

**On Claude failure:** Returns `{ "knowledge_base": null, "generated": false }` — 200 OK, not a 5xx. The frontend shows a retry option but does not block the wizard.

---

#### `POST /api/v1/onboarding/{tenant_id}/complete` (extend existing)

The existing endpoint already handles business info, hours, website crawl, and AI content. Extend the request body to accept `widget_customization` and `faqs`:

**New fields added to `OnboardingCompleteRequest`:**
```python
widget_bot_name: str | None = None
widget_primary_color: str | None = None
widget_greeting_message: str | None = None
widget_position: str | None = None
faqs: list[dict] | None = None  # [{"question": str, "answer": str}]
```

**New behavior:** If `widget_*` fields are provided, upsert `widget_configs` with those values (using the existing `PUT /api/v1/auth/widget-config/{tenant_id}` logic, or inline). If `faqs` is provided, insert them as `faq_entries` with `category = "wizard"`.

---

#### `PUT /api/v1/auth/widget-config/{tenant_id}` (existing, no change)

Already exists. The wizard calls this directly for the customization step if the user wants to preview changes before committing.

---

### New React Pages/Components

All components go in `frontend/src/pages/` (page-level) or `frontend/src/components/` (shared sub-components). Match the existing dark theme.

#### `OnboardingWizardPage.jsx` — `/onboarding`
Top-level wizard shell. Manages:
- `step` state (1–6, persisted to `sessionStorage` so a page refresh doesn't lose progress)
- `wizardData` accumulated form state (all steps merged into one object)
- Step transition animations (simple CSS fade or slide)
- Mobile-responsive layout (single column on < 768px)
- A progress bar showing `step / 6`

After the user is redirected from Stripe (`/onboarding/step/6?session_id=...`), parse the query param and jump directly to step 6.

---

#### Step components (each a standalone component, no shared state besides `wizardData` prop + `onNext(updates)` callback)

| Component | What it renders |
|-----------|----------------|
| `WizardStepBusiness.jsx` | Business info form (name, industry, city, phone, website, hours grid) |
| `WizardStepServices.jsx` | Tag-input chips for services + Q&A pairs for FAQs |
| `WizardStepKnowledgeBase.jsx` | Loading spinner → KB markdown preview → optional edit textarea |
| `WizardStepCustomize.jsx` | Bot name, color picker, greeting, position toggle + `WidgetPreviewFrame` |
| `WizardStepPlan.jsx` | Plan card grid + "Continue Free" CTA |
| `WizardStepEmbed.jsx` | Success banner + code block + copy button + dashboard link |

---

#### `WidgetPreviewFrame.jsx`
An `<iframe>` that loads a minimal HTML shell embedding the actual widget JS with the tenant's live `api_key` and a `?preview=1` flag. The preview flag is read in `widget_chat.py` to suppress lead capture and return a canned "This is a preview" final message after a short exchange. The iframe HTML is served from a static route or constructed as a `blob:` URL to avoid CSP issues.

---

### Database Changes

#### Migration 076 — `widget_configs.knowledge_base`

Note: migrations 071–075 are taken (teaser_message, custom_instructions, email_sequences, conversations.lead_captured, teaser_enabled/teaser_delay_seconds). Next available number is 076.

```sql
ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS knowledge_base TEXT;

COMMENT ON COLUMN widget_configs.knowledge_base IS
  'AI-generated markdown knowledge base for the chat system prompt. '
  'Created during onboarding wizard; editable in widget settings.';
```

**Apply via:** `mcp__supabase__apply_migration`

**Impact on chat:** Update `widget_chat.py` `_build_system_prompt()` to include `knowledge_base` text from `widget_configs` if present. Insert it between the business description and the FAQ list. No behavior change when column is NULL.

No other schema changes are needed — all other data (services, FAQs, hours, widget colors) maps to existing columns.

---

### Claude API Integration

**Endpoint:** Called from `POST /api/v1/onboarding/{tenant_id}/generate-kb`
**Model:** `claude-sonnet-4-6` (fast, 1M context, appropriate for structured generation)
**Timeout:** 30 seconds
**Max tokens:** 1,200

**Prompt structure:**
```
You are setting up an AI chat assistant for a local business. Generate a concise,
structured knowledge base in markdown that the AI will use to answer customer questions.

Business: {business_name}
Industry: {industry}
Location: {city}
Phone: {phone}
Website: {website_url}
Services offered: {services joined by ", "}
Business hours: {hours formatted as human-readable}

The business owner provided these common customer questions and answers:
{each FAQ as "Q: ... / A: ..."}

Generate a knowledge base with these sections (use ## headers):
- About (2-3 sentences describing the business)
- Services (bullet list with brief descriptions)
- Hours & Location
- FAQs (expand the provided Q&As into polished, customer-friendly answers; add 2-3
  additional FAQs that are typical for this industry)
- Contact

Keep it concise. Do not invent facts not supported by the input. Do not add markdown
formatting beyond headers and bullet lists.
```

**Failure handling:** Catch `anthropic.APIError` and any other exception. Log the error. Return `{"generated": false, "knowledge_base": null}`. Do not raise a 5xx — the wizard continues without a KB.

**Storage:** On success, `UPDATE widget_configs SET knowledge_base = <text> WHERE tenant_id = {tenant_id}`.

**Chat integration:** In `widget_chat.py`, `_build_system_prompt()` already receives the widget config dict. Add: if `widget_config.get("knowledge_base")`, inject it into the system prompt after the business description section and before the FAQ list.

---

### Stripe Integration

The existing Stripe infrastructure is fully reusable. The wizard adds only frontend wiring.

**Free tier flow:**
1. User clicks "Continue Free" on Step 5
2. Frontend calls `POST /api/v1/onboarding/{tenant_id}/complete` (extended, JWT auth)
3. Backend upserts all wizard data, returns success
4. Frontend advances to Step 6

**Paid tier flow:**
1. User clicks a paid plan card on Step 5
2. Frontend calls `POST /api/v1/auth/billing/checkout` with `{ plan: "growth" }` (JWT auth)
3. Backend returns `{ checkout_url: "https://checkout.stripe.com/..." }`
4. Frontend redirects: `window.location.href = checkout_url`
5. Stripe Checkout `success_url` must be set to `{FRONTEND_URL}/onboarding?step=6&session_id={CHECKOUT_SESSION_ID}`
6. The existing `stripe_webhooks.py` `checkout.session.completed` handler updates `tenants.plan` — **no changes needed**
7. When the user lands back on `/onboarding?step=6`, `OnboardingWizardPage` detects `step=6` in the URL, skips straight to the embed step

**Config change needed:** Update `success_url` in `billing.py` `create_checkout`:
```python
# Before (current):
"success_url": f"{settings.frontend_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"

# After (wizard flow):
"success_url": f"{settings.frontend_url}/onboarding?step=6&session_id={{CHECKOUT_SESSION_ID}}"
```

**Existing webhook handles:** `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted` — all in `stripe_webhooks.py`. No changes.

---

## Pre-Existing Issues (Do Not Block Wizard — Fix in Parallel)

These bugs exist today and do not block the wizard from shipping, but should be tracked:

1. **`lead_captured` hardcoded `false`** — New leads from wizard-provisioned tenants will appear in the leads table but `lead_captured` will always be false. Fix: look up the actual value before updating.
2. **`conversations` FK mismatch** — The `conversations` table may fail to insert if the FK pointing to `leads` uses the wrong column name. The wizard doesn't create conversations directly, so this doesn't break onboarding, but it will affect live chat.
3. ~~**`response_metrics` UUID casting error`**~~ — **Fixed 2026-04-01** (commit `418d871`). UUID validation guard added in `_record_response_metric()` in `widget_helpers.py`.

---

## Acceptance Criteria

1. A new user can complete all 6 wizard steps and arrive at a copyable embed snippet in under 5 minutes on a mobile device.
2. After completing the wizard, `SELECT * FROM tenants WHERE id = <id>` shows `business_name`, `business_type`, `city`, and `onboarding_completed_at` populated.
3. After completing the wizard, `SELECT * FROM widget_configs WHERE tenant_id = <id>` shows `api_key` (prefixed `anx_`), `bot_name`, `primary_color`, `greeting_message`, `knowledge_base` (non-null if KB generation succeeded), and `position`.
4. The embed snippet `<script data-api-key="anx_...">` copied from Step 6 loads the chat widget correctly when pasted into a plain HTML file opened in a browser.
5. The widget preview in Step 4 shows the correct bot name, primary color, and greeting without requiring the user to leave the wizard.
6. Choosing a paid plan in Step 5 redirects to Stripe Checkout. After a test payment, the user lands on Step 6 (embed code) and `tenants.plan` is updated in the database.
7. Choosing Free in Step 5 skips Stripe and proceeds directly to Step 6 without any payment prompt.
8. If the KB generation API call fails (e.g., simulated by killing the Anthropic key), the wizard shows an error banner on Step 3 and allows the user to proceed to Step 4 without a KB. The rest of the wizard works normally.
9. Completing the wizard for Tenant A does not modify Tenant B's widget config, FAQs, or knowledge base (multi-tenant isolation).
10. A fresh page load at `/onboarding` when the user is not authenticated redirects to `/login`.
11. Refreshing the browser mid-wizard (e.g., on Step 3) resumes at the correct step without data loss (via `sessionStorage`).
12. The wizard is usable on a 375px-wide mobile screen — no horizontal scroll, no overlapping elements, tap targets ≥ 44px.

---

## Out of Scope

- Multi-user team management during the wizard
- Custom domain configuration
- Google Calendar integration during onboarding
- Automated SMS configuration during onboarding (set up manually post-wizard)
- Wizard resumability across different devices/sessions (sessionStorage only, not DB-persisted progress)
- A/B testing different wizard flows
- Editing the knowledge base from within the wizard (read-only preview; full editing in Settings post-onboarding)
- Internationalization or language selection
- White-label / reseller onboarding flows
- Analytics configuration

---

## Open Questions

1. **`success_url` change in `billing.py`** — The current `success_url` points to `/billing/success`. If we change it to `/onboarding?step=6`, existing paying subscribers (e.g., MTOptions) who upgrade via the dashboard will land on the wizard instead of the billing success page. Decision needed: either (a) add a `source=wizard` param and keep both routes, or (b) create a separate checkout endpoint used only by the wizard. **Recommendation: (a) — cheapest change, one hour of work.**

2. **Widget preview iframe CSP** — The preview iframe must load `agentnexlify-widget.js` from the CDN. If Vercel sets restrictive CSP headers, the iframe may be blocked. Verify before building the preview component. If blocked, fall back to rendering a visual mockup (static HTML, no iframe) using the wizard's color/name/greeting state.

3. **Post-Stripe redirect data loss** — When Stripe redirects back to `/onboarding?step=6`, the `sessionStorage` wizard data may have been cleared by the browser (some browsers clear sessionStorage on cross-origin navigations). Evaluate whether this matters: by Step 6 all data is persisted to the DB, so the embed code only needs the `api_key` from JWT/localStorage. Likely not an issue but confirm during implementation.

4. **Industry-specific service suggestions** — The spec calls for pre-loaded chips per industry. We need a lookup table. Start with the 5 most common industries (plumbing, HVAC, salon, dental, roofing) and populate the rest with a generic "Add your services" prompt. Can be expanded post-launch.

---

## Estimated Effort

| Area | Days | Notes |
|------|------|-------|
| Backend — `generate-kb` endpoint | 0.5 | New endpoint, extend existing onboarding router |
| Backend — extend `onboarding/complete` | 0.5 | Add widget + FAQ fields to existing endpoint |
| Backend — `success_url` change + wizard source param | 0.25 | Small change to billing.py |
| Backend — update `widget_chat.py` to use `knowledge_base` | 0.5 | Add column to system prompt builder |
| Database migration 071 | 0.25 | One ALTER TABLE |
| Frontend — `OnboardingWizardPage` shell + routing | 0.5 | Step management, sessionStorage, progress bar |
| Frontend — Steps 1–2 (business info + services) | 1.0 | Forms + tag-input chip component |
| Frontend — Step 3 (KB generation + preview) | 0.5 | Loading state + markdown display |
| Frontend — Step 4 (customize + preview frame) | 1.0 | Color picker, iframe preview |
| Frontend — Step 5 (plan selection) | 0.5 | Plan cards + Stripe redirect |
| Frontend — Step 6 (embed code) | 0.5 | Code block + copy button |
| QA + mobile testing | 0.5 | Acceptance criteria walkthrough |
| **Total** | **6.0** | Fits within 1-week target |

**Build order:** Migration → `generate-kb` endpoint → extend `onboarding/complete` → update widget_chat.py → Frontend shell + Steps 1–2 → Steps 3–6 → QA
