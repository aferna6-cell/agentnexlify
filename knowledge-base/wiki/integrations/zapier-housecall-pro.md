---
title: "Send AgentNexLiFy Leads to Housecall Pro via Zapier"
category: integrations
tags: [zapier, housecall-pro, crm-export, home-services, setup-guide, new-lead]
sources: ["specs/zapier-crm-export_spec.md"]
created: 2026-07-22
updated: 2026-07-22
summary: "Step-by-step tenant guide for wiring AgentNexLiFy's new-lead trigger into Housecall Pro through Zapier, so every widget-captured lead becomes a Housecall Pro customer or lead without manual re-entry."
---

# Send AgentNexLiFy Leads to Housecall Pro via Zapier

Housecall Pro is the CRM of choice for solo operators and small crews who want scheduling, invoicing, and payments in one lightweight app. This guide connects AgentNexLiFy so a new widget lead becomes a Housecall Pro customer automatically — ideal for an owner-operator who cannot afford to let a lead sit while they are on a job. Best for a one-to-few-truck business already running Housecall Pro that wants inbound leads captured hands-free. It uses AgentNexLiFy's tier-gated polling API (see [[zapier]]) with Zapier's Housecall Pro app.

## Setup steps

1. In AgentNexLiFy, open **Settings → Integrations → Zapier**, click **Generate API key**, name it "Housecall Pro", and copy it immediately — the key is shown once and is not retrievable afterward.
2. In Zapier, create a Zap. For the **Trigger**, pick the AgentNexLiFy "New Lead" trigger and paste the API key into the `X-Api-Key` authentication field.
3. Test the trigger; confirm the lead fields load (`name`, `email`, `phone`, `areas_of_interest`, `status`, `created_at`).
4. For the **Action**, choose **Housecall Pro → Create Customer** (or Create Lead). Map `name`, `email`, and `phone` to the customer fields and `areas_of_interest` into the notes so the job type is captured.
5. Turn the Zap on. Leads poll once a minute and de-duplicate through Zapier on the lead `id`, so a lead is never entered twice.

If leads stop flowing, check the failure runbook at `docs/runbooks/zapier-failures.md` (rate-limit trip or revoked key).

## Key Concepts

- **Create Customer** — the Housecall Pro action that adds the lead as a customer record ready to schedule; the simplest target for a solo operator.
- **Hands-free capture** — polling means the owner does nothing after setup; a lead captured while they are on a job is in Housecall Pro before they get back to the truck.
- **Notes mapping** — routing `areas_of_interest` into the customer notes preserves what the customer asked for without a nested field mapping.

## Relevance to AgentNexLiFy

Housecall Pro tenants are the platform's smallest, most time-poor operators, exactly the segment for whom "the lead is already in my CRM" is the difference between winning and losing the job. A frictionless Housecall Pro path makes AgentNexLiFy indispensable to the owner-operator base and reinforces the premium tier that gates Zapier export.

## Related Articles

- [[zapier]] — how the CRM-export polling API and API keys work.
- [[zapier-jobber]] — the same setup for Jobber.
- [[zapier-servicetitan]] — the same setup for ServiceTitan.
