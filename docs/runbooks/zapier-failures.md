# Zapier Integration — Failure Runbook

**Service:** AgentNexLiFy Zapier App (`/api/zapier/v1/`)  
**Owner:** Engineering  
**Last updated:** 2026-04-20  
**Escalation:** Check Railway logs for backend errors; Supabase for DB issues; Zapier partner dashboard for app-level rejections.

---

## Failure 1 — Rate Limit Trips (429 Too Many Requests)

### Symptoms
- Zapier task history shows "Request failed: 429" for one or more tenant Zaps.
- `backend/logs` shows `RATE_LIMIT_EXCEEDED` for a specific `key_prefix`.
- In extreme cases, a tenant reports "my Zap isn't firing."

### Causes
1. **Tenant has multiple Zaps using the same API key** — each polls every 1 minute; 3+ Zaps = 180+ req/hour, approaching the 100 req/min limit if all Zaps poll in the same minute window.
2. **Zapier polling at sub-minute intervals** — can happen on Zapier's paid plans during backfill after re-activation.
3. **Automated scripts hitting the endpoint** — tenant using the Zapier API key outside of Zapier.

### Diagnosis
```bash
# Check rate limit hits in Railway logs (last 1 hour)
# Filter: "RATE_LIMIT_EXCEEDED" AND key_prefix
# Look for: which key_prefix is tripping, how often, time distribution
```

Query Supabase `tenant_api_keys` for the affected key:
```sql
SELECT key_prefix, last_used_at, client_id
FROM tenant_api_keys
WHERE key_prefix = '<first-8-chars>'
  AND revoked_at IS NULL;
```

### Recovery
1. **If tenant has multiple Zaps on one key:** Contact tenant. Recommend generating a separate API key per Zap (Settings → Integrations → Zapier → Generate API Key). Each key has its own rate limit bucket.
2. **If it's a backfill spike:** No action needed. Zapier self-regulates after the backfill completes. Zaps resume normally within 5 minutes.
3. **If scripts are hitting the endpoint:** Contact tenant. The API key is for Zapier use only; direct API consumers should use the standard REST API with a different auth pattern.
4. **If the rate limit is too low for a legitimate use case:** Review usage data. The 100 req/min limit is intentionally conservative for v1. A per-tenant limit increase can be applied via `ZAPIER_RATE_LIMIT_PER_KEY` env var in Railway (requires deploy).

### Prevention
- Each Zap should use its own named API key. This is documented in the Zapier setup guides.
- Consider distributing rate limits across keys when a tenant has many integrations (future: per-organization limit pool).

---

## Failure 2 — API Key Leak (Key Exposure or Unauthorized Use)

### Symptoms
- Tenant reports their API key was shared publicly (GitHub repo, Slack, screenshot).
- Unusual `last_used_at` pattern: key used at odd hours or from IPs inconsistent with Zapier's documented IP ranges.
- Support ticket: "I didn't authorize any new Zap, but my leads are being accessed."

### Zapier IP Ranges (for reference)
Zapier documents their static egress IPs in their developer docs. If `last_used_at` shows activity outside Zapier's IP range, the key was used by a non-Zapier client.

### Rotation Procedure (tenant self-service — fastest path)
1. Tenant logs into AgentNexLiFy dashboard.
2. Settings → Integrations → Zapier.
3. Locate the compromised key by its prefix (e.g., `ANX_abc1...`).
4. Click **Revoke** on that key. The key is immediately invalidated — all Zaps using it stop firing within 1 minute (next poll attempt).
5. Generate a new key: **Generate API Key**, label it, copy it.
6. In Zapier, go to **Connected Accounts → AgentNexLiFy** → edit the connection → replace the key with the new one.
7. Test the updated connection. All Zaps automatically resume using the new key.

### Rotation Procedure (engineering — if tenant can't self-serve)
```sql
-- Immediately revoke the compromised key
UPDATE tenant_api_keys
SET revoked_at = NOW()
WHERE key_prefix = '<first-8-chars>'
  AND client_id = '<verified-client-id>';

-- Verify revocation
SELECT key_prefix, revoked_at FROM tenant_api_keys WHERE key_prefix = '<first-8-chars>';
```

After revocation, the next Zapier poll returns 401. Zapier marks the Zap as "needs reconnection" and pauses it. The tenant must supply a new key to resume.

### Post-Rotation Verification
- Confirm in Supabase that `revoked_at IS NOT NULL` for the old key.
- Confirm `last_used_at` is not updated after revocation (no new successful polls).
- Notify tenant: old key is dead, Zap needs a new key, all lead data captured before revocation remains in the CRM (the leak does not affect historical data).

### Audit Logging
All successful authentications update `last_used_at` on the `tenant_api_keys` row. For forensic analysis, Railway logs contain the key prefix and the response code for every `/api/zapier/v1/` request. Supabase Row History (if enabled) shows who updated `revoked_at`.

### What Was Exposed
The Zapier endpoint returns lead data scoped to the tenant. A leaked key allows read access to leads (name, email, phone, areas_of_interest) for that tenant only — it does NOT grant access to other tenants, to the dashboard, or to payment/billing data. Scope the incident report accordingly.

---

## Failure 3 — Zapier App Review Rejection

### Symptoms
- Zapier review team sends an email to the Zapier developer account (Aidan) citing rejection reasons.
- The AgentNexLiFy app in Zapier's App Directory shows status "Rejected" or "Needs Changes".
- No new Zaps can be created from the app (existing Zaps using the private-beta app continue working).

### Common Rejection Reasons and Responses

| Rejection Reason | Root Cause | Response |
|---|---|---|
| "Authentication does not work as expected" | API key connection test failing in Zapier's automated review | Verify `/api/zapier/v1/auth/test` endpoint returns 200 with `{"status": "ok", "client_id": "..."}` |
| "Trigger returns no sample data" | Test lead endpoint empty during review | Ensure the Zapier developer account is connected to a test tenant with ≥1 lead in the DB |
| "Field names are not human-readable" | `areas_of_interest` or `client_id` flagged | Rename display labels in the Zapier CLI app definition (not the API schema): `"label": "Areas of Interest"` |
| "Action not clearly described" | Trigger description lacks clarity | Update the trigger description in `zapier-app/src/triggers/new_lead.js` to explain what fires the trigger |
| "Missing required error handling" | 4xx responses not handled per Zapier spec | Ensure 401/402/429 responses follow Zapier's error format: `{"code": "AuthenticationError", "message": "..."}` |
| "Privacy policy not accessible" | AgentNexLiFy privacy policy URL in app definition is 404 | Update `zapier-app/package.json` → `"privacyPolicyUrl"` to current URL |

### Review Resubmission Procedure
1. Read the rejection email carefully — Zapier provides specific line numbers or fields that failed.
2. Fix issues in the Zapier CLI app definition (`zapier-app/`).
3. Run `zapier test` locally to confirm automated tests pass.
4. Run `zapier push` to update the app in Zapier's dev environment.
5. Resubmit for review via `zapier promote <version>` after any required promotion steps.
6. Email the Zapier review team referencing the original rejection ticket number to expedite re-review.

### Timeline Expectations
- Initial review: 2–4 weeks.
- Re-review after addressing feedback: 1–2 weeks.
- During review, the app is available in private beta — existing tenants with the invite link can continue to create and use Zaps.

---

## Failure 4 — v1 → v2 Migration

### When This Applies
A schema change to the leads table or Zapier API response that breaks existing Zaps requires a v2 endpoint. Breaking changes include:

- Renaming any field in the response (e.g., `areas_of_interest` → `services`)
- Changing a field's type (e.g., string → array)
- Removing a field
- Changing timestamp format
- Changing the `;`-join separator for multi-value fields

Adding new fields is NOT a breaking change — Zapier ignores unmapped fields.

### Migration Procedure

**Phase 1 — Ship v2 endpoint without deprecating v1**
1. Create `backend/routers/zapier_v2.py` (new module, never edit `zapier_v1.py` for this).
2. Register at `/api/zapier/v2/leads/new` in `main.py`.
3. Update Zapier CLI app definition to default new Zaps to v2.
4. Document v2 changes in `docs/dev-knowledge/schema-log.md`.
5. Deploy. Both v1 and v2 serve simultaneously.

**Phase 2 — Notify tenants (minimum 30-day window)**
1. In-app banner: "Zapier integration update: please reconnect your Zap by [date]. [How-to guide link]"
2. Email campaign to all Growth/Pro tenants with active API keys.
3. Update `knowledge-base/wiki/integrations/zapier.md` to reflect v2 schema.
4. Update all three CRM guides (zapier-jobber, zapier-servicetitan, zapier-housecall-pro) for any field changes.

**Phase 3 — Deprecate v1 after deadline**
1. At `revoked_at` deadline, update v1 endpoint to return `410 Gone` with body:
   ```json
   {"code": "EndpointDeprecated", "message": "This endpoint was deprecated on YYYY-MM-DD. Please reconnect your Zap using the v2 endpoint. See [docs-url]."}
   ```
2. Keep the 410 response for 90 days so stale Zaps get actionable errors instead of silent failures.
3. After 90 days, remove `zapier_v1.py` from the codebase.

### Never Do
- **Never rename fields on a live v1 endpoint** — breaks every Zap silently (field maps to empty, no error).
- **Never remove a field without a 30-day deprecation window.**
- **Never change the `;` separator** — CRM guides and tenant Zaps all hardcode this expectation.

---

## Escalation Contacts

| Scenario | Contact |
|---|---|
| Zapier app review rejection | Zapier developer support email (in the Zapier developer account) |
| Data breach via leaked API key | Engineering → immediately revoke + notify tenant; assess scope |
| Rate limit causing tenant revenue impact | Engineering → temporary per-tenant limit increase via Railway env var |
| v2 migration timeline decision | Engineering + product review |
