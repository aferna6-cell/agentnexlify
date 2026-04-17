# Spec — Admin UI for manual managed-agent invocation

**Status:** Draft · 2026-04-11
**Owner:** Aidan
**Related:** 8 managed agents (support_agent, structured_extractor, deep_researcher, field_monitor, data_analyst, lead_qualifier, document_drafter, codebase_reviewer)
**Priority:** P3 (internal tooling, after P1 + P2 ship)

## Problem

The 8 managed agents provisioned 2026-04-10 can be invoked 3 ways today:

1. **Tenant-facing** — widget chat calls `run_support_query` automatically when FALLBACK marker fires.
2. **Router HTTP** — `POST /api/v1/managed-agents/support-query` etc. — no UI, curl-only.
3. **CLI** — `scripts/managed_agents/*_run.py` — require shell access + local Python env.

There's no web UI to run an agent on an ad-hoc question from the dashboard. Aidan wants to:

- Test new agent system prompts against real questions quickly.
- Pull a deep-research brief or data-analysis report without dropping to terminal.
- Show partners/testers what the agents can do without teaching them curl.
- Capture a transcript of the run for later reference.

## Goal

Add an **Admin → Managed Agents** page under the dashboard sidebar (admin-only, gated on `user.role === 'admin'` or a specific `is_super_admin` flag) that lets an authenticated admin:

1. Pick an agent from a dropdown (support / extractor / researcher / monitor / analyst / qualifier / drafter / reviewer)
2. Fill in the required inputs for that agent (varies per agent — driven by a schema)
3. Click **Run** → streams the agent's response in real time (or polls if streaming is hard)
4. See the structured result in a card: `answer`, `confidence`, `escalate_reason`, `duration_ms`, cost estimate
5. Save the run to a local history list (stored in Supabase, not just frontend state)
6. Re-run with the same inputs (useful for regression testing)

## Non-goals

- Multi-user collaborative runs.
- Long-running jobs > 2 minutes (use the CLI runners for those).
- Billing integration — show estimated cost, don't charge.
- Tenant-scoped isolation — this is admin-only, uses the service role key.

## Architecture

### Access control

Gate the page + endpoint on a NEW `is_super_admin` boolean on `users` (or `tenants` — whichever holds admin rights today). Migration 103:

```sql
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS is_super_admin boolean NOT NULL DEFAULT false;

UPDATE tenants SET is_super_admin = true WHERE owner_email = 'aidan@agentnexlify.com';
```

Frontend check via `useAuth()` reading the JWT claim `is_super_admin`. Backend enforces via a new `_require_super_admin(claims)` helper that raises `HTTPException(403)` on fail.

### Agent schemas

Each agent has different inputs. Store as a frontend constant OR (better) expose a `GET /api/v1/managed-agents/schemas` endpoint that returns:

```json
{
  "support_agent": {
    "display_name": "Support Agent",
    "description": "Tenant-grounded customer support answers with KB + FAQ + tools",
    "inputs": [
      {"name": "tenant_id", "type": "tenant_picker", "required": true},
      {"name": "customer_question", "type": "textarea", "required": true},
      {"name": "conversation_id", "type": "text", "required": false}
    ],
    "avg_duration_ms": 4600,
    "avg_cost_usd": 0.045
  },
  "structured_extractor": {
    "display_name": "Structured Extractor",
    "description": "Text → JSON with schema enforcement",
    "inputs": [
      {"name": "tenant_id", "type": "tenant_picker", "required": true},
      {"name": "raw_text", "type": "textarea", "required": true},
      {"name": "target_schema", "type": "select", "options": ["lead", "appointment", "invoice", "contact"], "required": true}
    ],
    "avg_duration_ms": 1200,
    "avg_cost_usd": 0.002
  },
  // ... 6 more
}
```

Backend reads this from `config/managed_agents.yaml` and exposes it. Keeps schemas DRY across backend + frontend.

### Run history

New table `managed_agent_runs`:

```sql
CREATE TABLE managed_agent_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_by_tenant_id uuid REFERENCES tenants(id),
    target_agent text NOT NULL,
    target_tenant_id uuid,             -- if the run targeted another tenant
    inputs jsonb NOT NULL,             -- form field values
    result jsonb,                      -- parsed agent response
    confidence text,
    duration_ms integer,
    cost_usd numeric(10, 4),
    status text NOT NULL DEFAULT 'running',  -- running | success | error | timeout
    error text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_managed_agent_runs_tenant_created
    ON managed_agent_runs(run_by_tenant_id, created_at DESC);
```

Every click of Run inserts a row (status='running'), then updates on completion.

## Files to modify / create

### Backend

1. **`migrations/103_admin_agent_ui.sql`** — new migration (is_super_admin + managed_agent_runs table)
2. **`backend/routers/admin_agents.py`** — NEW router
   - `GET /api/v1/admin/agents/schemas` — list 8 agents + their input schemas
   - `POST /api/v1/admin/agents/run` — invoke agent by name with inputs
   - `GET /api/v1/admin/agents/runs` — list run history for current admin
   - `GET /api/v1/admin/agents/runs/{run_id}` — single run detail
   - All gated on `_require_super_admin`
3. **`backend/services/admin_agents_dispatcher.py`** — NEW service
   - `run_agent_by_name(name, inputs, run_id) -> dict` — delegates to existing service functions based on name
   - Wraps result + timing + cost estimate + writes to `managed_agent_runs`
4. **`backend/main.py`** — register new router
5. **`backend/config.py`** — no changes (env vars already set)

### Frontend

6. **`frontend/src/pages/admin/ManagedAgentsPage.jsx`** — NEW page, dark theme
   - Sidebar link (only shown when `user.is_super_admin === true`)
   - Left panel: agent picker + input form (dynamic from schema)
   - Right panel: run history (most recent 20, paginated)
   - Center: result card with `answer`, `confidence`, `escalate_reason`, `duration_ms`, cost, full JSON toggle, "Run again" button
   - Loading spinner during run, error banner on failure
7. **`frontend/src/utils/api/admin-agents.js`** — NEW API client module (mirrors `frontend/src/utils/api/managed-agents.js`)
8. **`frontend/src/App.jsx`** — route `/admin/managed-agents`
9. **`frontend/src/components/Sidebar.jsx`** — conditional link

### Tests

10. **`backend/tests/test_admin_agents_router.py`** — NEW, ~10 tests
    - `test_unauthenticated_returns_401`
    - `test_non_admin_returns_403`
    - `test_admin_can_list_schemas`
    - `test_admin_can_run_support_agent`
    - `test_admin_can_run_extractor`
    - `test_run_writes_to_managed_agent_runs_table`
    - `test_run_error_writes_error_status`
    - `test_run_history_filtered_by_admin`
    - `test_run_detail_404_on_missing`
    - `test_invalid_agent_name_returns_400`

## Design

Dashboard dark theme (hex `#0b0e13` background, `#00BFFF` accents). Two-column layout:

```
┌──────────────────────────┬──────────────────────────┐
│ Agent: [support_agent ▼] │ Run history              │
│                          │ ┌──────────────────────┐ │
│ Tenant: [MTOptions    ▼] │ │ 2026-04-11 15:32     │ │
│                          │ │ support_agent        │ │
│ Question:                │ │ conf=high · 4.2s     │ │
│ ┌────────────────────┐   │ │ $0.041               │ │
│ │                    │   │ └──────────────────────┘ │
│ │                    │   │ ┌──────────────────────┐ │
│ └────────────────────┘   │ │ 2026-04-11 15:28     │ │
│                          │ │ structured_extractor │ │
│ [Run]                    │ │ conf=- · 1.1s        │ │
│                          │ │ $0.002               │ │
│                          │ └──────────────────────┘ │
├──────────────────────────┴──────────────────────────┤
│ Result                                              │
│ ─────                                               │
│ Answer: "Our hours are 9am-5pm Mon-Fri..."          │
│ Confidence: high                                    │
│ Duration: 4,192 ms                                  │
│ Est. cost: $0.041                                   │
│ [Show full JSON] [Run again]                        │
└─────────────────────────────────────────────────────┘
```

## Security

- Every endpoint gated on `_require_super_admin`.
- Frontend gates sidebar link + route on same flag; backend is the source of truth.
- No tenant impersonation — when running an agent that takes a `tenant_id`, admin picks which tenant to run AGAINST. The `run_by_tenant_id` is always the admin's own tenant (for audit trail).
- All runs written to `managed_agent_runs` with `run_by_tenant_id = admin.tenant_id` and `target_tenant_id = whatever they picked`.
- Rate limit: 30/min per admin (same as public `/extract` limit).
- No secrets in the UI — agent IDs come from backend config, never exposed to frontend.

## Rollout

1. Phase 1: migration + router + dispatcher + tests (backend only, no UI) — can be exercised via curl with admin JWT
2. Phase 2: frontend page (sidebar entry + form + history)
3. Phase 3: flip `is_super_admin = true` for Aidan's own tenant
4. Phase 4: share dashboard URL with partners as a "try it" sandbox

## Verification

```bash
# 1. Backend tests
python3 -m pytest backend/tests/test_admin_agents_router.py -v

# 2. Curl test (with admin JWT)
curl -X POST https://agentnexlify-production.up.railway.app/api/v1/admin/agents/run \
    -H "Authorization: Bearer <admin_jwt>" \
    -H "Content-Type: application/json" \
    -d '{"agent_name": "support_agent", "inputs": {"tenant_id": "<mt>", "customer_question": "What are your hours?"}}'

# 3. Frontend check — open /admin/managed-agents in browser, should see form + history
```

## Risks + mitigations

1. **Service role key exposure** — every agent run hits Supabase via service role. If frontend leaks the admin JWT, attacker can run agents. Mitigation: JWT expires in 24h, rate limit 30/min, all runs logged to `managed_agent_runs`, cost alerts if > $5/hour.
2. **Cost spike from bored admin** — admin clicks Run 100 times on deep_researcher at $0.40/run. Mitigation: rate limit + daily budget alert ($10/day/admin).
3. **Agent drift** — adding a new agent requires both backend schema update AND frontend to re-fetch. Schema endpoint returns whatever's configured, so frontend auto-adapts — no frontend redeploy needed for new agents.
4. **Long-running agent blocks API worker** — deep_researcher can take 30s+. Use `run_in_threadpool` + 60s hard timeout. If timeout hits, status='timeout' on the run row.
5. **Tenant data leak via agent context** — agent runs with full service role. If admin picks tenant A but asks a question that causes the agent to read tenant B's KB, that's a leak. Mitigation: every agent already scopes its Supabase queries by the `tenant_id` passed in. Audit this before shipping — verify no agent service function queries cross-tenant.

## Out of scope

- Scheduling recurring runs (use GitHub Actions cron for that).
- Batch runs (run one agent on 100 inputs). Separate tool.
- Full chat UI / multi-turn conversation with the agent. This is a one-shot form, not a chat.
- Sharing runs between admins.
- Export run history to CSV.

## Delegation model

Opus planned this (file you're reading). **Sonnet executes** in 3 phases:
- Phase 1: backend (router, dispatcher, migration, tests) — ~3hr
- Phase 2: frontend (page, API client, routing, sidebar gate) — ~3hr
- Phase 3: deploy + live smoke with Aidan's real admin JWT — ~1hr

Total estimated: ~7hr Sonnet execution after approval.
