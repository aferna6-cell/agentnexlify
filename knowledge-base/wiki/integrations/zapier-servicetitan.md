---
title: "Send AgentNexLiFy Leads to ServiceTitan via Zapier"
category: integrations
tags: [zapier, servicetitan, crm-export, home-services, setup-guide, new-lead]
sources: ["specs/zapier-crm-export_spec.md"]
created: 2026-07-22
updated: 2026-07-22
summary: "Step-by-step tenant guide for wiring AgentNexLiFy's new-lead trigger into ServiceTitan through Zapier, so every widget-captured lead becomes a ServiceTitan lead or customer without manual re-entry."
---

# Send AgentNexLiFy Leads to ServiceTitan via Zapier

ServiceTitan is the operations backbone for larger trades shops — dispatch, CSR workflows, and job costing all run through it. This guide feeds AgentNexLiFy leads straight into ServiceTitan so the front office sees a new lead the moment the widget captures it. Best for a bigger contractor or multi-truck operation already running dispatch in ServiceTitan that wants inbound web leads in the same queue as phone calls. It uses AgentNexLiFy's tier-gated polling API (see [[zapier]]) with Zapier's ServiceTitan app.

## Setup steps

1. In AgentNexLiFy, open **Settings → Integrations → Zapier**, click **Generate API key**, name it "ServiceTitan", and copy the key — it is shown once and cannot be retrieved later.
2. In Zapier, create a Zap. For the **Trigger**, select the AgentNexLiFy "New Lead" trigger and authenticate with the API key in the `X-Api-Key` field.
3. Test the trigger and confirm the lead fields appear (`name`, `email`, `phone`, `areas_of_interest`, `status`, `created_at`).
4. For the **Action**, choose **ServiceTitan → Create Lead** (or Create Customer). Map `name`, `email`, and `phone` to the matching ServiceTitan fields, and `areas_of_interest` into the summary/notes field so the CSR sees what the customer wants.
5. Turn the Zap on. Leads are polled once a minute; ServiceTitan de-duplicates through Zapier on the lead `id`.

For rate-limit or revoked-key issues, see `docs/runbooks/zapier-failures.md`.

## Key Concepts

- **Create Lead** — the ServiceTitan action that opens a new lead the CSR team can dispatch from; the natural target for an inbound web lead.
- **CSR handoff** — mapping `areas_of_interest` into the ServiceTitan summary gives the customer-service rep the job context up front, so the follow-up call is warm.
- **Polling cadence** — one poll per minute per Zap keeps ServiceTitan current without a webhook endpoint to maintain.

## Relevance to AgentNexLiFy

ServiceTitan tenants are typically the platform's larger accounts, where a missed or slowly-entered lead has the highest dollar cost. Automating the lead into their dispatch queue makes AgentNexLiFy part of the revenue pipeline, not a side tool, which is exactly the stickiness the premium (agent_os) tier is meant to buy.

## Related Articles

- [[zapier]] — the CRM-export polling API and key model.
- [[zapier-jobber]] — the same setup for Jobber.
- [[zapier-housecall-pro]] — the same setup for Housecall Pro.
