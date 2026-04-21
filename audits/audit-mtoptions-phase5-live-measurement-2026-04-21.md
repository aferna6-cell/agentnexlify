# Audit - MTOptions Phase 5 Live Measurement

**Date:** 2026-04-21  
**Owner:** Aidan  
**Source script:** `scripts/mtoptions_phase5_measurement.py`

## Summary

Live measurement succeeded from this repo session by using the Supabase Management API read-only SQL endpoint with `SUPABASE_ACCESS_TOKEN`.

The MTOptions tenant was resolved live and the structured lead parser flag is enabled, but the recent activity windows are currently quiet.

## Live Output

```text
project_ref: pxserpybmajixqrmzaly
tenant_id: 6d76f24b-dd71-470c-9b86-03ee35b7e887
tenant: MTOptions / enterprise / aidanfernandes31@gmail.com
structured_lead_parser_enabled: True
widget_bot_name: MTOptions Assistant
lead_field_completion_rate_7d: n/a
lead_enriched_events_24h: 0
widget_chat_error_events_48h: 0
estimated_monthly_enrichment_cost: $0.00
```

## Interpretation

- Phase 5 is enabled for MTOptions.
- No `widget_chat_error` or `automation_error` events appeared in the last 48 hours.
- No `lead_enriched` events appeared in the last 24 hours.
- No leads were created in the last 7 days, so the completion-rate metric is currently `n/a`, not failing.

## What Changed

- `scripts/mtoptions_phase5_measurement.py` now supports either:
  - `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`, or
  - `SUPABASE_ACCESS_TOKEN` (+ optional `SUPABASE_PROJECT_REF`)

That makes live measurement possible in sessions where the management token is available but the service-role connection values are not.

## Follow-Up

1. Re-run this script after the next real MTOptions traffic window.
2. If the tenant is expected to be active this week, investigate whether the lull is a demand problem, a distribution problem, or a tracking gap.
