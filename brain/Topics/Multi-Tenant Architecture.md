---
type: topic
name: "Multi-Tenant Architecture"
tags:
  - topic
  - architecture
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Multi-Tenant Architecture

## Definition (in this codebase)
AgentNexLiFy is multi-tenant from day one: every request carries a tenant/client ID, every
table has RLS, and no query is un-scoped. A planned agency hierarchy (Platform > Agency >
Business) supports white-label resale.

## Key rules
- Never write an un-scoped query. Source: [[repo-agentnexlify-claude-md]]
- [[client_id vs tenant_id]] — `leads`/`conversations` use `client_id`; other tables `tenant_id`.
- RLS on every table. Source: [[dev-knowledge-canonical-schema]]

## Related
- [[client_id vs tenant_id]] · [[AgentNexLiFy Platform]] · [[Compound Operating System]]

## Provenance
- [[repo-agentnexlify-claude-md]] · [[dev-knowledge-canonical-schema]] · [[dev-knowledge-architecture-decisions]]
