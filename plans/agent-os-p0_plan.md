# Agent OS — P0 Foundation Build Plan

Source spec: `specs/agent-os-overhaul_spec.md` (authoritative).
Branch: `claude/agent-os-grill-resume-cHznV` (isolated long-lived; no merge to
`main` until the full OS is done).

P0 is the spine. P1–P4 (workflow agents) and the connectors depend on it, so it
ships first and alone. After P0 lands, P1–P4 + connector groups fan out in
parallel.

## P0 scope

Orchestrator routing, dual-layer memory, chat shell, onboarding hook,
agent-run flowchart, no-fit backlog, usage metering. No workflow agents yet —
P0 proves the orchestrator → agent-run → deliverable → memory loop with a
single stub worker.

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
| `118_os_threads.sql` | `os_threads` + `client_id`/`(client_id,status)` index + RLS |
| `119_os_messages.sql` | `os_messages` + `thread_id` index + RLS |
| `120_agent_runs.sql` | `agent_runs` + `(client_id,status)` index + RLS |
| `121_os_memory_entries.sql` | `os_memory_entries` + pgvector index + RLS (owner-write) |
| `122_os_memory_graph.sql` | `os_memory_nodes` + `os_memory_edges` + RLS (owner-write) |
| `123_backlog_requests.sql` | `backlog_requests` + `(client_id,status)` index + RLS |
| `124_tenant_usage.sql` | `tenant_usage` + `client_id` index + RLS |

All additive. Schema invariants: `client_id` not `tenant_id`; no destructive
changes to existing tables.

## Backend files (new)

- `backend/services/orchestrator.py` — Opus orchestrator: intent classify,
  route to worker, spawn agent runs, no-fit → backlog. Reuse `llm_runtime.py`,
  `advisor_executor.py`, `managed_agents_registry.py`.
- `backend/services/os_memory.py` — dual-layer memory: semantic
  (Voyage `voyage-3-lite` 512d + pgvector) + Karpathy graph
  (`os_memory_nodes`/`os_memory_edges`). Write trigger = auto + explicit
  "remember this". Owner-only edit/delete.
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

- All 7 migrations apply cleanly.
- `/api/v1/os/threads` round-trip: send prompt → orchestrator responds →
  agent_run row created → deliverable approval gate works.
- Memory write (auto + explicit) + semantic retrieval verified.
- No-fit request → `backlog_requests` row + owner email path.
- Usage meter blocks a run when the cap is hit.
- `npm run build` clean.

## After P0

Fan out in parallel: P1 (customer-question agent), P2 (booking), P3
(lead-nurture), P4 (marketing campaign); connector groups A/B/C. Each becomes
its own plan + build agent.
