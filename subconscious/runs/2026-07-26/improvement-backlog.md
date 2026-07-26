# Improvement Backlog — Run 103 (2026-07-26)

## Active (winner, pending human approval)
- **Managed Agents Phase 0 GH issue** — provision environment, set Railway env vars, run smoke tests. 15-min configuration task, no code change. Unblocks entire Managed Agents product lane. (Winner: run 103)

## Parking Lot (conditions not yet met)
- **Step 9H — GH Actions spending-limit heartbeat**: Add to nightly SKILL.md after PR #577 merges. Fires when no successful GH run in 7+ days. Comments on GH #500 with elapsed days + opportunity cost. Condition: wait for PR #577 to merge before adding more SKILL.md steps. (Debated run 103 — parked on timing)
- **email_sequences 8 auth failures**: File classification GH issue. Condition: wait until GH #500 resolved and CI is green; failures are pre-existing and non-blocking while CI is dark. (Debated run 103)
- **Keys Koffee widget diagnostic**: Verify embed is still on their site before filing. Could be intentionally removed. (Eliminated run 103 — premise uncertain)
- **LoopHealthPage.jsx** — dashboard page showing autopilot loop, issue-to-pr-loop, and KB autopopulate status in real-time. Promote when Agent OS >5 tenants. (Parking lot from run 100)
- **Owner MCP quickstart** — document how to add a tenant to the MCP endpoint. Promote when 3+ MCP tenants activated. (Parking lot from run 100)
- **fastapi<0.136 cap removal** — check when fastapi 0.136 actually releases on PyPI; cap may be precautionary. (Parking lot from run 103)

## Rejected (do not re-propose)
- MCP adoption monitoring Step 9H — evidence too thin (1 tenant), auth mechanism inadequate. (Run 100)
- os_opportunities referral_activation rule — mechanism mismatch (env-var vs DB column). (Run 102)
- GH #181 Fix AMOUNT_TO_PLAN — recommendation loop exhausted. (Run 101)
- ai_human_handoff feature — frozen. (Governance)
