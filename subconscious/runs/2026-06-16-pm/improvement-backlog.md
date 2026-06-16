# Improvement Backlog — 2026-06-16-pm (Run 59)

## Active
- Fix `zapier_auth.py::_get_api_key_client` plan_status check — closes revenue leak from 7-day trial system (GH #107, S-effort ~15 min)

## Bonus: Autonomous Tonight
- Check 13 wire (check_project_invariants into pre-commit FAIL gate) — pending_autonomous, expected nightly execution 2:37 AM

## Parking Lot (survived debate but not chosen)
- **AI-to-Human Handoff v1** (customer-gaps.md Critical, all 7 industries) — FIRST post-moratorium customer value win. os_outbound_mirror.py exists (152 tests). Scope ~1 day. Implementation sketch: subconscious/runs/2026-05-28-pm/winning-concept.md. Do not re-recommend as winner until Zapier fix implemented and moratorium exits.
- **check-widget-sync.sh** (runs 7/50, pending_autonomous 55+ days) — Superseded in urgency by Check 13 (widget byte-sync is one of 6 checks in check_project_invariants). Re-evaluate after Check 13 confirms via tomorrow's git log. If nightly doesn't execute Check 13, promote this back.
- **admin_analytics.py unit tests** — Verify test_conversion_funnel.py covers all admin_analytics.py endpoints before creating test_admin_analytics.py. If coverage gap confirmed: create tests (S-effort ~30 min).
- **RequirePaid.jsx multi-PR consistency audit** — 3 billing gate components touched in 3 days. Read all 3, verify consistent plan_status state handling. Low-effort audit, no evidence of active bug.
- **Cross-tenant isolation test for os_graph_memory.py** — ROI 2.1, 284 mock tests exist but no client_id=A cannot see client_id=B test. Deferred to next Agent OS sprint.
- **Add tenant scope checklist to schema-discipline.md** — ROI 2.0, 3rd _TENANT_COLUMN_OVERRIDES miss confirmed. Add 5-question New Table Checklist, path-scoped to backend/**/*.py. S-effort.
- **email_sequences.py god-class split** (1255L, run 35/41) — god-class-splitter SKILL.md ready, post-split-test-repair SKILL.md ready. GH #112/#113 N+1 tracked. Unblock after moratorium exits.
- **Fix kb-autopopulate.sh** (35d+ broken, agent-browser CLI) — replace with curl/WebFetch calls. S-effort.

## Rejected This Run
- **Zapier as "wait for non-moratorium"** — parking lot deferral overridden on time-sensitivity grounds. 7-day trials create active revenue leak; fix is S-effort with exact spec in bug-patterns.md. Governance update: parking lot note amended to "PROMOTED run 59, time-sensitive."

## Questions for Next Run
1. Did Check 13 (check_project_invariants pre-commit) auto-execute tonight at 2:37 AM? (Check git log for `scripts/hooks/pre-commit` modification)
2. Was GH #107 Zapier plan_status fix implemented? (grep `plan_status` in `backend/services/zapier_auth.py`)
3. With Check 13 confirmed: is moratorium now blocking only pending_approval items? What is the true `pending_approval` count?
4. With 7-day trials live + pay_gate active: are there other API surfaces that bypass plan_status (beyond Zapier)?
