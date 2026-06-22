---
type: topic
name: "Database Schema"
tags:
  - topic
  - schema
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Database Schema

## Summary
The [[AgentNexLiFy Platform]] Supabase database (project `pxserpybmajixqrmzaly`, org
[[VoltOps]]) has ~130 `public` tables, **RLS enabled on every table**. Grouped by domain:

## Domains (representative tables)
- **Tenancy/identity**: `tenants` (12), `clients` (2), `team_members`, `client_accounts`.
- **Conversations/leads**: `conversations` (1051), `chat_messages` (2706), `leads` (27),
  `messages`, `action_items` (15). Note [[client_id vs tenant_id]].
- **Widget/config**: `widget_configs` (10), `faq_entries` (92), `chat_flows`, `business_hours`.
- **Appointments/CRM**: `appointments` (9), `pipeline_stages` (18), `pipeline_automations`,
  `client_notes`, `invoices` (9), `bids`, `service_records`.
- **Automation**: `automations`, `automation_sequences/steps/executions/logs`,
  `automation_rules`, `email_sequences/steps/enrollments/sends`.
- **Agent OS** (`os_*`): `os_threads` (17), `os_messages` (77), `os_agent_runs` (14),
  `os_memory_entries` (14), `os_graph_nodes` (9), `os_graph_edges`, `os_routing_decision`,
  `os_model_call_log`, `os_action_runs`. Confirms Agent OS + graph memory live.
- **Billing**: `idempotency_keys` (webhook dedup, 7-day TTL), `billing_refunds`,
  `billing_dunning_events`, `tenant_cancellation_events`, `tenant_ai_usage_monthly`,
  `tenant_usage_packs`, `pricing_ab_events` (331).
- **Marketing/SEO**: `marketing_campaigns` (4), `ab_tests`, `social_posts`, `seo_audits`,
  `keyword_rankings` (mostly empty — consistent with the retired add-on).
- **KB**: `kb_articles` (16), `kb_sources` (3).

## Related
- [[Multi-Tenant Architecture]] · [[client_id vs tenant_id]] · [[AgentNexLiFy Platform]] · [[Agent OS]]

## Provenance
- [[connector-supabase-schema]]
