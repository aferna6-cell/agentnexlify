# Improvement Backlog — 2026-06-19

## Active

- Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events (run 61 winner, 3rd consecutive, moratorium override, ~20 min human)

## RUN 62 MANDATE

If GH #308 still unimplemented: winner switches to GH #292/#293 (add chatbot/agent_os to
plan-name dicts, 10 min, lower activation energy). 4-consecutive-run threshold.

## Parking Lot (survived debate but not chosen)

- Fix GH #292/#293 — chatbot/agent_os missing from sms_rate_limiter._UNLIMITED_PLANS +
  api_key_auth._ALLOWED_PLANS + billing_reconciliation (~10 min, all new paid tenants broken,
  RUN 62 MANDATE if GH #308 unimplemented)
- Add plan-name invariant guard check 7 to check_project_invariants.py (AUTONOMOUS-EXECUTABLE,
  sequencing: requires GH #292/#293 first, ~15 min Python)
- Cross-tenant isolation test for os_graph_memory (ROI 2.1, 2 tests, ~30 min, M-effort)
- Add New-Table Checklist to schema-discipline.md (ROI 2.0, autonomous markdown edit,
  promote after next Agent OS service lands)
- Fix email_sequences N+1 queries (GH #112, ROI 2.3, M-effort, promote post-moratorium)
- Fix kb-autopopulate.sh broken CLI (ROI 1.8, KB stale 50+ days)
- AI-to-Human Handoff v1 (run 4, 70+ days, Critical gap all industries, Agent OS outbound
  infra available — promote post-moratorium)

## Rejected This Run

None killed outright. Idea 5 (schema-discipline checklist) weakened to parking lot —
valid autonomous candidate, lower urgency vs open revenue bugs.

## Questions for Next Run

1. Has GH #308 been implemented? (check idempotency.py for delete_key method)
2. Has GH #292/#293 been implemented? (grep chatbot in sms_rate_limiter.py)
3. Has moratorium lifted? (true pending ≤ 2)
4. Any new security incidents or payment failures in Railway logs?
5. Is the leadgen pipeline (scripts/leadgen/) getting integrated with the main app's
   leads table, or staying as CSV export? (signals whether a bridge integration is needed)
