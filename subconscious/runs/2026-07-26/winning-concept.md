# Winning Concept — 2026-07-26 (Run 103)

## Recommendation
File a GitHub issue: **[Managed Agents] Phase 0 kickoff — provision environment, set Railway env vars, run smoke tests**. The rollout plan (`plans/managed-agents-rollout_plan.md`) was created in session ab1a7c2 but Phase 0 has not started. No tracking issue exists. This issue provides the concrete 3-step checklist that starts the Managed Agents product lane.

## Why This, Why Now
The Managed Agents architecture is wired (`backend/services/managed_agents_registry.py` references `MANAGED_AGENTS_ENVIRONMENT_ID`; `managed_agents_registry.py` has `advised_lead_qualifier()`, `advised_document_drafter()`, `advised_codebase_reviewer()` ready). The rollout plan was committed. But all 3 managed-agent run endpoints return 503 because the Anthropic Managed Agents environment has never been provisioned and the Railway env vars are not set. This is a start-the-car problem: 0 lines of new code needed for Phase 0 — only configuration. Every day Phase 0 stays unstarted is a day the product's differentiated AI layer sits at 0 tenants served.

Compared to alternatives: Step 9H (spending limit heartbeat) is the right idea but timing is wrong — it should be added after PR #577 merges. email_sequences auth failures are lower urgency while CI is dark. Keys Koffee silence premise may be wrong (embed may be intentionally removed). Managed Agents Phase 0 is the highest-leverage, unblocked item: no code change, no secrets needed beyond Anthropic console access, clear success criterion (health endpoint returns 200).

## Issue Content (to be created as GH issue)

**Title:** `[Managed Agents] Phase 0: provision environment + Railway env vars + smoke test`

**Body:**
```
## Context
`plans/managed-agents-rollout_plan.md` created 2026-07-23. Phase 0 not started.
All managed-agent run endpoints currently 503.
`managed_agents_registry.py` references `MANAGED_AGENTS_ENVIRONMENT_ID` — env var not set in Railway.

## Phase 0 Checklist
- [ ] 1. Provision Managed Agents environment at platform.anthropic.com → Managed Agents → Create Environment. Note the `MANAGED_AGENTS_ENVIRONMENT_ID`.
- [ ] 2. Identify or create the LEAD_QUALIFIER_AGENT_ID (agent definition already in managed_agents_registry.py). Note the agent ID from the Anthropic console.
- [ ] 3. Set both env vars in Railway:
  - `MANAGED_AGENTS_ENVIRONMENT_ID=<value>`
  - `LEAD_QUALIFIER_AGENT_ID=<value>`
- [ ] 4. Redeploy Railway backend service.
- [ ] 5. Smoke test: `GET /api/managed-agents/health` → should return `{"status": "active", "environment_id": "..."}`.
- [ ] 6. End-to-end test: POST a lead qualification request for one test tenant via `POST /api/managed-agents/qualify-lead` with a sample lead.

## Success Criterion
`GET /api/managed-agents/health` returns HTTP 200 with `status: "active"`.

## References
- `plans/managed-agents-rollout_plan.md` — full rollout plan (Phase 0–3)
- `backend/services/managed_agents_registry.py` — agent registry + advised_*() helpers
- `backend/services/advisor_executor.py` — advisor pattern implementation
- GH #399 — AUTOPILOT_GH_TOKEN (separate, does not block Phase 0)
```

**Labels:** `managed-agents`, `phase-0`, `configuration`, `no-code`

## Implementation Path for Human
1. Open the Anthropic console (platform.anthropic.com).
2. Navigate to Managed Agents → create a new environment for AgentNexLiFy.
3. Copy the environment ID + lead qualifier agent ID.
4. Add both to Railway env vars.
5. Redeploy.
6. Hit the health endpoint.

Estimated time: 15 minutes. No code changes required.

## What This Is NOT
This issue does not implement Phase 1 (tenant opt-in UI), Phase 2 (billing integration), or Phase 3 (analytics). Those follow after Phase 0 proves the environment is live.

## Backlog Items from Debate
- **Step 9H** (GH Actions spending-limit heartbeat in nightly): Park until PR #577 merges. Then add in run 104 or 105.
- **email_sequences 8 auth failures**: File GH issue after GH #500 resolved and CI is green.
- **fastapi<0.136 cap**: Revisit when fastapi 0.136 actually releases on PyPI (not released as of 2026-07-26).
- **Keys Koffee widget**: Verify whether embed is live on their site before filing a diagnostic issue.

## Confidence
**HIGH** — No code change. Issue creation is low-risk. Phase 0 completion unblocks the entire Managed Agents product lane. The code is already wired and waiting.
