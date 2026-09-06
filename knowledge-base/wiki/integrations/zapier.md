---
title: "Zapier CRM Export — new_lead Trigger via Polling API Keys"
category: integrations
tags: [zapier, crm-export, api-keys, new-lead, polling, jobber, servicetitan, housecall-pro, tier-gated]
sources: ["specs/zapier-crm-export_spec.md"]
created: 2026-07-22
updated: 2026-07-27
summary: "Zapier CRM Export lets a tenant push every new AgentNexLiFy lead into Jobber, ServiceTitan, Housecall Pro, and 6,000+ other apps through a tier-gated, API-key-authenticated polling endpoint that returns flat lead rows Zapier reads once a minute and de-duplicates on the lead id."
---

# Zapier CRM Export — new_lead Trigger via Polling API Keys

Zapier CRM Export turns every lead the widget captures into a row in the tenant's existing CRM, with no custom integration work. The tenant generates an API key in the dashboard, pastes it into a Zapier "new lead" trigger, and from then on each lead AgentNexLiFy captures flows into Jobber, ServiceTitan, Housecall Pro, or any of Zapier's 6,000+ apps. This meets small-business owners where they already work: they do not move into a new system, their leads just show up where they already run their jobs. It is the outbound half of the platform's lead value — the widget and photo-quote capture the lead, Zapier delivers it into the tools the business already pays for.

The transport is a polling API, not a webhook, chosen for reliability. Zapier calls `GET /api/zapier/leads/new?since=<iso>&limit=<n>` once a minute per active Zap; the endpoint returns leads created after `since`, ordered oldest-first, as flat one-level dicts. Zapier advances `since` to the newest lead it has seen and de-duplicates on the lead `id`, so the same lead is never delivered twice even across overlapping polls. A polling design has no delivery-failure retry problem to manage (a webhook that 500s is lost; a poll just runs again next minute) and no inbound endpoint for the tenant to expose. The endpoint lives in `backend/routers/zapier.py` alongside the dashboard key-management routes.

Authentication is a per-tenant API key, and access is tier-gated. Keys are generated in the dashboard (Settings → Integrations → Zapier), shown exactly once at creation, and stored only as a bcrypt hash (cost 12) plus an 8-character prefix — the raw key is never persisted or logged and cannot be retrieved after the modal closes. Every request carries the key in the `X-Api-Key` header; the endpoint resolves it to a `client_id`, checks the tenant's plan, and returns 401 for an invalid or revoked key, 402 for a Free-tier or cancelled-subscription tenant, 429 when the per-key rate limit trips, and 200 with results otherwise. The dashboard page can generate multiple named keys and revoke any of them (revocation is a soft-delete: `revoked_at` is set, the key stops authenticating immediately).

The response schema is deliberately flat and versioned. Each lead row is `{id, client_id, name, email, phone, areas_of_interest, status, created_at}` — no nested objects, because a Zapier field mapping is easiest against a flat shape. `areas_of_interest` is a semicolon-joined string (`"plumbing;emergency"`), not comma-joined, so a value that itself contains a comma cannot break the field. The columns are the canonical ones (`client_id`, `status`, `areas_of_interest`) — never `tenant_id`, `lead_stage`, or `service_interest`, which have burned the codebase before (see [[photo-quote]] for the same `client_id` discipline). The schema is pinned as v1; any breaking change ships as `/api/zapier/v2/leads/new` rather than mutating v1, so existing Zaps never break under a tenant.

Rate limiting is per-key, in-memory, and fail-open. Each API key gets a per-minute request budget; the limiter counts requests per prefix in a per-process bucket and returns 429 with a `Retry-After` header past the budget. Because the counter is per-worker and in-memory, it is a coarse guardrail against a runaway Zap, not a billing meter — and it fails open: if the limiter itself errors, the request is allowed rather than blocked, because a limiter outage must never take down a paying tenant's lead flow. Typical Zapier polling (once a minute per Zap) sits far under any reasonable budget, so the limit only bites on misconfiguration or abuse.

The featured CRMs are the three that matter most to the home-services base: Jobber, ServiceTitan, and Housecall Pro. Each has its own tenant-facing setup guide ([[zapier-jobber]], [[zapier-servicetitan]], [[zapier-housecall-pro]]) walking the owner from "generate a key" to "leads appear in my CRM." OAuth-based auth and dynamic per-tenant custom fields are explicitly post-GA (v1.1, issue #63): they require Zapier partner-tier app status and production usage data, so v1 ships with the simpler, robust API-key model and a fixed flat schema that already covers the fields a CRM needs.

The Zapier app definition lives in the `zapier/` directory at the repo root. `zapier/index.js` declares the app with custom API-key auth and the `new_lead` trigger; `zapier/authentication.js` sets the `X-Api-Key` header and tests it against `GET /api/zapier/leads/new`; `zapier/triggers/new_lead.js` performs the polling fetch with a 30-day lookback and a page limit of 50; `zapier/constants.js` supplies `BASE_URL` (defaulting to the production Railway URL) and the lookback/limit constants. The directory also contains a `zapier/README.md` that cross-references this article and documents the remaining publication steps — `zapier validate`, `zapier push`, and `zapier promote` — which require a Zapier developer account and are tracked in issue #61. Until promotion, tenants connect via the current API-key flow rather than through the Zapier marketplace.

## Key Concepts

- **Polling trigger** — Zapier calls `GET /api/zapier/leads/new?since=&limit=` once a minute; the endpoint returns leads created after `since`, oldest-first. `since` is the cursor; Zapier de-duplicates on lead `id`, so no lead is delivered twice.
- **Single-view API key** — Keys are generated in the dashboard, shown once, and stored as a bcrypt(cost 12) hash + 8-char prefix. The raw key is never persisted or logged and is unrecoverable after creation.
- **Tier gate** — The endpoint returns 402 for Free-tier or cancelled-subscription tenants; only premium plans (agent_os + grandfathered growth/autopilot/professional/enterprise) can poll.
- **Flat, `;`-joined schema** — `{id, client_id, name, email, phone, areas_of_interest, status, created_at}`; `areas_of_interest` is semicolon-joined so commas in values are safe. Canonical columns only (`client_id`, not `tenant_id`).
- **Per-key rate limit** — In-memory per-prefix per-minute budget; 429 + `Retry-After` past the budget; fails open so a limiter error never blocks a paying tenant.
- **v1 pinned** — The schema is versioned; a breaking change ships as `/v2/leads/new`, never a mutation of v1, so live Zaps do not break.

## Relevance to AgentNexLiFy

Zapier CRM Export is the outbound complement to the platform's lead-capture moat: the widget and photo-quote win the lead, and Zapier delivers it into the tools the business already runs, without asking the owner to adopt a new system. It is a retention and stickiness lever — once a tenant's leads flow automatically into Jobber or ServiceTitan, the platform is wired into their daily operations. It is also a premium gate (agent_os + legacy paid), so it reinforces the plan ladder. Against GoHighLevel's all-in-one pitch, "keep your CRM, we just feed it" is a lower-friction story for an owner who is not going to rip out the field-service software they already depend on.

## Related Articles

- [[zapier-jobber]] — tenant setup guide: send leads to Jobber.
- [[zapier-servicetitan]] — tenant setup guide: send leads to ServiceTitan.
- [[zapier-housecall-pro]] — tenant setup guide: send leads to Housecall Pro.
- [[photo-quote]] — the inbound lead-capture feature this delivers outbound, and the same `client_id` schema discipline.
- `zapier/index.js`, `zapier/triggers/new_lead.js` — the Zapier CLI app definition committed to repo

Updated 2026-07-27 due to #555
