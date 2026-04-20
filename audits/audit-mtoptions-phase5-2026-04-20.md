# Audit - MTOptions Phase 5 Measurement

**Date:** 2026-04-20
**Owner:** Aidan
**Workstream:** MTOptions Phase 5 rollout / monitoring
**Related artifacts:**
- [audit-lead-parser-rollout-2026-04-16.md](./audit-lead-parser-rollout-2026-04-16.md)
- [audit-mtoptions-chatbot-2026-04-18.md](./audit-mtoptions-chatbot-2026-04-18.md)
- [scripts/mtoptions_phase5_measurement.py](../scripts/mtoptions_phase5_measurement.py)

## Summary

I could not complete live Phase 5 measurement from this repo session.

Local non-interactive measurement was blocked because the shell had `SUPABASE_ACCESS_TOKEN` set, but not the database connection inputs the local Python client needs:

- `SUPABASE_URL` missing
- `SUPABASE_KEY` missing
- `SUPABASE_SERVICE_KEY` missing
- `supabase` CLI not installed in PATH

That means there was no safe local path to query Supabase directly without asking for secrets or inventing credentials. I did not expose any secret values.

## What I added

- A safe, env-driven helper script at [scripts/mtoptions_phase5_measurement.py](../scripts/mtoptions_phase5_measurement.py).
- A copy-paste runbook below that can be executed once Supabase access is available.

## Measurement blocker

The repo is configured for Supabase MCP access via `.mcp.json`, but this shell session does not have the database URL or service key needed for the local Python client. The MCP access token alone is not enough for the script path.

Until `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are available in the shell or `.env`, I cannot run live queries non-interactively from the workspace.

## Copy-paste runbook

### 1. Resolve the MTOptions tenant row

```sql
SELECT id, business_name, plan, owner_email
FROM tenants
WHERE business_name ILIKE '%MTOptions%'
   OR owner_email = 'support@mtoptions.com'
ORDER BY business_name, plan, owner_email;
```

If more than one row returns, use the enterprise tenant row already referenced in prior audits or pass the chosen UUID explicitly to the measurement script.

### 2. Confirm the Phase 5 flag

```sql
SELECT client_id, enable_structured_lead_parser, bot_name
FROM widget_configs
WHERE client_id = '<mtoptions-client-id>';
```

### 3. Measure the four Phase 5 metrics

#### Metric A: lead-field completion rate, last 7 days

```sql
SELECT
  COUNT(*) AS total_leads,
  COUNT(*) FILTER (
    WHERE name IS NOT NULL
      AND email IS NOT NULL
      AND phone IS NOT NULL
  ) AS complete_leads,
  ROUND(
    100.0 * COUNT(*) FILTER (
      WHERE name IS NOT NULL
        AND email IS NOT NULL
        AND phone IS NOT NULL
    ) / NULLIF(COUNT(*), 0),
    1
  ) AS completion_rate_pct
FROM leads
WHERE client_id = '<mtoptions-client-id>'
  AND created_at > now() - interval '7 days';
```

Pass: `completion_rate_pct >= 95.0`

#### Metric B: `lead_enriched` events, last 24 hours

```sql
SELECT COUNT(*) AS lead_enriched_events_24h
FROM activity_log
WHERE tenant_id = '<mtoptions-client-id>'
  AND activity_type = 'lead_enriched'
  AND created_at > now() - interval '24 hours';
```

Pass: `lead_enriched_events_24h >= 1`

#### Metric C: widget chat / automation error events, last 48 hours

```sql
SELECT COUNT(*) AS error_events_48h
FROM activity_log
WHERE tenant_id = '<mtoptions-client-id>'
  AND activity_type IN ('widget_chat_error', 'automation_error')
  AND created_at > now() - interval '48 hours';
```

Pass: `error_events_48h = 0`

#### Metric D: estimated monthly enrichment cost

```sql
WITH enrichment AS (
  SELECT COUNT(*) AS lead_enriched_events_24h
  FROM activity_log
  WHERE tenant_id = '<mtoptions-client-id>'
    AND activity_type = 'lead_enriched'
    AND created_at > now() - interval '24 hours'
)
SELECT
  lead_enriched_events_24h,
  ROUND(lead_enriched_events_24h * 30 * 0.002, 2) AS estimated_monthly_cost_usd
FROM enrichment;
```

Pass: `estimated_monthly_cost_usd <= 1.50`

## Script usage

Once the shell has `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`, run:

```bash
python scripts/mtoptions_phase5_measurement.py --tenant-id <mtoptions-client-id>
```

If `--tenant-id` is omitted, the script will try to discover MTOptions automatically, but it will refuse to guess if duplicate rows make the result ambiguous.

## Notes

- I did not touch `planning/launch-readiness-rubric.md`.
- I did not run live DB queries.
- The script prints only the four DB-observable Phase 5 metrics; exact extractor log checks still belong in Railway logs, not this repo.

Verified: local repo guidance read, MTOptions and lead-parser audits read, local Supabase/CLI path checked, live measurement blocked by missing env/CLI. PASS for desk audit, FAIL for live measurement.
