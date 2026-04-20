---
title: "Send AgentNexLiFy Leads to ServiceTitan via Zapier"
category: technical
tags: ["zapier", "servicetitan", "crm", "lead-export", "home-services", "enterprise", "integration", "tutorial"]
sources: ["specs/zapier-crm-export_spec.md"]
created: 2026-04-20
updated: 2026-04-20
summary: "Step-by-step guide for connecting AgentNexLiFy's Zapier trigger to ServiceTitan's Create Lead action, covering the Customer/Location/Job hierarchy and field mapping for home-services enterprise tenants."
word_count: 0
relevance_score: 8
---

# Send AgentNexLiFy Leads to ServiceTitan via Zapier

ServiceTitan is the dominant field service management platform for larger home service operations — multi-tech plumbing companies, commercial HVAC, electrical contractors, and franchise groups. Its data model is more structured than Jobber's: contacts are organized as **Customer → Location → Job**, and the Zapier integration reflects this hierarchy. AgentNexLiFy's Zapier app sends the `New Lead` trigger payload into ServiceTitan's **Create Lead** action, which creates a combined Customer + booking request in ServiceTitan's Leads module — the native place dispatchers review inbound web inquiries. Growth and Professional tier tenants can activate this in under 15 minutes.

**Prerequisite:** AgentNexLiFy Growth or Professional plan. ServiceTitan account with Zapier integration enabled (requires ServiceTitan's Zapier app, available in their App Marketplace under Integrations).

---

## Step 1 — Generate an API Key in AgentNexLiFy

1. Log into your AgentNexLiFy dashboard.
2. Navigate to **Settings → Integrations → Zapier**.
3. Click **Generate API Key**.
4. Label the key (e.g., "Zapier – ServiceTitan").
5. **Copy the key immediately** — shown only once. Store it securely.
6. Click **Done**.

> **Screenshot placeholder:** AgentNexLiFy Settings → Integrations → Zapier showing the key generation modal with the label field.

---

## Step 2 — Create a New Zap in Zapier

1. In Zapier, click **+ Create Zap**.
2. Search for **AgentNexLiFy** as the trigger app.
3. Select **New Lead** as the trigger event.
4. Click **Sign in to AgentNexLiFy**, paste the API key, and confirm the connection.
5. Click **Test trigger** to pull a sample lead.

---

## Step 3 — Understand the Sample Lead Data

The trigger returns these fields from AgentNexLiFy:

| Field | Example Value | Notes |
|-------|--------------|-------|
| `name` | `John Smith` | Full name — split for ServiceTitan's First/Last fields |
| `email` | `john@example.com` | Maps to Customer email |
| `phone` | `+15551234567` | Maps to Customer phone |
| `areas_of_interest` | `HVAC repair;Emergency service` | Semicolon-joined; maps to Job Summary or Lead notes |
| `status` | `new` | Lead status — not mapped to ServiceTitan (handled internally) |
| `created_at` | `2026-04-20T14:30:00Z` | ISO 8601 — ServiceTitan accepts this format |

---

## Step 4 — Add ServiceTitan as the Action App

1. Click **+** to add an action step.
2. Search for **ServiceTitan** and select it.
3. Select the action event **Create Lead**.

   > **Note:** ServiceTitan also offers "Create Customer" and "Create Location" as separate actions. For inbound web leads, **Create Lead** is preferred — it populates ServiceTitan's Leads module (where dispatchers review pending bookings) and creates the customer record in a single step.

4. Click **Sign in to ServiceTitan** and authorize with your ServiceTitan credentials (requires Admin or Office Staff role).

> **Screenshot placeholder:** Zapier action setup showing ServiceTitan "Create Lead" action selected and the ServiceTitan OAuth authorization screen.

---

## Step 5 — Map AgentNexLiFy Fields to ServiceTitan Lead Fields

ServiceTitan's Create Lead action expects these fields:

| AgentNexLiFy Field | ServiceTitan Field | Notes |
|--------------------|--------------------|-------|
| `name` (first word) | **Customer First Name** | Use Zapier Formatter → Split Text on space, position 1. |
| `name` (remaining) | **Customer Last Name** | Zapier Formatter → Split Text, position 2+. If single-name lead, map full `name` to Last Name and leave First Name blank. |
| `phone` | **Customer Phone** | Direct mapping. ServiceTitan normalizes to E.164. |
| `email` | **Customer Email** | Direct mapping. |
| `areas_of_interest` | **Summary** | The job summary field. Replace `;` with ` / ` for readability. Prefix: "Website chat inquiry: ". |
| *(static value)* | **Campaign** | Enter your web/chat campaign name in ServiceTitan (e.g., "Website Chat"). Helps track lead source attribution. |
| *(static value)* | **Business Unit** | Select your default business unit if you have multiple. |

> **Tip — Formatter step for name split:** Between the AgentNexLiFy trigger and the ServiceTitan action, add a **Formatter by Zapier** step:
> - Action: Text → Split Text
> - Input: the `name` field
> - Separator: space (` `)
> - Segment Index: "First" for First Name, "Last" for Last Name (Zapier handles the multi-word case)

> **Tip — areas_of_interest cleanup:** Add a second **Formatter** step:
> - Action: Text → Replace
> - Find: `;`
> - Replace: ` / `
> - Input: `areas_of_interest`

---

## Step 6 — Set Lead Priority and Status (Optional)

ServiceTitan's Create Lead action supports additional optional fields:

- **Priority** — Set to "High" for emergency or urgent service keywords in `areas_of_interest`. This can be automated with a Zapier Filter or conditional logic.
- **Booking Type** — Select the default service type for web leads (e.g., "Service Call"). Consult your ServiceTitan configuration for valid values.
- **Note** — Add the full `areas_of_interest` value here as a secondary field so the dispatcher sees the raw text alongside the formatted Summary.

---

## Step 7 — Test and Activate

1. Click **Test action**. Zapier creates a test Lead in ServiceTitan.
2. In ServiceTitan, navigate to **Leads** (or **Dispatch → Leads** depending on your version).
3. Verify the lead appears with the correct customer name, phone, email, and summary.
4. Check that the lead is assigned to the correct Business Unit and Campaign.
5. If the test passes, click **Publish Zap** and toggle **On**.

> **Screenshot placeholder:** ServiceTitan Leads module showing a test lead created from the AgentNexLiFy chat widget, with customer details and summary populated.

---

## Verification

After activation, submit a test lead through the chat widget and confirm it appears in ServiceTitan's Leads module within 2 minutes. Dispatchers should see the lead in their queue with the campaign attribution set to "Website Chat".

---

## Troubleshooting

**"Invalid Business Unit" error** — ServiceTitan requires a valid Business Unit ID. In ServiceTitan, go to Settings → Business Units to find your unit's internal ID. Use the exact ID (numeric) in the Zapier field, not the display name.

**Lead appears without customer phone number** — Phone numbers in E.164 format (`+1...`) are required by ServiceTitan. If the widget captures a 10-digit US number (`5551234567`), add a Formatter step to prepend `+1`: Text → Replace `^` (regex) with `+1`. Enable regex matching.

**Duplicate customer created** — ServiceTitan creates a new customer for every Create Lead call, even if the email matches an existing customer. To prevent duplicates, add a **ServiceTitan → Find Customer** step before Create Lead; if found, use "Update Customer" + "Create Job" instead. This requires a more complex multi-step Zap.

**"Unauthorized" (401) from AgentNexLiFy** — API key revoked or entered incorrectly. Regenerate in AgentNexLiFy Settings → Integrations → Zapier and update the connection in Zapier → Connected Accounts → AgentNexLiFy.

**"Access denied — plan upgrade required" (402)** — Upgrade to Growth or Professional tier.

---

## Key Concepts

- **ServiceTitan Lead** — A combined contact + job request record that lives in ServiceTitan's Leads module pending dispatcher review and booking. Distinct from a "Job" (already booked) or a "Customer" (already in the system).
- **Customer/Location/Job hierarchy** — ServiceTitan's three-level data model. The Create Lead action creates a Customer and a pending Lead in one step; a Location and Job are created when the dispatcher books the call.
- **Business Unit** — ServiceTitan's internal organizational unit (e.g., HVAC division, Plumbing division). Required for proper lead routing and reporting. Hardcode the correct Business Unit ID in the Zap.
- **Campaign attribution** — ServiceTitan's source tracking field for leads. Setting it to a consistent value (e.g., "Website Chat") enables revenue attribution reporting later.

## Related Articles

- [[zapier]] — Main Zapier integration article covering API key security, tier gating, schema design, and v1 contract.
- [[zapier-jobber]] — Simpler single-tier CRM guide; good comparison point for the added complexity of ServiceTitan's hierarchy.
- [[zapier-housecall-pro]] — Housecall Pro guide; similar complexity level to Jobber but targets the same enterprise-adjacent mid-market ServiceTitan serves.
- [[customer-gaps-by-industry]] — Home-services industry pain points that ServiceTitan tenants specifically report.

## Relevance to AgentNexLiFy

ServiceTitan tenants are typically larger operations — multi-location plumbing companies, franchise HVAC groups — with more to lose from manual lead handling and more to gain from automation. They are also the most likely to be on Professional tier ($499/mo). A clean ServiceTitan integration is a retention and upsell argument: tenants who connect their CRM have higher engagement scores and lower churn per the benchmarks in [[saas-churn-benchmarks-2026]]. The added complexity of ServiceTitan's field hierarchy (versus Jobber or HCP) is the main support risk; this guide should be surfaced as in-app help on the Settings → Integrations page when the tenant's CRM is detected as ServiceTitan.
