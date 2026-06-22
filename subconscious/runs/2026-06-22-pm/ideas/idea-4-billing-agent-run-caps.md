### Idea 4: Resolve billing_reconciliation._PLAN_AGENT_RUN_CAPS Product Decision

**Evidence:**
- `billing_reconciliation.py` line 55: "Agent-run caps for chatbot/agent_os are intentionally
  absent... pending a product decision (GH #293)." Uses `_DEFAULT_AGENT_RUN_CAP = 100` as placeholder.
- GH #293 commit (29ed1d4) addressed token baselines but left run caps deferred.
- `usage_meter.PLAN_AGENT_RUN_CAPS` (referenced in billing_reconciliation header) is the
  enforcement-side dict — discrepancy between enforcement and reconciliation dicts risks
  reporting wrong overages.
- Run 64 proposed: chatbot = 200 agent runs, agent_os = 1500 agent runs (parity-tier defaults).

**Action:**
1. Confirm product decision: what are the monthly agent-run caps for chatbot + agent_os?
2. Add the two entries to `billing_reconciliation._PLAN_AGENT_RUN_CAPS`
3. Verify `usage_meter.PLAN_AGENT_RUN_CAPS` mirrors the same values
4. Remove "pending product decision" comment from billing_reconciliation

**Impact:**
- Accurate overage reporting for all new paid tenants (every signup since 2026-06-16)
- Removes the last known GH #293 remnant
- Requires product decision (not autonomous)

**Category:** code_health
