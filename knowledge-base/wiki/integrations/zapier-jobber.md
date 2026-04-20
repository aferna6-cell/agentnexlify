---
title: "Send AgentNexLiFy Leads to Jobber via Zapier"
category: technical
tags: ["zapier", "jobber", "crm", "lead-export", "home-services", "field-service", "integration", "tutorial"]
sources: ["specs/zapier-crm-export_spec.md"]
created: 2026-04-20
updated: 2026-04-20
summary: "Step-by-step guide for connecting AgentNexLiFy's Zapier trigger to Jobber's Create Client action, mapping lead fields to client records, and handling areas_of_interest as job notes."
word_count: 0
relevance_score: 9
---

# Send AgentNexLiFy Leads to Jobber via Zapier

Jobber is field service management software used by roughly 200,000 home service businesses — plumbers, HVAC technicians, landscapers, roofers, and general contractors. Tenants on AgentNexLiFy's Growth or Professional plan can push every widget lead directly into Jobber as a new client record, eliminating manual copy-paste between the two systems. Setup takes under 10 minutes and requires no code. The result: when a homeowner submits their contact information through the chat widget, Jobber has a client record with name, phone, email, and service interest within 60 seconds.

**Prerequisite:** AgentNexLiFy Growth or Professional plan. Free-tier tenants see this feature locked in Settings; upgrade at `dashboard → Settings → Billing`.

---

## Step 1 — Generate an API Key in AgentNexLiFy

1. Log into your AgentNexLiFy dashboard.
2. Navigate to **Settings → Integrations → Zapier**.
3. Click **Generate API Key**.
4. In the modal that appears, enter a label (e.g., "Zapier – Jobber") so you can identify this key later.
5. **Copy the key immediately** — it is shown only once. Store it in a password manager or secure note.
6. Click **Done**. The key now appears in your key list with a truncated prefix (e.g., `ANX_abc1...`) and a "Never used" timestamp.

> **Screenshot placeholder:** Settings → Integrations → Zapier page showing the "Generate API Key" button and the key list with last-used timestamps.

---

## Step 2 — Create a New Zap in Zapier

1. Log into [zapier.com](https://zapier.com) and click **+ Create Zap**.
2. In the trigger search box, type **AgentNexLiFy** and select it from the results.
3. Select the trigger event **New Lead**.
4. Click **Sign in to AgentNexLiFy**.
5. In the connection dialog, paste the API key you copied in Step 1 and click **Yes, Continue**.
6. Zapier tests the connection. A green "Connection successful" message appears.

> **Screenshot placeholder:** Zapier trigger setup showing AgentNexLiFy app selected, "New Lead" trigger event, and the API key input field.

---

## Step 3 — Test the Trigger

1. Click **Test trigger**. Zapier polls the AgentNexLiFy endpoint and returns a sample lead record.
2. Review the fields returned:
   - `name` — full name from the widget conversation
   - `email` — email address
   - `phone` — phone number
   - `areas_of_interest` — service(s) the lead mentioned, semicolon-separated (e.g., `Plumbing repair;Emergency service`)
   - `status` — lead status (typically `new`)
   - `created_at` — ISO 8601 timestamp
3. If no leads appear, submit a test conversation through your widget, wait 2 minutes, and click **Test trigger** again.

---

## Step 4 — Add Jobber as the Action App

1. Click **+** to add an action step.
2. Search for **Jobber** and select it.
3. Select the action event **Create Client**.
4. Click **Sign in to Jobber** and authorize with your Jobber account credentials.

> **Screenshot placeholder:** Jobber action step showing "Create Client" selected and the Jobber OAuth authorization screen.

---

## Step 5 — Map AgentNexLiFy Fields to Jobber Client Fields

Map the trigger output fields to Jobber client fields:

| AgentNexLiFy Field | Jobber Client Field | Notes |
|--------------------|---------------------|-------|
| `name` | **First Name / Last Name** | Zapier can split on the first space: use "First Name" = first word, "Last Name" = remaining words. Or map `name` to "Company Name" for business leads. |
| `email` | **Email** | Direct 1:1 mapping. |
| `phone` | **Phone** | Direct 1:1 mapping. |
| `areas_of_interest` | **Notes** | Jobber has no service-type field at the client level. Paste service interest here so your team sees it on the client record. Prefix with "Inquiry via website chat: " for clarity. |
| `created_at` | *(not mapped)* | Jobber timestamps clients automatically on creation. |

> **Tip:** For the First/Last Name split, use Zapier's "Formatter" app with the "Text → Split Text" action between the trigger and the Jobber action. Set the separator to a space and output position 1 as First Name, position 2+ as Last Name.

---

## Step 6 — Test and Activate

1. Click **Test action**. Zapier creates a test client record in Jobber.
2. In Jobber, navigate to **Clients** and verify the test client appears with the correct name, phone, email, and notes.
3. If the test passes, click **Publish Zap** and toggle it **On**.

> **Screenshot placeholder:** Jobber Clients list showing the test client created by the Zap, with the Notes field containing the areas_of_interest value.

---

## Verification

After activation, submit a real lead through your chat widget and confirm it appears in Jobber's client list within 2 minutes. Zapier polls every 1 minute on paid plans; allow up to 2 minutes for the first live lead.

To view Zap history and debug errors: Zapier dashboard → **Zap history** → filter by your AgentNexLiFy–Jobber Zap. Each task shows the raw input fields and any error messages from Jobber's API.

---

## Troubleshooting

**"Authentication failed" in Zapier** — The API key was either miscopied or has been revoked. Return to AgentNexLiFy Settings → Integrations → Zapier, check if the key shows "Revoked", and generate a new key if needed. Update the connection in Zapier under **Connected Accounts → AgentNexLiFy**.

**"Access denied — plan upgrade required" (402 error)** — Your account is on the Free tier. Upgrade to Growth or Professional to enable Zapier.

**Leads appear in Zapier task history as "Held"** — Jobber rejected the client creation. The most common cause is a duplicate email address. In Jobber, search for the email to find the existing client. Consider adding a "Find or Create Client" step in Zapier to handle duplicates.

**`areas_of_interest` shows raw semicolons** — This is the correct format. If your Jobber notes should show bullet points, add a Zapier Formatter step between trigger and action: **Text → Replace** `;` with `\n• ` (newline + bullet).

---

## Key Concepts

- **Jobber client record** — Jobber's core contact object. Created from the Zapier integration and immediately visible under Clients in the Jobber web app and mobile app.
- **Zap task history** — Zapier's per-execution log. Every time the trigger fires, a task is created showing success or failure, the input payload, and the Jobber API response. Essential for debugging.
- **Polling interval** — Zapier checks AgentNexLiFy for new leads every 1 minute (paid Zapier plan) or 15 minutes (free Zapier plan). Lead-to-Jobber latency equals the polling interval.
- **OAuth vs API key** — Jobber uses OAuth; AgentNexLiFy uses API key. Both connections are managed in Zapier's "Connected Accounts" section and can be updated without rebuilding the Zap.

## Related Articles

- [[zapier]] — Main Zapier integration article covering API key security, tier gating, schema design, and v1 contract.
- [[zapier-servicetitan]] — Same guide for ServiceTitan, which has a more complex client/location/job hierarchy.
- [[zapier-housecall-pro]] — Same guide for Housecall Pro, which uses a "Create Customer" action similar to Jobber.
- [[customer-gaps-by-industry]] — Home-services tenant pain points that this integration directly addresses.

## Relevance to AgentNexLiFy

Jobber is the most common CRM among AgentNexLiFy's plumber, HVAC, and landscaping tenants — the three verticals with the highest PMF scores per [[customer-gaps-by-industry]]. Publishing this guide as the primary Zapier onboarding tutorial for those tenants reduces the support ticket rate for "how do I get leads into Jobber?" to near zero and accelerates time-to-value after a Growth-tier upgrade. The guide should be linked directly from the Settings → Integrations → Zapier page once that frontend page ships.
