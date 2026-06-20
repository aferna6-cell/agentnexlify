# Improvement Backlog — 2026-06-20-pm (Run 64)

## Active

- Fix GH #292/#293 — add chatbot/agent_os to sms_rate_limiter._UNLIMITED_PLANS, api_key_auth._ALLOWED_PLANS, billing_reconciliation._PLAN_AGENT_RUN_CAPS/_PLAN_BASELINE_AI_TOKENS (~10 lines, 3 files, human required)

## Bonus Actions (do alongside winner)

- **Bonus A:** Fix GH #308 — add `delete_key()` to idempotency.py, call in stripe_webhooks.py exception handler before re-raise (~10 lines, human required, payment recovery)
- **Bonus B:** Add plan-name guard Check 7 to check_project_invariants.py (AUTONOMOUS-EXECUTABLE after Bonus A lands)

## Parking Lot (survived debate but not chosen)

- Fix kb-autopopulate.sh (46-day stale KB, ROI 1.8 — simple `|| true` fallback or curl replacement)
- Add New-Table Checklist to schema-discipline.md (ROI 2.0, prevents _TENANT_COLUMN_OVERRIDES miss on new tables)
- Cross-tenant isolation test for os_graph_memory.py (ROI 2.1, 2 tests verifying client_id scope)

## Rejected This Run

- Fix GH #308 as winner — mandate hierarchy requires GH #292/#293 this run (GH #308 won runs 59-63, 5 consecutive). Included as Bonus A.
- Fix kb-autopopulate.sh as winner — two production bugs take clear priority. Stays in parking lot.

## Questions for Next Run

1. Was GH #292/#293 implemented? (grep `chatbot` in sms_rate_limiter.py — should show `_UNLIMITED_PLANS` containing chatbot)
2. Was GH #308 implemented? (grep `delete_key` in idempotency.py)
3. Was plan-name guard Check 7 added to check_project_invariants.py?
4. Has the leadgen pipeline introduced any new test coverage gaps? (new files: scripts/leadgen/osm.py, merge_leads.py, enrich.py)
5. Is AI-to-Human Handoff (run 4, now 65+ days pending) worth moving to a different track given no movement?
