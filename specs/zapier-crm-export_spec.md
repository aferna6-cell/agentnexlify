# Zapier CRM Export — PRD

**Status:** grilled 2026-04-20, ready for issue staging
**Owner:** Aidan
**Created:** 2026-04-20
**Target tier:** Growth + Professional (Free excluded); legacy Growth $199 tenants included
**v1 auth:** API key; **v1.1:** add OAuth after Zapier partner-tier review

## Goal

Publish Zapier app exposing AgentNexLiFy leads as a trigger. Tenants export new leads to their CRM (HubSpot, Jobber, ServiceTitan, etc.) without custom webhook code. Unlocks revenue tier upgrade.

## Non-goals

- Bidirectional sync (Zapier app is outbound-only v1)
- Contact field updates (one-shot insert only)
- Invoice / appointment sync (separate Zap triggers later)
- Make.com / n8n apps v1 (Zapier has biggest SMB share)
- Custom field mapping UI (use Zapier's built-in mapper)

## Target users

Growth+ tenants who already use external CRM and want leads flowing into it. Ballpark: 30% of Growth tenants per industry benchmark.

## User stories

1. Plumber-tenant opens Zapier → searches "AgentNexLiFy" → connects with API key from dashboard → picks trigger `New Lead` → action `Create Contact in Jobber` → tests → activates.
2. Lead hits widget → within 60s, Zap fires → HubSpot contact created with name/phone/email/areas_of_interest.
3. Tenant revokes API key in dashboard settings → Zap stops firing within 5min.

## Acceptance criteria

### Zapier app
- Published to Zapier App Directory (private beta first, then public)
- Single trigger v1: `new_lead`
- Auth: API key + tenant_id header
- Schema matches `leads` table canonical fields (see schema-discipline.md)
- Rate-limited server-side: 100 requests/min per API key
- Polling interval 1min (Zapier default)

### Backend
- `GET /api/zapier/leads/new?since=<iso>` — returns leads created after `since`, paginated
- Auth middleware validates API key → resolves `client_id`, blocks Free tier, allows Growth/Pro + legacy Growth
- Uses canonical schema (flat, Q6 A): `id, client_id, name, email, phone, areas_of_interest (;-joined string), status, created_at`
- **NEVER `tenant_id` or `lead_stage` or `service_interest`** (CLAUDE.md Rule 1-3)
- Returns 401 on invalid key, 402 on Free tier, 429 on rate limit, 200 with results array
- Redis cache `last_seen_lead_id` per API key — reduces polling overhead

### Dashboard
- New `Settings → Integrations → Zapier` page
- "Generate API key" button → shows key ONCE + copy button + "Store securely" warning
- Lists existing keys with last-used timestamp + revoke button
- "Connect to Zapier" deep link opens Zapier app wizard

### Schema
New table `tenant_api_keys`:
- `id uuid pk`
- `client_id uuid` (FK tenants) — **client_id not tenant_id**
- `key_hash text` (bcrypt of key)
- `key_prefix text` (first 8 chars for display)
- `name text` (user-facing label)
- `last_used_at timestamptz`
- `created_at timestamptz`
- `revoked_at timestamptz nullable`
- `created_by_user_id uuid nullable`

## Success metrics

- 20% Growth-tier tenants activate Zapier within 30 days of launch
- <2% support tickets mentioning Zapier
- +15% Free→Growth tier upgrade rate with Zapier in paid-tier marketing
- p95 lead→CRM latency <90s

## Risks

| Risk | Mitigation |
|---|---|
| Zapier app review 2-4 weeks | Submit early, private beta while waiting |
| Schema drift breaks Zaps silently | `/api/zapier/*` is v1-pinned, changes require v2 endpoint |
| API key leak exposes tenant data | Hash-at-rest, single-view on create, revoke UI visible |
| Tenant maps to wrong CRM fields | Good docs + sample field mapping in Zapier app |
| Polling overhead 100 tenants × 1min = lot of noise | Redis cache last-seen-id per key |

## Dependencies

- Migration NNN for `tenant_api_keys`
- `secrets` utility for key gen (`secrets.token_urlsafe(32)`)
- Zapier developer account (Aidan) + app submission
- Frontend Settings page refactor
- Docs: `knowledge-base/wiki/integrations/zapier.md`

## Resolved decisions (grill-me 2026-04-20)

1. **Tier gating:** Growth + Professional both; Free excluded (option C)
2. **Auth:** API key v1 ships now; OAuth v1.1 after Zapier partner-tier review (option C)
3. **Featured CRMs:** Jobber, ServiceTitan, Housecall Pro (option B) — matches home-services tenant base
4. **Free tier:** excluded entirely (option A) — consistent with Q1
5. **Legacy pricing:** $199 legacy Growth tenants get Zapier (option A) — gated by tier name, not contract vintage
6. **Zap output schema:** flat; arrays joined with `;` to avoid comma-in-value edge cases (option A)
7. **Custom fields:** canonical fields only v1; dynamic introspection v1.1 (option D)

## Rollout

1. Migration + `tenant_api_keys`
2. Backend `/api/zapier/*` routes + middleware
3. Frontend Settings → Integrations page
4. Zapier CLI app: trigger, auth, sample data
5. Submit to Zapier app review
6. Docs + tutorial
7. Private beta: 5 tenants
8. Fix → public release
9. Add second trigger (`new_appointment`) v1.1

## Skipped scope

- Bidirectional sync (v2)
- Other marketplaces (Make.com v1.1, n8n later)
- Custom triggers per tenant (v2)
- Webhook endpoint for push-based CRMs (v1.1)
