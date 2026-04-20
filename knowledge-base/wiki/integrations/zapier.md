---
title: "Zapier Integration — AgentNexLiFy Lead Export for SMB CRMs"
category: technical
tags: ["zapier", "crm", "api-key", "lead-export", "integration", "jobber", "servicetitan", "housecall-pro", "home-services"]
sources: ["specs/zapier-crm-export_spec.md"]
created: 2026-04-20
updated: 2026-04-20
summary: "AgentNexLiFy's Zapier app exposes a polling `new_lead` trigger on a versioned endpoint, letting Growth+ tenants push widget leads to 7,000+ CRMs including Jobber, ServiceTitan, and Housecall Pro without custom webhook code."
word_count: 0
relevance_score: 9
---

# Zapier Integration — AgentNexLiFy Lead Export for SMB CRMs

AgentNexLiFy's Zapier app closes the "lead capture to CRM" gap that costs home-service tenants hours of manual data entry every week. Tenants on Growth or Professional tiers generate an API key from Settings → Integrations → Zapier, connect it in Zapier's app wizard, select the `New Lead` trigger, map fields to their CRM's contact schema, and activate — the entire setup takes under 10 minutes and requires no code. Once live, every lead captured by the widget fires a Zap within 60 seconds, creating a contact record in the tenant's CRM with name, phone, email, and service interest pre-populated. The v1 release targets three featured CRMs chosen for their concentration in AgentNexLiFy's home-services tenant base: Jobber, ServiceTitan, and Housecall Pro.

The integration uses Zapier's standard polling trigger model. Every minute, Zapier calls `GET /api/zapier/leads/new?since=<iso_timestamp>` with the tenant's API key in the `Authorization: Bearer` header. The backend resolves the API key to a `client_id`, validates tier eligibility, and returns leads created after `since` — paginated, ordered by `created_at` ascending. A Redis key per API key stores the last-seen lead ID so repeated polls over an idle period return empty arrays without a full table scan. Rate limiting enforces 100 requests/minute per API key; a 429 response tells Zapier to back off without permanently deactivating the Zap. The response schema is flat and intentionally minimal: `id`, `client_id`, `name`, `email`, `phone`, `areas_of_interest` (array values joined with `;` to avoid comma-in-value edge cases), `status`, and `created_at`. This matches the canonical `leads` table schema from `schema-discipline.md` exactly — `client_id` not `tenant_id`, `areas_of_interest` not `service_interest`, `status` not `lead_stage`.

API key security follows a single-view, hash-at-rest pattern. When a tenant generates a key, the dashboard shows the full key exactly once (with a copy button and a "store this securely" warning). The key is never stored in plaintext: the backend bcrypt-hashes it immediately and stores only the hash plus the first 8 characters as a display prefix. Revocation is instantaneous — deleting the `tenant_api_keys` row stops the next poll from authenticating. The `last_used_at` timestamp on each key lets tenants audit activity and detect stale or unauthorized keys. Multiple keys per tenant are supported so tenants can maintain separate Zaps for different CRMs or test environments without sharing a single credential.

Tier gating blocks Free-tier tenants at the middleware layer before any lead data is accessed. Growth, Professional, and legacy Growth ($199/mo contracts) all get access. The middleware returns 402 for Free-tier requests, a distinct status code from 401 (invalid key) and 429 (rate limit) so Zapier's task history surfaces actionable error messages rather than generic failures. This gating is enforced server-side, not client-side, making it impossible to bypass via UI manipulation. The goal is a +15% Free→Growth upgrade rate as Zapier appears in paid-tier marketing — friction at the auth layer is intentional and must stay in place even as the feature set expands.

The v1 endpoint (`/api/zapier/v1/leads/new`) is version-pinned in the URL. Schema changes that would break existing Zaps require a v2 endpoint; v1 remains stable until actively deprecated with tenant communication. This matters because Zapier users map fields by name: if `areas_of_interest` were renamed or split into an array in the JSON response, every existing Zap using that field would silently drop data. The v1 contract is: flat object, `;`-joined strings for multi-value fields, no null values (empty string instead), ISO 8601 timestamps. Any deviation from this contract is a breaking change and requires a new version.

## Key Concepts

- **Polling trigger** — Zapier's standard mechanism for triggers that don't push: Zapier calls the source API on a fixed interval (1 minute for paid plans, 15 minutes for free) and compares results to the last poll to detect new items.
- **`since` parameter** — ISO 8601 timestamp passed by Zapier to filter leads created after the last successful poll. Prevents returning leads already processed; the backend also uses Redis `last_seen_lead_id` as a secondary dedup guard.
- **API key hash-at-rest** — The actual key is never stored. Only a bcrypt hash and an 8-character display prefix are persisted. Single-view on creation means even the owner can't retrieve it again — only revoke and regenerate.
- **Tier gating** — Middleware check that resolves the API key to a tenant, reads their plan tier from the `tenants` table, and returns 402 for Free-tier tenants. Growth, Professional, and legacy Growth ($199/mo) pass through.
- **Schema pinning** — The v1 endpoint schema is a contractual commitment. Multi-value fields use `;`-join instead of JSON arrays to avoid CRM field mappers that can't handle arrays. Changes require a v2 endpoint.
- **`tenant_api_keys` table** — New migration table holding `client_id` (FK), `key_hash`, `key_prefix`, `name`, `last_used_at`, `revoked_at`. Never uses `tenant_id`.

## Related Articles

- [[customer-gaps-by-industry]] — Home-services tenants (plumber, HVAC, landscaping) are the primary Zapier audience; industry-specific pain points map directly to which CRM fields matter most.
- [[post-launch-growth-strategy]] — Zapier integration is one of the top activation levers for Growth-tier retention; the +15% Free→Growth upgrade target belongs in the growth strategy roadmap.
- [[saas-churn-benchmarks-2026]] — CRM connectivity reduces churn by making the platform sticky beyond the widget itself — tenants who export leads to CRM have higher retention because switching costs extend to their workflow.
- [[fastapi-best-practices-zhanymkanov]] — The `/api/zapier/*` router follows domain-module structure with its own `router.py`, `schemas.py`, `dependencies.py`; the tier-gating dependency is the canonical example of `valid_tenant_scoped_resource`.

## Relevance to AgentNexLiFy

Zapier is the highest-leverage distribution move for Q3 because it connects the chat widget's lead capture to the tools tenants already trust. A plumber who uses Jobber doesn't want a second place to check for leads — they want leads to appear in Jobber within 60 seconds. That's what this integration delivers, and it's a clear differentiator from GoHighLevel (which requires tenants to use GHL's own CRM) and from raw-webhook alternatives that require developer setup. The $300–500 implementation cost per tenant drops to zero with the Zapier wizard.

The upgrade-gate strategy is intentional: putting Zapier behind Growth+ creates a concrete, high-value reason to leave Free tier. The +15% upgrade target is conservative — any tenant who has ever copy-pasted leads from the dashboard into their CRM will upgrade the moment they see the Zapier option. Support burden should stay below 2% of Growth-tier tickets if the field mapping docs are accurate and the step-by-step CRM guides (see [[zapier-jobber]], [[zapier-servicetitan]], [[zapier-housecall-pro]]) are maintained alongside CRM UI changes. The biggest ongoing risk is Zapier app review rejection, covered in `docs/runbooks/zapier-failures.md`.
