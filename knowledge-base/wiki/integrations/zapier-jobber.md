---
title: "Send AgentNexLiFy Leads to Jobber via Zapier"
category: integrations
tags: [zapier, jobber, crm-export, home-services, setup-guide, new-lead]
sources: ["specs/zapier-crm-export_spec.md"]
created: 2026-07-22
updated: 2026-07-22
summary: "Step-by-step tenant guide for wiring AgentNexLiFy's new-lead trigger into Jobber through Zapier, so every lead the widget captures becomes a Jobber client or request without manual re-entry."
---

# Send AgentNexLiFy Leads to Jobber via Zapier

Jobber is the field-service CRM most of AgentNexLiFy's home-services tenants already run their jobs, quotes, and invoices in. This guide connects the two so every lead the widget captures lands in Jobber automatically — no copy-paste, no missed lead. Best for a contractor or trades business already quoting and scheduling in Jobber who wants inbound leads to appear where their crew already works. The connection uses AgentNexLiFy's tier-gated polling API (see [[zapier]]) on one side and Zapier's native Jobber app on the other.

## Setup steps

1. In AgentNexLiFy, open **Settings → Integrations → Zapier** and click **Generate API key**. Name it "Jobber". Copy the key immediately — it is shown only once and cannot be viewed again.
2. In Zapier, create a new Zap. For the **Trigger**, choose the AgentNexLiFy "New Lead" app/trigger (or a "polling" trigger against `GET /api/zapier/leads/new`), and paste the API key in the `X-Api-Key` field when prompted for authentication.
3. Test the trigger. Zapier fetches a recent lead and shows its fields: `name`, `email`, `phone`, `areas_of_interest` (semicolon-joined), `status`, `created_at`.
4. For the **Action**, choose **Jobber → Create Client** (or **Create Request**). Map AgentNexLiFy fields to Jobber fields: `name` → client name, `email` → email, `phone` → phone, `areas_of_interest` → the request/notes field.
5. Turn the Zap on. From now on, each new lead is polled once a minute and created in Jobber; Zapier de-duplicates on the lead `id` so no lead is created twice.

If leads stop appearing, see the failure runbook (rate-limit, revoked key) in `docs/runbooks/zapier-failures.md`.

## Key Concepts

- **New Lead trigger** — the AgentNexLiFy side of the Zap; polls `GET /api/zapier/leads/new` once a minute and hands each new lead to Zapier.
- **Create Client / Create Request** — the Jobber side; the action that turns a lead into a Jobber record. Choose Client for a contact, Request for a job inquiry.
- **Field mapping** — `areas_of_interest` arrives semicolon-joined (`"plumbing;emergency"`); map it into a Jobber notes or request-details field.

## Relevance to AgentNexLiFy

Jobber is the highest-demand CRM target in the home-services base, so a frictionless "leads into Jobber" path directly reinforces the platform's stickiness: once a tenant's leads flow into the system they already dispatch and invoice from, AgentNexLiFy is wired into their daily operation. It also anchors the premium tier, since Zapier export is agent_os-gated.

## Related Articles

- [[zapier]] — how the CRM-export polling API and API keys work under the hood.
- [[zapier-servicetitan]] — the same setup for ServiceTitan.
- [[zapier-housecall-pro]] — the same setup for Housecall Pro.
