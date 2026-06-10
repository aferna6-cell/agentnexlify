# Improvement Backlog — 2026-06-09-pm (Run 53)

## Active
- **Write `backend/tests/test_os_action_dispatch.py`** — 5 mock-based tests for `queue_action_for_run()`, AUTONOMOUS-EXECUTABLE, labeled for tonight's nightly (run 53)

## Parking Lot (survived debate but not chosen)

| Title | ROI | Notes |
|-------|-----|-------|
| Fix kb-autopopulate agent-browser dependency | 2.0 | 35-day stale KB. Script calls agent-browser CLI which isn't installed. Fix: graceful skip + compile-only fallback. Human or directed nightly task. |
| Integration health probe `GET /api/widget/{client_id}/health` | 2.0 | GH #215. Anti-churn — surfaces silent widget failures at onboarding. Low effort. |
| WordPress plugin spec (GH #214) | 1.8 | Evidence thin (24h old issue). Valid distribution moat. Revisit if user prioritizes. |
| Activity log emission for 4 automations (GH #213) | 1.7 | Dashboard parity gap. Customers can't see what the AI is doing. Medium effort. |
| email_sequences.py god-class split (runs 35/41) | 1.9 | Still 1255L. Blocked on PR #183 merge (GH #181 billing). |
| Zapier API key plan_status enforcement (GH #107) | 2.5 | Security: cancelled tenants bypass tier gate. Route via issue-to-pr-loop. |

## Rejected This Run
- **WordPress plugin spec** — KILLED. Evidence thin (24h-old issue). Production correctness gap higher priority. Moratorium discourages new-feature specs. Parking lot ROI 1.8.

## Questions for Next Run
1. **kb-autopopulate:** Is `scripts/daily/kb-autopopulate.sh` trying to call agent-browser CLI? If so, what's the minimal fallback patch to restore compile-only operation?
2. **Test gap audit:** After `test_os_action_dispatch.py` lands, which other new Phase 4 services (os_graph_memory.py has 284 test lines ✓; os_thread_runner.py has 14 tests — enough?) need coverage?
3. **Moratorium exit path:** PR merges #209+#200+#183 (~20 min human) would unblock Items A+B + billing fix + email split. Moratorium exit requires pending_approval ≤ 2. What's the current true pending_approval count after governance corrections this run?
