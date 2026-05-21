# Agent OS — P0 Foundation Build Plan

Source spec: `specs/agent-os-overhaul_spec.md` (authoritative).
Branch: `claude/agent-os-grill-resume-cHznV` (isolated long-lived; no merge to
`main` until the full OS is done).

P0 is the spine. P1–P4 (workflow agents) and the connectors depend on it, so it
ships first and alone. After P0 lands, P1–P4 + connector groups fan out in
parallel.

## P0 scope

Orchestrator routing, semantic memory, chat shell, agent-run flowchart, no-fit
backlog, usage metering. No workflow agents yet — P0 proves the orchestrator →
agent-run → deliverable → memory loop with a single stub worker.

### Confirmed decisions (2026-05-21)

1. **`os_` prefix on every new table** — `os_threads`, `os_messages`,
   `os_agent_runs`, `os_memory_entries`, `os_backlog_requests`,
   `os_tenant_usage`. Avoids collision with existing `agent_runs`-style names.
2. **Semantic memory only in P0** — the Karpathy graph layer (entity
   pages/edges) is dropped from P0. Rationale: the graph layer is the API-cost
   driver (an LLM call per memory write to update entity pages); the semantic
   layer is cheap (one embedding per write, free pgvector retrieval). The spec
   already marks graph the cut candidate (§Memory architecture, Open Questions).
   Graph layer is re-decided at end of P1.
3. **Migrations written to `migrations/` AND applied via Supabase MCP.**
4. **Async agent runs via FastAPI `BackgroundTasks`** — proves the real
   async post-back path (worker writes status/result back to `os_agent_runs` +
   `os_messages`) that P0 must de-risk. No external queue in P0.

## Build order

1. **Schema** (migrations 118+) — must land before any router.
2. **Backend** — services + routers, registered in `main.py`.
3. **Frontend** — chat shell + side-panel editor + flowchart, against the
   spec's API Surface.

Backend and frontend touch disjoint directories — built concurrently, but
frontend codes against the spec's documented API contract.

## Migrations (next free number: 118)

| File | Table |
|---|---|
| `118_os_threads.sql` | `os_threads` + `(client_id,status)` index + RLS |
| `119_os_messages.sql` | `os_messages` + `thread_id` index + RLS |
| `120_os_agent_runs.sql` | `os_agent_runs` + `(client_id,status)` index + RLS |
| `121_os_memory_entries.sql` | `os_memory_entries` + pgvector index + RLS |
| `122_os_backlog_requests.sql` | `os_backlog_requests` + `(client_id,status)` index + RLS |
| `123_os_tenant_usage.sql` | `os_tenant_usage` + `client_id` index + RLS |

Six migrations (graph-memory migration dropped per decision 2). All additive.
Schema invariants: `client_id` not `tenant_id`; no destructive changes to
existing tables. RLS = `client_id`-scoped on every table; memory edit/delete
and backlog decisions gated to owner role at the app layer (`require_role`).

## Backend files (new)

- `backend/services/orchestrator.py` — Opus orchestrator: intent classify,
  route to worker, spawn agent runs, no-fit → backlog. Reuse `llm_runtime.py`,
  `advisor_executor.py`, `managed_agents_registry.py`.
- `backend/services/os_memory.py` — semantic memory only (decision 2): Voyage
  `voyage-3-lite` 512d embeddings + pgvector top-k retrieval. Reuses
  `backend/services/embeddings.py`. Write trigger = auto + explicit "remember
  this". Owner-only edit/delete enforced in the router via `require_role`.
- `backend/services/usage_meter.py` — per-tenant API spend metering + cap
  enforcement before each agent run.
- `backend/routers/os_threads.py` — thread + message endpoints.
- `backend/routers/os_agent_runs.py` — run status, thought-process, bug report.
- `backend/routers/os_deliverables.py` — approve / reject / edit approval-gated
  drafts.
- `backend/routers/os_memory.py` — memory CRUD (write/delete owner-only) +
  `/remember`.
- `backend/routers/os_backlog.py` — backlog list + owner decision.
- `backend/routers/os_usage.py` — current-cycle usage vs cap.
- Register all routers in `main.py` (lines ~746–813 block).
- No `from __future__ import annotations` in any FastAPI file. Pydantic models
  per endpoint.

## Frontend files (new)

- `frontend/src/pages/AgentOS.jsx` — chat shell, thread list, message stream,
  async agent-result rendering.
- `frontend/src/components/os/DeliverablePanel.jsx` — side-panel doc editor
  for approval-gated drafts (approve / edit / reject).
- `frontend/src/components/os/AgentRunFlowchart.jsx` — agent-run flowchart with
  thought process + "report bug" action.
- `frontend/src/utils/api/os.js` — API client for `/api/v1/os/*`.
- Sidebar entry + `App.jsx` route. Dark theme, live API, empty states.
- No `localStorage` in any component.

## P0 done criteria

- All 6 migrations apply cleanly via Supabase MCP.
- `/api/v1/os/threads` round-trip: send prompt → orchestrator responds →
  `os_agent_runs` row created → stub worker posts deliverable back →
  approval gate works.
- Memory write (auto + explicit) + semantic retrieval verified.
- No-fit request → `os_backlog_requests` row + owner email path.
- Usage meter blocks a run when the cap is hit.
- `npm run build` clean.

## After P0

Fan out in parallel: P1 (customer-question agent), P2 (booking), P3
(lead-nurture), P4 (marketing campaign); connector groups A/B/C. Each becomes
its own plan + build agent.
