# Audit — Lead Parser Replacement Phase 5 Rollout

**Date:** 2026-04-16
**Owner:** Aidan
**Spec:** [specs/lead-parser-replacement_spec.md](../specs/lead-parser-replacement_spec.md)
**Plan:** [plans/lead-parser-replacement_plan.md](../plans/lead-parser-replacement_plan.md)
**Status:** Phases 1–4 shipped (2026-04-15). Phase 5 runbook below. Tiny gap closed 2026-04-16.

## Summary

Structured lead parser (managed Haiku agent wrapping `structured_extractor`) is fully wired end-to-end. Behavior is off by default, gated on `widget_configs.enable_structured_lead_parser`. This audit closes Phase 5 — MTOptions rollout, monitoring, and success-gate verification — plus one tiny cleanup found while auditing.

## What shipped (phases 1–4)

| Layer | Change | File |
|---|---|---|
| Migration | `widget_configs.enable_structured_lead_parser` boolean, default false | `migrations/103_widget_configs_enable_structured_lead_parser.sql` |
| Migration | `leads.enrichment_source` text, documented `'regex' \| 'ai' \| NULL` | [migrations/105_leads_enrichment_source.sql](../migrations/105_leads_enrichment_source.sql) |
| Backend helper | `_enrich_lead_from_message` — background enrichment, sets `enrichment_source='ai'` when fields added | [backend/routers/widget_helpers.py:~1605](../backend/routers/widget_helpers.py) |
| Backend wire | `background_tasks.add_task(...)` gated on flag | [backend/routers/widget_chat.py](../backend/routers/widget_chat.py) |
| Tests | 10 unit tests, 4 classes — skip paths, merge, persist, never-crash | [backend/tests/test_lead_enrichment.py](../backend/tests/test_lead_enrichment.py) |
| UI | Dashboard toggle + `WidgetConfigDetail` / `WidgetConfigUpdateRequest` schemas | `frontend/src/pages/WidgetPage.jsx`, `backend/models/schemas.py`, `backend/routers/auth.py` |
| Frontend display | `enrichment_source === 'ai'` badge on LeadsPage + AI-enriched count card | [frontend/src/pages/LeadsPage.jsx:127](../frontend/src/pages/LeadsPage.jsx) |

## Cleanup closed this audit (2026-04-16)

**Gap:** Migration 105 column values documented as `'regex' | 'ai' | NULL`, but production code only wrote `'ai'` (in the enrichment helper). Regex-captured leads left `enrichment_source=NULL`, so the dashboard's regex-vs-AI breakdown silently showed 0% regex.

**Fix:** Added `"enrichment_source": "regex"` to the insert payload in `_capture_leads_from_session` ([backend/routers/widget_helpers.py:1232](../backend/routers/widget_helpers.py)). The AI enrichment helper's later-running overwrite to `'ai'` is preserved because it updates the column inside `update_payload` on the same row (widget_helpers.py:~1605). Lifecycle:

1. Regex capture creates lead → `enrichment_source='regex'`
2. (Optional, per-tenant flag) AI helper adds missing fields → `enrichment_source='ai'`
3. If AI helper has nothing to add → early return, tag stays `'regex'`

**Regression test:** [backend/tests/test_lead_regex_tag.py](../backend/tests/test_lead_regex_tag.py) — asserts insert payload carries `enrichment_source='regex'` + payload invariants (`client_id`, `status`, `source`, `email`, `name`).

**Why not also set on update path:** The update path at widget_helpers.py:~1193 runs when regex re-extracts info for an existing lead. Tagging `'regex'` there would clobber a valid `'ai'` from a prior enrichment. Safer to only tag on INSERT; the column then reflects the first-writer-wins origin.

## Rollout runbook (Phase 5)

### Step 1 — Enable flag for MTOptions

MTOptions is the highest-signal tenant (704 msgs/mo per 2026-04-08 tenant-chatbot-audit). Flag-flip SQL:

```sql
-- Manual step via Supabase SQL editor or mcp__supabase__execute_sql
-- Replace <mtoptions-client-id> with actual UUID before running
UPDATE widget_configs
  SET enable_structured_lead_parser = true
  WHERE client_id = '<mtoptions-client-id>'
  RETURNING client_id, enable_structured_lead_parser;
```

**Pre-check:** confirm `client_id` via `SELECT id, business_name FROM clients WHERE business_name ILIKE '%mtoption%';` — do NOT guess the UUID.

### Step 2 — 24-hour monitor

Watch the activity log for enrichment events:

```sql
SELECT
  created_at,
  lead_id,
  metadata->>'fields_added' AS fields_added,
  metadata->>'source' AS source
FROM activity_log
WHERE activity_type = 'lead_enriched'
  AND tenant_id = '<mtoptions-client-id>'
ORDER BY created_at DESC
LIMIT 50;
```

**Also watch for crashes** — structured_extractor errors should NOT bubble up to widget chat:

```sql
-- No widget_chat 500s should have increased
SELECT date_trunc('hour', created_at) AS hr, count(*)
FROM activity_log
WHERE activity_type IN ('widget_chat_error', 'automation_error')
  AND tenant_id = '<mtoptions-client-id>'
  AND created_at > now() - interval '48 hours'
GROUP BY 1 ORDER BY 1;
```

### Step 3 — Success gates (go / no-go to broader rollout)

| Metric | Target | Query |
|---|---|---|
| Lead field-completion rate (name+email+phone within 3 msgs) | ≥95% on enriched tenant | `SELECT count(*) FILTER (WHERE name IS NOT NULL AND email IS NOT NULL AND phone IS NOT NULL)::float / count(*) FROM leads WHERE client_id = '<mtoptions>' AND created_at > now() - interval '24 hours';` |
| `lead_enriched` activity events | ≥1 per day for active tenant | See Step 2 query |
| Widget chat 500s | No increase vs prior 48h | See Step 2 crash query |
| Enrichment call cost | ≤$1.50/tenant/month | Anthropic usage dashboard |
| Extractor error rate | <5% of enrichment attempts | `grep "lead_enrichment: structured_extractor parse failed" <railway logs>` |

### Step 4 — Expand to remaining 4 testers

If MTOptions gates pass after 24h:

```sql
UPDATE widget_configs
  SET enable_structured_lead_parser = true
  WHERE client_id IN (
    '<tester-2-uuid>', '<tester-3-uuid>', '<tester-4-uuid>', '<tester-5-uuid>'
  );
```

### Step 5 — Default ON (after 1 clean week)

Requires a new migration to change the column default:

```sql
-- migrations/1NN_enable_structured_lead_parser_default.sql
ALTER TABLE widget_configs
  ALTER COLUMN enable_structured_lead_parser SET DEFAULT true;

UPDATE widget_configs
  SET enable_structured_lead_parser = true
  WHERE enable_structured_lead_parser = false;
```

Only ship Step 5 after Steps 1–4 show zero regressions for 7+ days.

## Rollback plan

Per-tenant flip back to false:

```sql
UPDATE widget_configs
  SET enable_structured_lead_parser = false
  WHERE client_id = '<client-id>';
```

Zero code rollback needed — the synchronous regex path still runs for every tenant regardless of the flag. The managed-agent call is additive background enrichment.

## Risks carried over from spec

| Risk | Current mitigation |
|---|---|
| Managed agent hallucinating field values | "Regex wins on fields both populated" policy enforced in `_enrich_lead_from_message` |
| Duplicate leads | Dedup by email + client_id before insert; AI helper updates via `id` eq filter |
| Anthropic outage | `_enrich_lead_from_message` catches `ValueError` + `Exception`, never raises |
| Extractor not provisioned | `ManagedAgentNotConfigured` caught in the generic `Exception` branch |
| Cost blowout on spam tenant | Widget chat rate-limited at 60/min; caps enrichment volume implicitly |

## Next actions (owner: Aidan)

1. Look up MTOptions `client_id` via Supabase SQL editor
2. Run Step 1 flag-flip
3. Check Step 2 queries after 24h
4. If gates green → run Step 4
5. Revisit this doc after 1 week for Step 5 decision
