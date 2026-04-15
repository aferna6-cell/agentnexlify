# Audit — Lead Enrichment Rollout (Phase 5)

**Date:** 2026-04-15  
**Owner:** Aidan  
**Feature:** `enable_structured_lead_parser` — structured_extractor managed agent background enrichment  
**Related plan:** `plans/lead-parser-replacement_plan.md`  
**Status:** 🟡 In progress — awaiting MTOptions 24h window

---

## Pre-rollout checklist

- [x] Migration 103 applied to production (2026-04-15)
- [x] `_enrich_lead_from_message` helper live in `widget_helpers.py` (Phase 2)
- [x] 10/10 smoke tests pass (`_smoke_lead_enrichment.py`)
- [x] `backend/tests/test_lead_enrichment.py` — 10 tests in CI
- [x] UI toggle live in WidgetPage.jsx (Phase 4)
- [x] Frontend build green (4.18s, zero warnings)
- [ ] MTOptions flag enabled
- [ ] 24h monitoring clean
- [ ] 4 additional testers enabled

---

## Step 1 — Find MTOptions tenant UUID

```sql
SELECT id, business_name, plan, created_at
FROM tenants
WHERE lower(business_name) LIKE '%mt%options%'
   OR lower(business_name) LIKE '%mtoptions%'
ORDER BY created_at DESC
LIMIT 5;
```

Record UUID here: `________________________________`

---

## Step 2 — Enable flag for MTOptions

```sql
-- Confirm current state first
SELECT tenant_id, enable_structured_lead_parser, enable_ai_fallback
FROM widget_configs
WHERE tenant_id = '<MTOPTIONS-UUID>';

-- Enable
UPDATE widget_configs
SET enable_structured_lead_parser = true
WHERE tenant_id = '<MTOPTIONS-UUID>';

-- Verify
SELECT tenant_id, enable_structured_lead_parser
FROM widget_configs
WHERE tenant_id = '<MTOPTIONS-UUID>';
```

**Enable timestamp:** ________________________________

---

## Step 3 — 24h monitoring queries

Run these ~1h after enabling, then again at 24h mark.

### Activity log — enrichment events
```sql
SELECT
    id,
    created_at,
    metadata->>'session_id'          AS session_id,
    metadata->>'fields_added'        AS fields_added,
    lead_id
FROM activity_log
WHERE activity_type = 'lead_enriched'
  AND tenant_id = '<MTOPTIONS-UUID>'
ORDER BY created_at DESC
LIMIT 50;
```

### Lead-field completion rate (post-enrichment baseline)
```sql
SELECT
    COUNT(*)                                          AS total_leads,
    COUNT(*) FILTER (WHERE name    IS NOT NULL)       AS has_name,
    COUNT(*) FILTER (WHERE email   IS NOT NULL)       AS has_email,
    COUNT(*) FILTER (WHERE phone   IS NOT NULL)       AS has_phone,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE name IS NOT NULL
            AND email IS NOT NULL AND phone IS NOT NULL)
        / NULLIF(COUNT(*), 0), 1
    )                                                  AS pct_full_contact
FROM leads
WHERE client_id = '<MTOPTIONS-UUID>'
  AND created_at > now() - interval '7 days';
```

### Enrichment hit rate (what % of messages triggered enrichment)
```sql
SELECT
    DATE_TRUNC('hour', created_at) AS hour,
    COUNT(*)                        AS enrichments
FROM activity_log
WHERE activity_type = 'lead_enriched'
  AND tenant_id = '<MTOPTIONS-UUID>'
  AND created_at > now() - interval '24 hours'
GROUP BY 1
ORDER BY 1;
```

### Error check (should be zero)
```sql
-- Look for backend errors in Railway logs after flag enable.
-- No DB-side error table — check Railway log stream for:
--   "lead_enrichment: structured_extractor parse failed"
--   "lead_enrichment: unexpected extractor error"
--   "lead_enrichment: leads.update failed"
```

---

## Step 4 — Gate criteria

| Metric | Target | Actual (24h) | Pass? |
|--------|--------|-------------|-------|
| Lead-field completion rate (name+email+phone) | ≥95% | | |
| Zero widget_chat crashes | 0 errors | | |
| Cost per enrichment | ~$0.002 | | |
| MTOptions monthly cost | ≤$1.50 | | |
| `lead_enriched` events firing | >0 in 24h | | |

---

## Step 5 — Expand to 4 additional testers

After MTOptions gate passes:

```sql
-- Find the 4 next-highest-volume tenants with widget activity
SELECT
    wc.tenant_id,
    t.business_name,
    COUNT(cm.id) AS msgs_this_month
FROM widget_configs wc
JOIN tenants t ON t.id = wc.tenant_id
JOIN chat_messages cm ON cm.tenant_id = wc.tenant_id
WHERE cm.created_at > date_trunc('month', now())
  AND wc.enable_structured_lead_parser = false
  AND t.plan != 'free'
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 4;

-- Enable for each
UPDATE widget_configs
SET enable_structured_lead_parser = true
WHERE tenant_id IN ('<UUID2>', '<UUID3>', '<UUID4>', '<UUID5>');
```

---

## Step 6 — Default true for new tenants (migration 104)

After 1 week clean across all 5 testers, apply:

```bash
# Migration already pre-written at:
# migrations/104_widget_configs_structured_lead_parser_default_true.sql
#
# Apply via Supabase MCP:
# mcp__supabase__apply_migration  OR  paste into Supabase SQL editor
```

**Apply date target:** 2026-04-22 (1 week post-MTOptions enable)

---

## Rollback procedure

```sql
-- Single tenant
UPDATE widget_configs
SET enable_structured_lead_parser = false
WHERE tenant_id = '<TENANT-UUID>';

-- All tenants (emergency)
UPDATE widget_configs SET enable_structured_lead_parser = false;
```

Zero code deploy needed — flag is the only gate.

---

## Results log

| Date | Action | Outcome |
|------|--------|---------|
| 2026-04-15 | Phases 1-4 shipped | — |
| | MTOptions enabled | |
| | 24h check | |
| | 4 testers enabled | |
| | Migration 104 applied | |
