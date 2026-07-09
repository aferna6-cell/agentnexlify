# Idea 03 — SMS Compliance Dashboard Section (Post-Council-Sprint)

**Category:** customer_value  
**Confidence:** MEDIUM  
**Autonomous:** false — REQUIRES HUMAN  
**Effort:** S (~1h frontend + 1 endpoint)

## Summary
TCPA compliance landed in the council sprint (commit 9ddfd0e + 5b9ead8): `sms_compliance.py` (125L), migration 160 (`sms_opt_outs` table), `os_actions/sms.py` suppression, 162 tests. Tenants cannot currently see their opt-out data — there's no UI surface. A small "SMS Compliance" section on the dashboard Settings page would show: total opt-out count, suppressed numbers (masked), last opt-out date, TCPA suppression active badge. This completes the compliance loop: backend guards + tenant visibility.

## Evidence
- `sms_opt_outs` table live since commit 9ddfd0e (2026-06-24)
- `sms_compliance.py::get_opt_out_stats(client_id)` — query ready, no endpoint yet
- Customer risk: tenant sends SMS to opted-out number → TCPA fine $500-$1500 per violation
- Council sprint Fix #8 ("sell outcomes not agents") addressed trust positioning — compliance visibility reinforces it

## Proposed Action
- `GET /api/sms/compliance-stats` — returns `{opt_out_count, last_opt_out_date, sample_masked_numbers}` 
- `frontend/src/pages/Settings.jsx` — add "SMS Compliance" card below Integrations
- Empty state: "No opt-outs recorded" + TCPA info badge
- Non-empty state: count + "Numbers suppressed" list (last 4 digits only)

## Why Competing
- S-effort, additive, completes the council sprint compliance story
- No schema change needed (table already exists)
- But: moratorium active, council sprint just landed (3 days ago), give it time to stabilize

## Sequencing
Strong run 69 candidate after run 65 fix clears pre-commit block. Logical follow-on to council sprint.
