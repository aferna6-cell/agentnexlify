---
title: "Send AgentNexLiFy Leads to Housecall Pro via Zapier"
category: technical
tags: ["zapier", "housecall-pro", "hcp", "crm", "lead-export", "home-services", "residential", "integration", "tutorial"]
sources: ["specs/zapier-crm-export_spec.md"]
created: 2026-04-20
updated: 2026-04-20
summary: "Step-by-step guide for connecting AgentNexLiFy's Zapier trigger to Housecall Pro's Create Customer action, with field mapping optimized for residential home service tenants."
word_count: 0
relevance_score: 8
---

# Send AgentNexLiFy Leads to Housecall Pro via Zapier

Housecall Pro is a field service app targeting residential home service businesses — independent plumbers, electricians, carpet cleaners, garage door technicians, and similar trades. It occupies the mid-market between Jobber's SMB simplicity and ServiceTitan's enterprise complexity. AgentNexLiFy tenants on Growth or Professional tier can route chat widget leads directly into Housecall Pro as new customer records using the Zapier **Create Customer** action. The result is identical to Jobber from the tenant's perspective: a new widget lead produces a Housecall Pro customer record within 60 seconds, ready to receive an estimate or be booked for a job.

**Prerequisite:** AgentNexLiFy Growth or Professional plan. Housecall Pro account (any paid plan — Housecall Pro's Zapier integration is available on all paid tiers).

---

## Step 1 — Generate an API Key in AgentNexLiFy

1. Log into your AgentNexLiFy dashboard.
2. Navigate to **Settings → Integrations → Zapier**.
3. Click **Generate API Key**.
4. Label the key (e.g., "Zapier – Housecall Pro").
5. **Copy the key immediately** — shown only once.
6. Click **Done**.

> **Screenshot placeholder:** AgentNexLiFy Settings → Integrations → Zapier, showing the "Generate API Key" modal with a label field.

---

## Step 2 — Create a New Zap in Zapier

1. In Zapier, click **+ Create Zap**.
2. Search for **AgentNexLiFy** as the trigger app and select it.
3. Choose **New Lead** as the trigger event.
4. Click **Sign in to AgentNexLiFy**, paste the API key, and confirm.
5. Click **Test trigger** to pull a sample lead record.

---

## Step 3 — Review Sample Lead Fields

The trigger returns:

| Field | Example Value | What It Is |
|-------|--------------|------------|
| `name` | `Maria Gonzalez` | Full name from widget conversation |
| `email` | `maria@email.com` | Contact email |
| `phone` | `+15559871234` | Contact phone |
| `areas_of_interest` | `Carpet cleaning;Upholstery cleaning` | Services mentioned, semicolon-separated |
| `status` | `new` | Always `new` at time of capture |
| `created_at` | `2026-04-20T15:00:00Z` | Lead capture timestamp |

---

## Step 4 — Add Housecall Pro as the Action App

1. Click **+** to add an action step.
2. Search for **Housecall Pro** and select it.
3. Select the action event **Create Customer**.
4. Click **Sign in to Housecall Pro** and authorize with your Housecall Pro credentials.

> **Screenshot placeholder:** Zapier action step showing Housecall Pro selected with "Create Customer" action event and the Housecall Pro authorization screen.

---

## Step 5 — Map AgentNexLiFy Fields to Housecall Pro Customer Fields

Housecall Pro's customer record is simpler than ServiceTitan's — no hierarchy, no business unit selection:

| AgentNexLiFy Field | Housecall Pro Field | Notes |
|--------------------|--------------------|-------|
| `name` (first word) | **First Name** | Use Zapier Formatter → Split Text on space if you need separate first/last name fields. |
| `name` (remaining words) | **Last Name** | Split result. If widget captures full name as a single string, map the full `name` to Last Name and leave First Name blank — Housecall Pro displays both together. |
| `email` | **Email** | Direct mapping. |
| `phone` | **Mobile Phone** | Map to Mobile Phone (not Home Phone) — more accurate for residential leads who primarily use cell. |
| `areas_of_interest` | **Notes** | Housecall Pro's customer Notes field accepts plain text. Format: "Chat inquiry: [value]". Replace `;` with `, ` for readability. |
| *(static value)* | **Lead Source** | Set to "Website Chat" or your equivalent lead source label. Housecall Pro uses this for conversion reporting. |

> **Tip — Lead Source matters for reporting.** Housecall Pro's Revenue by Lead Source report breaks down closed jobs by how the customer was acquired. Setting Lead Source to "Website Chat" for every AgentNexLiFy lead lets you directly measure the revenue value of the widget.

---

## Step 6 — Optional: Add a Tag to New Customers

Housecall Pro supports customer tags. Adding a "AgentNexLiFy" or "Chat Lead" tag to every customer created via this Zap makes it easy to filter, bulk-email, or report on this segment later.

In the Zapier action, scroll to **Tags** and enter your desired tag name. Tags must already exist in Housecall Pro (Settings → Tags) before Zapier can apply them.

---

## Step 7 — Test and Activate

1. Click **Test action**. Zapier creates a test customer in Housecall Pro.
2. In Housecall Pro, go to **Customers** and search for the test customer by name or email.
3. Verify the record shows the correct phone, email, notes (service interest), and tag.
4. Click **Publish Zap** and toggle **On**.

> **Screenshot placeholder:** Housecall Pro Customers list showing the test customer with Notes containing the areas_of_interest value and the "Chat Lead" tag applied.

---

## Verification

Submit a real lead through your chat widget. Within 2 minutes, the customer should appear in Housecall Pro. Your techs can book a job directly from the customer record within Housecall Pro.

---

## Troubleshooting

**"Email already exists" error** — Housecall Pro rejects duplicate email addresses. Add a **Housecall Pro → Find Customer** step before Create Customer; if found, route to **Update Customer** instead of Create. This prevents double-entries for returning leads.

**Phone number rejected** — Housecall Pro requires 10-digit US numbers without country code (`5551234567`, not `+15551234567`). Add a Formatter step: Text → Replace `+1` with `` (empty string).

**Notes field missing service interest** — Check that `areas_of_interest` is mapped and not empty in the sample data. If the test lead came from a conversation where the lead didn't mention a service, the field may be an empty string. Housecall Pro handles empty Notes fine — the customer record is created regardless.

**Zap is off / paused** — Zapier pauses Zaps after 3 consecutive task errors. Check Zap history for the error details, fix the mapping issue, and re-enable the Zap.

**"Access denied — plan upgrade required" (402 from AgentNexLiFy)** — Upgrade to Growth or Professional tier in AgentNexLiFy.

---

## Key Concepts

- **Housecall Pro customer** — The core contact object. Created by this Zap and immediately available for booking in the Housecall Pro web app and mobile app. Technicians can view customer history, notes, and service address from the mobile app on-site.
- **Lead Source** — Housecall Pro's source attribution field on customer records. Setting it to "Website Chat" enables revenue attribution reporting that proves ROI on the AgentNexLiFy widget.
- **Customer tag** — A freeform label applied to customer records. Used for segmentation, bulk campaigns, and filtering. "Chat Lead" tag separates widget-originated customers from referrals or repeat customers.
- **Find or Create pattern** — Two-step Zapier flow that searches for an existing customer before creating a new one. Prevents duplicate records when the same person submits the widget form twice.

## Related Articles

- [[zapier]] — Main Zapier integration article covering API key security, tier gating, schema design, and the v1 endpoint contract.
- [[zapier-jobber]] — Jobber guide; Housecall Pro and Jobber have the most similar UX; this guide is structurally parallel.
- [[zapier-servicetitan]] — ServiceTitan guide for tenants with more complex multi-location operations.
- [[customer-gaps-by-industry]] — Residential home services pain points that Housecall Pro tenants specifically report; carpet cleaners, electricians, and garage door techs appear in this data.

## Relevance to AgentNexLiFy

Housecall Pro is the most popular CRM among AgentNexLiFy's residential trade tenants (carpet cleaners, garage door techs, independent electricians). These tenants are highly price-sensitive — they chose HCP over ServiceTitan specifically because it's simpler and cheaper. The Zapier integration must be simple to configure, which this guide supports by keeping the field mapping to four fields and the optional steps explicitly labeled. The revenue attribution story (Lead Source → Housecall Pro revenue reports) is particularly compelling for this segment because they are motivated by direct ROI visibility. Linking this guide from the dashboard's "Connect to Zapier" flow and from the integrations marketing page should drive a measurable percentage of HCP-using tenants to activate within the first 7 days of seeing the feature.
