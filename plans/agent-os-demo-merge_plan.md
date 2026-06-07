# Agent OS — Demo-Framework Adoption Plan

**Owner:** Aidan
**Author:** Claude (planning session)
**Date:** 2026-06-06
**Branch:** `claude/gracious-wozniak-QFHoe`
**Status:** Draft for approval. No code changed yet — this is the plan-first artifact.

---

## 0. Decision record (locked this session)

1. **Direction:** The agent framework defined in the standalone demo (`Agent-Nexlify-OS`) becomes the **orchestration core** of the product. The agents do not query tables — they pull from data sources behind provider interfaces.
2. **Backend fate:** The existing **FastAPI + Supabase** backend is **demoted to a data / identity / integrations plane**. It keeps serving the widget, multi-tenant auth, billing, Supabase persistence, and inbound bridges. It does **not** get rewritten in TypeScript.
3. **Widget:** Becomes a **data source** the Agent OS pulls from — `SharedContext.widgetHistory` ← `chat_messages`.
4. **Customers:** None today. Target is **future customers**, so multi-tenancy is a *build requirement before launch*, not a migration. No data-migration, rollback, or classic-view obligations.
5. **What gets replaced:** The current native Python agent layer (`os_thread_runner`, `os_workers/`, `managed_agents_registry`, the Python `orchestrator.orchestrate`). What gets kept: the `os_*` persistence tables/endpoints, widget, auth, billing, inbound bridges, memory/pgvector.

---

## 1. Target architecture

```
                         ┌─────────────────────────────────────────┐
   Embedded widget  ───► │ FastAPI / Supabase  =  DATA + IDENTITY   │
   (customer sites)      │ PLANE                                    │
                         │  • widget chat endpoint  → chat_messages │
   Dashboard (Vite) ───► │  • JWT auth (tenant_id == client_id)     │
        │                │  • Supabase persistence (os_* tables)    │
        │                │  • Stripe billing, inbound bridges       │
        │                │  • READ endpoints for SharedContext      │
        │                │  • WRITE endpoints for run/draft persist │
        ▼                └───────────────▲───────────────┬─────────┘
   /agent-os page                        │ HTTP (scoped  │ persist run,
   (demo chat UX)                        │  by tenant_id)│ draft, trace
        │                                │               ▼
        └──────────► POST /orchestrate ──┴──► ┌──────────────────────────┐
                     (ask, accountId)         │ agent-service (Node)     │
                                              │ = ORCHESTRATION CORE     │
                                              │  demo framework:         │
                                              │   handle() orchestrator  │
                                              │   classify() router      │
                                              │   8 department agents    │
                                              │   anthropic.ts (Haiku/   │
                                              │     Sonnet) + cost log   │
                                              │  providers:              │
                                              │   SharedContextProvider ─┼─► FastAPI reads
                                              │   AuthProvider (passthru)│
                                              │   RunStore (NEW seam) ───┼─► FastAPI writes
                                              └──────────────────────────┘
```

**One account id everywhere.** JWT `tenant_id` = `tenants.id` = `leads.client_id` = `os_*.client_id` = `chat_messages.tenant_id`. FastAPI authenticates and passes the verified id to agent-service per request; agent-service never authenticates and never trusts a body-supplied id.

---

## 2. The seams (contracts)

### 2.1 What the demo already gives us (verified)
- `handle(userId, ask, opts)` → `HandleResult` — `src/agents/_orchestrator.ts:54`. Zero Next.js imports.
- `classify(ask, runId?)` → `Classification` (Haiku + heuristic fallback) — `src/agents/_classifier.ts:196`.
- Agent contract `async ({ input, context, emitTrace, ownerAsk, runId, userId }) => AgentOutput` — `src/types/agent.ts:134`.
- `SharedContext` (the read-only object agents consume) — `src/types/agent.ts:78`.
- `SharedContextProvider` / `AuthProvider` / `OwnerActions` interfaces + setters — `src/lib/providers/*`.
- `anthropic.ts` `complete({purpose, system, prompt, runId})` — portable Node, only couples to Prisma for cost logging.
- 8 department heads: `sales, marketing, customer_service, operations, invoicing, accounting, admin_records, people` (+ internal `lead_triage`) — `src/agents/departments.ts:35`.

### 2.2 The one missing seam — persistence (NEW work)
The orchestrator still writes Prisma inline (`db.agentRun/draft/routingDecision`, `_trace.ts` → `db.traceStep`, `anthropic.ts` → `db.modelCallLog`). Because the **data plane owns the DB**, we extract a `RunStore` interface mirroring the existing provider pattern:

```ts
interface RunStore {
  createRun(accountId, agentId, ownerAsk): Promise<{ runId: string }>
  recordDecision(accountId, decision): Promise<void>          // routing dataset
  emitTraceStep(runId, step): Promise<void>                   // honest-load trace
  saveDraft(runId, draft): Promise<{ draftId: string }>       // deliverable
  logModelCall(runId, usage): Promise<void>                   // cost tracking
  captureWishlist(accountId, ask, candidates): Promise<void>  // no-fit dataset
}
```
Node implementation = thin HTTP calls into FastAPI persistence endpoints, which write `os_agent_runs`, `os_messages`, `os_backlog_requests`, and a cost/routing log table — all `client_id`-scoped in one place. Standalone keeps a `PrismaRunStore` so the demo still runs unchanged.

### 2.3 Provider implementations to write
- **`HttpSharedContextProvider`** (Node) → calls a new FastAPI `GET /api/v1/os/context/{accountId}` that assembles `SharedContext` from `tenants` (businessProfile), `chat_messages` (widgetHistory — **the widget-as-data-source seam**), `leads` (pipeline), `appointments`, `invoices`, `os_agent_runs` (history), KB. Enforces the demo's cold-start caps (widget last 30 days/cap 200; leads cap 100; runs last 14 days).
- **`PassthroughAuthProvider`** (Node) → returns `{ userId: accountId, businessProfileId: accountId }` from the request-scoped id FastAPI already verified. Real auth stays in FastAPI (`auth_service.get_current_tenant`).
- **`HttpOwnerActions`** (Node) → `tagAiVisibilityInterest` → FastAPI flag write.

---

## 3. Phases

Ordered as tracer-bullet-first: prove the full seam end-to-end on **one** agent before porting the other seven.

### Phase 0 — Repo prep (0.5 wk)
- Vendor the demo framework into `agent-service/` (the agent engine is Next.js-free): `src/agents/`, `src/types/agent.ts`, `src/lib/anthropic.ts`, `src/lib/providers/`, `_trace.ts`, `_classifier.ts`, `_registry.ts`, `departments.ts`. Leave Prisma `db.ts` behind.
- Add `RunStore` seam (§2.2) and refactor orchestrator/trace/anthropic to call it instead of `db.*`. Standalone keeps `PrismaRunStore`; verify the standalone still passes its tests (no behavior change).
- **Exit:** demo framework runs inside `agent-service` against in-memory stub providers; standalone repo unchanged in behavior.

### Phase 1 — Tracer bullet: one agent, end-to-end, multi-tenant (1.5 wk)
- Add `agent-service` endpoint `POST /orchestrate { accountId, ask }` (SSE for trace) calling `handle()`.
- FastAPI: new `GET /api/v1/os/context/{accountId}` (HttpSharedContextProvider source) + persistence endpoints behind `RunStore`. Reuse existing `os_agent_runs` / `os_deliverables` approval surface.
- Wire `HttpSharedContextProvider` + `PassthroughAuthProvider` + `HttpRunStore` in agent-service startup.
- Pick **Sales (`sales`)** as the tracer. Drive: dashboard ask → FastAPI (auth, resolve `tenant_id`) → `POST /orchestrate` → agent pulls `SharedContext` (incl. widget history) scoped by `client_id` → produces a draft → persisted to `os_agent_runs` (pending approval) → existing approve/reject flow.
- **Multi-tenancy gate (blocking):** add a test that two accounts never see each other's context or runs. Mirrors the merge-plan §9 "Critical" risk. No further phases until green.
- **Exit:** Sales agent works for ≥2 tenants through the real persistence + approval path; isolation test green.

### Phase 2 — Port the remaining 7 department heads (1.5 wk)
- Bring over `marketing, customer_service, operations, invoicing, accounting, admin_records, people` + `lead_triage`.
- Map each agent's output `channel` to the existing action handlers (`os_actions/{widget,email,sms}.py`) so approved drafts can still send.
- Port the Haiku/heuristic router config; confirm `registry.routable()` lists all 8.
- **Exit:** all 8 routable; routing accuracy spot-checked on a fixture set of owner asks.

### Phase 3 — Frontend swap (1 wk)
- Port demo React components into Vite dashboard, replacing `frontend/src/pages/AgentOS.jsx`: `OrchestratorChat`, `TraceView`, `DraftPanel` (vanilla React — portable per inventory).
- Rewrite Next-specific bits: `IndustryPicker` form-action → `fetch`; cluster-picker industry setup → new account-setup page that supplements the flat 27-option `tenants.business_type`.
- Port `/admin/costs` + `/admin/routing` as React pages reading new FastAPI cost/routing-log endpoints.
- **Exit:** `/agent-os` in the dashboard is the demo UX, talking to the new core.

### Phase 4 — Cut over + deprecate the old Python agent layer (1 wk)
- Route widget + OS thread runs through the new core. Keep `managed_agents` as the documented graceful-degradation fallback when `AGENT_SERVICE_URL` is unset (the pattern already exists in `agent_sdk_client.py`).
- `dead-code-sweep`: retire `os_thread_runner.process_user_turn`, `os_workers/`, Python `orchestrator.orchestrate`, `managed_agents_registry` once the new path is proven. (Separate session per the "don't audit + fix together" rule.)
- **Exit:** demo framework is the only live agent path; old Python agent logic removed; `os_*` tables/endpoints still the persistence layer.

---

## 4. What gets kept vs replaced (precise)

| Keep (data/identity plane) | Replace with demo framework |
|---|---|
| `widget_chat.py` + `chat_messages` (now a data source) | `os_thread_runner.py`, `os_workers/` |
| JWT auth, `tenant_scope.py`, `client_id` discipline | Python `orchestrator.orchestrate` |
| `os_threads/messages/agent_runs/deliverables/memory/backlog/usage` tables + routers | `managed_agents_registry.py` (demote to fallback) |
| Inbound bridges (SMS/email/Facebook), approval gating (`os_auto_send_enabled`) | `frontend/src/pages/AgentOS.jsx` (→ demo chat UX) |
| Stripe billing, leads/invoices/appointments | Flat-only industry field (→ supplemented by cluster picker) |

---

## 5. Risks

| Risk | Sev | Mitigation |
|---|---|---|
| Cross-tenant data leak (agent pulls wrong account's context) | **Critical** | Single id threaded from verified JWT; agent-service never trusts body id; blocking isolation test in Phase 1; all FastAPI reads/writes via `tenant_scope` helpers. |
| `RunStore` extraction destabilizes the demo orchestrator | High | Mirror the existing provider-seam pattern; standalone keeps `PrismaRunStore` + its test suite as the regression guard. |
| Two agent frameworks coexist mid-migration (claude-agent-sdk wrapper vs demo orchestrator) | Med | agent-service hosts both temporarily; widget fallback stays on `managed_agents` until Phase 4 cutover. No half-migration shipped (user rule 8): each phase is independently working. |
| Latency: per-turn HTTP round-trips (dashboard→FastAPI→agent-service→FastAPI reads) | Med | Single `GET /context` assembles SharedContext in one call; cold-start caps; SSE for perceived latency. |
| Demo `anthropic.ts` cost logging assumes Prisma | Low | Routed through `RunStore.logModelCall`; standalone unchanged. |

---

## 6. Open decisions (need Aidan)

1. **agent-service language/runtime:** keep the demo's bespoke orchestrator on `@anthropic-ai/sdk` (recommended — it's the validated framework), and let the existing `claude-agent-sdk` wrapper remain only for the widget fallback? Or converge both onto one SDK later?
2. **Cluster picker vs flat 27-option `business_type`:** supplement (add `industry_cluster` + `business_type` columns, keep the flat field) — recommended — vs replace the flat field outright.
3. **Cost/routing-log storage:** new `os_model_call_log` + `os_routing_decision` tables in Supabase (recommended, keeps admin pages server-backed) vs reuse `os_tenant_usage` only.
4. **Hosting:** agent-service grows in responsibility — stays a single Railway service, or splits orchestrator vs widget-fallback?

---

## 7. First move after approval
Phase 0 + the Phase 1 tracer (Sales agent, 2-tenant isolation test). Everything else waits on that proving the seam. Estimated to first working multi-tenant agent: ~2 weeks.

---

*Grounded in: `Agent-Nexlify-OS/src/agents/_orchestrator.ts`, `_classifier.ts`, `src/lib/providers/*`, `src/types/agent.ts`, `src/lib/anthropic.ts`; `agentnexlify/agent-service/src/{server,runner}.ts`, `backend/services/agent_sdk_client.py`, `backend/routers/os_*.py`, `backend/routers/widget_chat.py`, `backend/services/auth_service.py`, `backend/services/tenant_scope.py`, `migrations/118–130`.*
