# Improvement Backlog — 2026-06-21-pm (Run 65)

## Active

- **Combined PR `fix/two-production-bugs`**: Fix GH #308 (idempotency.py delete_key + stripe_webhooks.py exception handler) + Fix GH #292/#293 (chatbot/agent_os in sms_rate_limiter._UNLIMITED_PLANS + api_key_auth._ALLOWED_PLANS + billing_reconciliation._PLAN_AGENT_RUN_CAPS/_PLAN_BASELINE_AI_TOKENS). ~25 lines, 5 files, one PR approval resolves both moratorium-override items.

## Bonus Actions (do alongside or immediately after winner)

- **Bonus B (AUTONOMOUS-EXECUTABLE after combined PR merges):** Add plan-name presence guard Check 7 to check_project_invariants.py — assert chatbot/agent_os in sms_rate_limiter._UNLIMITED_PLANS and api_key_auth._ALLOWED_PLANS. Prevents next repricing from silently drifting.
- **Bonus C (optional research, ~15 min):** Run broader grep for other plan-gating dicts that may also be missing chatbot/agent_os beyond the 3 confirmed files. Scope: `grep -r "growth.*autopilot\|autopilot.*professional" backend/ --include="*.py" | grep -v test`.

## Parking Lot (survived debate but not chosen)

- Fix kb-autopopulate.sh (46-day stale KB, ROI 1.8 — `|| true` fallback or curl fix)
- Add New-Table Checklist to schema-discipline.md (ROI 2.0, prevents _TENANT_COLUMN_OVERRIDES miss)
- Cross-tenant isolation test for os_graph_memory.py (ROI 2.1, 2 tests verifying client_id scope)
- Home.jsx god-class split (1006L — god-class threshold crossed, parked behind active bugs)
- AI-to-Human Handoff v1 (run 4, 66+ days pending — infrastructure exists via os_outbound_mirror.py)

## Rejected This Run

- Fix GH #308 alone — subsumed into combined PR as the primary bug
- Fix GH #292/#293 alone — subsumed into combined PR as the secondary bug
- Post-repricing audit as winner — useful research but lower priority than the active fixes

## Questions for Next Run

1. Was the combined `fix/two-production-bugs` PR opened and merged? (grep `delete_key` in idempotency.py; grep `chatbot` in sms_rate_limiter.py)
2. Was plan-name guard Check 7 added to check_project_invariants.py autonomously?
3. Did the Bonus C broader audit find additional plan-gating dicts missing chatbot/agent_os?
4. Is AI-to-Human Handoff (66+ days pending, run 4) worth a dedicated mechanism change given zero implementation across 65 runs?
5. Does kb-autopopulate.sh need a diagnostic run to identify the actual failure mode before recommending a fix?
