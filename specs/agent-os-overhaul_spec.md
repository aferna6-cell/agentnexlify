# Agent OS Overhaul — Spec

**Status:** draft
**Owner:** Aidan
**Created:** 2026-05-21
**Tenant scope:** all
**Priority:** P0

Source of truth for every decision below: `specs/agent-os-overhaul_grill-notes.md`
(completed 7-branch grill-me interview, 2026-05-21). This spec converts that
interview into a buildable, phased plan. It adds no new product decisions —
where the interview deferred a call to `write-prd`, the resolution is marked
**[write-prd decision]**.

---

## Problem

AgentNexLiFy today is a dashboard with an embedded chat widget bolted on. A
small-business owner has to learn ~77 pages to get value, and the AI is a
support-desk feature, not the product. Owners want to *tell* the software what
to do ("build me a marketing campaign", "chase my stale leads") and have it
done — not navigate menus. The current shape can't deliver that.

## Goals

- Replace the dashboard-first product with a **chat-first Agent OS**: one
  orchestrator chatbot is the entry point; it delegates to specialist agents.
- Ship **four end-to-end workflows at launch** so the product is worth buying
  on day one: marketing campaign (hero), lead follow-up/nurture, appointment
  booking, customer-question answering.
- Give the orchestrator **persistent cross-conversation memory** of the
  business (facts, preferences, decisions, past conversations).
- Let agents request **connectors in-chat** as work requires them, covering all
  nine launch connectors.
- Capture every request the OS *can't* serve in a **no-fit backlog** routed to
  the owner instead of failing silently or force-fitting an agent.
- Hit **5 paying tenants within 90 days of launch.**

## Non-Goals

- iOS / native mobile app — desktop-first; mobile is "much later".
- A separate SKU for widget-only customers — the widget becomes a feature of
  the OS; existing tenants are migrated in.
- Direct user-to-agent access — the orchestrator is always the entry point.
- Autonomous consequential actions — every email send, post, or purchase
  recommendation is approval-gated to the user.
- Keeping the legacy dashboard — only Leads, Conversations inbox, and Settings
  survive as standalone pages; everything else folds into agent functionality.
- A phased / opt-in tenant migration — migration is big-bang at launch.
- Haiku pre-routing — orchestrator is Opus; Haiku routing is a future cost
  optimization with no UX impact, out of scope here.

## User Stories

- As an **owner**, I sign up, give my website URL, and answer a few onboarding
  questions (in chat, or a wizard fallback) so the OS builds memory of my
  business.
- As an **owner or staff member**, I open a chat, describe a task in plain
  language, and the orchestrator routes it to the right specialist agent.
- As a **user**, I watch agent runs as a flowchart (which agents ran, their
  thought process) and can report a wrong-agent pick as a bug.
- As a **user**, I review every agent deliverable (draft email, social post,
  campaign) in a side-panel editor and approve, edit, or reject before anything
  is sent.
- As a **user**, when an agent needs a connector it doesn't have, it asks me
  in-chat to connect it, then resumes the task.
- As an **owner**, when I ask for something the OS can't do, it tells me
  honestly ("we don't have that capability"), and the request lands in a
  backlog emailed to me.
- As an **owner**, I edit or delete anything in the OS's memory of my business;
  staff can read memory but not change it.
- As a **user**, async agents post their results back into the chat thread
  when finished, ChatGPT-style.
- Edge cases:
  - Tenant with **0 leads / 0 conversations / no website** — onboarding offers
    a barebones site setup; pages show helpful empty states.
  - **Connector revoked mid-task** — agent pauses, surfaces a Settings banner,
    asks the user to reconnect, then resumes.
  - **Usage cap hit** — tenant is told they've reached their plan's API
    allowance; further runs blocked until upgrade or cycle reset.
  - **Agent failure** — user is told it failed, failure is logged with full
    detail, and the report is sent to the owner (Aidan).
  - **Two memory facts contradict** — agent flags the contradiction to the
    owner to resolve.

## Success Metrics

- **5 paying tenants by 90 days post-launch.** Measure: count of tenants on a
  paid plan with `status = active` 90 days after launch date.
- **All existing tenants migrated** with no widget regressions. Measure: widget
  embed smoke test passes for every tenant post-migration.
- **No silent no-fits.** Measure: every request the orchestrator can't route
  produces a `backlog_requests` row + owner email — 100%, audited via logs.
- **Usage cap holds.** Measure: 0 tenants exceed their plan's API allowance
  without being blocked.

## Constraints

- Multi-tenant: every query carries `client_id`.
- Schema invariants: `client_id` not `tenant_id` on `leads` + `conversations`;
  `status` not `lead_stage`; `areas_of_interest` not `service_interest`.
- No `from __future__ import annotations` in FastAPI files.
- Widget JS byte-identical in `widget/` AND `frontend/public/widget/`.
- Plan names: free, growth, autopilot, professional, enterprise.
- Schema changes only via numbered `migrations/NNN_name.sql` — next free number
  is **118** (latest on disk is `117_zapier_api_keys.sql`).
- OAuth tokens stay in the existing `tenant_integrations` table (migration 109)
  — no dedicated vault for v1; tokens encrypted at rest (see Security).
- **Every consequential action is approval-gated** — agents draft, the user
  decides.
- Reuse existing infra; this is an orchestrator layer + interaction-model
  re-conception, not a from-scratch build.

## Architecture

### Interaction model

```
Owner/staff ──chat──▶ Orchestrator (Opus 4.7)
                          │  interprets prompt, routes to best-fit agent(s)
                          ├──▶ Worker agent A (Sonnet 4.6)  ─┐ run async
                          ├──▶ Worker agent B (Sonnet 4.6)  ─┤ post back
                          └──▶ no agent fits ──▶ Backlog ──▶ email to owner
                          │
                       Memory (semantic + graph)  ◀── reads/writes
                          │
Connectors (tenant_integrations) ◀── agents request in-chat as needed
Embedded widget ──▶ widget store ──▶ feeds orchestrator memory
```

- **Orchestrator** = Opus 4.7. Always the entry point. Interprets each prompt,
  classifies intent (LLM classifier), spins up one or more worker agents for
  multi-step requests, holds cross-conversation memory.
- **Worker agents** = Sonnet 4.6. Run async; post results back into the thread
  when done. Roster changes by the tenant's selected business type. Roster kept
  deliberately small — exact agent boundaries are **[write-prd decision:
  deferred to build phase]**, but each of the four launch workflows maps to a
  worker agent (campaign agent, lead-nurture agent, booking agent,
  question-answer agent) plus the backlog handler.
- **No force-fit**: no agent fits → orchestrator says "we don't have that
  capability", writes a `backlog_requests` row, emails the owner. The OS
  **distinguishes** "no agent exists" from "an agent ran and failed" — the
  latter is a bug report, never reported as a missing capability.
- **Approval gates**: any agent output that sends an email, posts to social,
  or recommends a purchase is held for user review in a side-panel editor.

### Reused infrastructure (do not rebuild)

| Need | Reuse |
|---|---|
| Worker agent runtime | `backend/services/managed_agents_registry.py` (~10 Managed Agents incl. lead_qualifier, document_drafter, appointment_booker, support_agent), `managed_agents.py`, `llm_runtime.py` |
| Advisor pattern | `backend/services/advisor_executor.py` |
| Website ingestion | `POST /api/v1/onboarding/{tenant_id}/complete` (crawl → Claude → KB) |
| KB + embeddings | `widget_configs.knowledge_base`, Voyage AI `voyage-3-lite` (512d), pgvector |
| OAuth | `backend/routers/integrations.py` (Google, signed-JWT state), `tenant_integrations` table (migration 109) |
| Connectors | Google Calendar, Facebook (`channels_facebook.py`), Google Business Profile (`gbp.py`), Zapier (`zapier.py`) |
| Widget | `POST /api/v1/widget/chat` (`widget_chat.py`) — kept; widget data feeds memory |

### Surviving pages

Launch surface = **chat** + three standalone pages: **Leads**, **Conversations
inbox**, **Settings**. The orchestrator can render data inline (e.g. "show my
leads" → table in chat) and deep-link to these pages. Every other dashboard
page folds into agent functionality.

### Memory architecture **[write-prd decision]**

Two layers, both reused/extended from existing infra:

1. **Semantic layer** (base) — memory slices (business facts, preferences,
   decisions, conversation summaries) embedded with Voyage AI + stored in
   pgvector. Retrieval = top-k similarity against the current prompt.
2. **Graph layer** (Karpathy LLM-wiki pattern, see
   `knowledge-base/wiki/ai-llm/llm-wiki-karpathy-pattern.md`) — entity pages
   (the business, products/services, key people, connected accounts, recurring
   customers) with typed relationships. Each new source (crawl, conversation,
   explicit "remember this") updates the relevant entity pages. The graph gives
   the orchestrator structured, navigable memory; the semantic layer gives it
   fuzzy recall. **Both ship in v1.** If a simpler design proves sufficient
   during the Phase 1 build, the graph layer is the cut candidate — flag to
   owner before cutting.

- **Write trigger**: dual — orchestrator auto-decides what's important, AND the
  user can explicitly flag "remember this".
- **Edit/delete**: owner only. Staff have read-only memory access.
- **Staleness**: three mechanisms — manual Settings edits, periodic re-crawl,
  agent flags contradictions when it notices them.
- **Widget data**: full customer conversations from the embedded widget are
  stored; the orchestrator pulls from that store when relevant.

### Draft-editing surface **[write-prd decision]**

Agent deliverables (draft emails, posts, campaigns) are reviewed in a
**side-panel document editor**, not chat bubbles. Chat bubbles are poor for
editing multi-paragraph drafts; the side panel gives an editable doc surface
with approve / edit / reject actions that feed the approval gate.

### Cost model

- **Opus orchestrator + Sonnet worker agents.**
- **Monthly subscription with a per-tenant usage cap tied to API spend.**
  Illustrative: a ~$500/mo plan includes ~$100 of API usage (≈5:1 margin).
- Per-tenant API spend is metered; when a tenant's cycle usage hits the cap,
  further agent runs are blocked with an upgrade prompt.

### Build phasing **[write-prd decision]**

Day-1 launch = all four workflows + all nine connectors + backlog + memory.
That is the **launch gate**, not a single deliverable. Build order so each
piece is independently shippable and testable:

| Phase | Deliverable | Rationale |
|---|---|---|
| **P0 — Foundation** | Chat shell, orchestrator routing, memory (semantic + graph), onboarding, agent-run flowchart, backlog flow, usage metering | Nothing else works without the orchestrator + memory spine |
| **P1 — Customer-question answering** | Question-answer worker agent | Lowest new build — leans on existing `support_agent` + KB; proves the orchestrator→agent loop end-to-end |
| **P2 — Appointment booking** | Booking worker agent | Reuses `appointment_booker` + Google Calendar connector |
| **P3 — Lead follow-up / nurture** | Lead-nurture worker agent | Reuses `lead_qualifier`; needs Gmail connector (P-connectors B) |
| **P4 — Marketing campaign (hero)** | Campaign worker agent | Highest new build; needs social connectors (P-connectors C) |

Connector build order, sequenced by OAuth-app cost:

| Connector phase | Connectors | Cost |
|---|---|---|
| **A — Existing** | Google Calendar, Facebook, Google Business Profile, Zapier | Already built — wire into orchestrator |
| **B — Google/Meta-shared** | Gmail (extend existing Google OAuth), Instagram (extend existing Meta/Facebook app via Meta Graph) | Extend existing OAuth apps |
| **C — Net-new OAuth apps** | LinkedIn, X/Twitter, Microsoft (Microsoft Graph → Outlook email + Outlook calendar + Word/Excel + OneDrive) | New OAuth app registration + review per platform |

Launch is gated on all phases complete; the 90-day / 5-tenant goal depends on
this sequencing landing in order, not on a single big-bang code drop.

## Data Model

New tables (numbers from 118; exact names confirmed at build time):

- `os_threads` — one row per task conversation. `client_id`, `title`,
  `created_by`, `status`, timestamps. Separate conversations per task.
- `os_messages` — messages within a thread. `thread_id`, `role`, `content`,
  `agent_run_id` nullable.
- `agent_runs` — one row per delegated agent invocation. `client_id`,
  `thread_id`, `agent_name`, `status` (queued/running/succeeded/failed),
  `thought_process` (JSON, for the flowchart), `error_detail` nullable,
  timestamps. Async — worker writes status back here.
- `os_memory_entries` — semantic memory slices. `client_id`, `kind`
  (fact/preference/decision/conversation_summary), `content`, `embedding`
  (pgvector), `source`, `created_by`, `is_pinned` (explicit "remember this").
- `os_memory_nodes` — graph entity pages. `client_id`, `entity_type`,
  `name`, `summary`, `attributes` (JSON).
- `os_memory_edges` — typed relationships. `client_id`, `from_node`,
  `to_node`, `relation`.
- `backlog_requests` — no-fit requests. `client_id`, `requested_by`,
  `request_text`, `status` (new/emailed/approved/rejected/shipped),
  `created_at`.
- `tenant_usage` — per-tenant API spend per billing cycle. `client_id`,
  `cycle_start`, `api_spend_usd`, `cap_usd`, `blocked_at` nullable.

Reused: `tenant_integrations` (connectors), `widget_configs.knowledge_base`
(KB), `leads`, `conversations`, `tenants`.

- **Indexes**: pgvector index on `os_memory_entries.embedding`; `client_id`
  index on every new table; composite `(client_id, status)` on `agent_runs`
  and `backlog_requests`.
- **RLS**: every new table gets a `client_id`-scoped RLS policy. Memory
  edit/delete additionally gated to the owner role (staff = read-only).
- **Migration safety**: all additive — new tables only, no destructive changes
  to existing columns. Migration order: tables before the routers that query
  them.

## API Surface

New endpoints (FastAPI, registered in `main.py`; auth = tenant session unless
noted):

- `POST /api/v1/os/threads` — create a task thread.
- `GET  /api/v1/os/threads` — list threads for the tenant.
- `POST /api/v1/os/threads/{thread_id}/messages` — send a prompt; returns the
  orchestrator response + any spawned `agent_run` ids.
- `GET  /api/v1/os/threads/{thread_id}/messages` — thread history.
- `GET  /api/v1/os/agent-runs/{run_id}` — run status + thought-process JSON for
  the flowchart.
- `POST /api/v1/os/agent-runs/{run_id}/report-bug` — user flags a wrong-agent
  pick or failure → routes to owner.
- `POST /api/v1/os/deliverables/{run_id}/approve` — approve an approval-gated
  draft (triggers the send/post).
- `POST /api/v1/os/deliverables/{run_id}/reject` — reject a draft.
- `PATCH /api/v1/os/deliverables/{run_id}` — edit a draft in the side panel.
- `GET/POST/PATCH/DELETE /api/v1/os/memory` — read all roles; write/delete
  owner-only.
- `POST /api/v1/os/memory/remember` — explicit "remember this" flag.
- `GET  /api/v1/os/backlog` — owner views the no-fit backlog.
- `POST /api/v1/os/backlog/{id}/decision` — owner approves/rejects a backlog
  item.
- `GET  /api/v1/os/usage` — current-cycle API spend vs cap.
- Connector OAuth callbacks: extend `integrations.py` for Gmail + Instagram;
  net-new callback routes for LinkedIn, X/Twitter, Microsoft Graph.

Pydantic request/response models per endpoint — no `from __future__ import
annotations`. Async agent results post back to `os_messages` / `agent_runs`;
the frontend polls or subscribes for updates.

## Security

- **AuthN/AuthZ**: tenant session for all `/api/v1/os/*`. Memory write/delete,
  backlog decisions, and connector management are **owner-role only**; staff
  are read-only on memory and backlog.
- **Tenant isolation**: every new table is `client_id`-scoped with RLS;
  orchestrator and worker agents pass `client_id` on every query. Memory and
  agent runs never cross tenants.
- **OAuth token storage**: refresh/access tokens stored in `tenant_integrations`
  with **app-level envelope encryption at rest** — data key per token,
  master key from the environment/secret manager. No plaintext tokens in DB,
  logs, or error reports.
- **Approval gates**: no email, social post, or purchase action executes
  without an explicit user approve on the deliverable — enforced server-side,
  not just in the UI.
- **Email sending**: through the user's connected Gmail (OAuth, "from them") —
  every send approval-gated.
- **Connector OAuth**: signed-JWT state on every OAuth flow (existing pattern);
  callback validates state before token exchange.
- **PII**: widget customer conversations stored as memory are tenant-scoped and
  RLS-protected; failure reports sent to the owner must redact OAuth tokens and
  customer PII beyond what's needed to diagnose.
- **Usage cap**: enforced server-side before each agent run — a tenant cannot
  bypass the cap from the client.

## Open Questions

- Worker-agent roster — exact agents and boundaries. Owner: Aidan. Blocks:
  P1–P4 build. Resolved during P0/P1 (interview deferred to Claude's
  discretion; preference = fewer agents).
- Per-tenant usage cap — exact dollar figures per plan tier. Owner: Aidan.
  Blocks: billing wiring. Illustrative ~$500/$100 only; final numbers needed
  before launch.
- Migration mechanics — how the big-bang cutover handles in-flight widget
  conversations and existing dashboard data. Owner: Aidan. Blocks: launch.
- Graph memory — whether the Karpathy layer survives Phase 1 or is cut to
  semantic-only. Owner: Aidan. Decision point: end of P1.

## Out-of-Scope (defer)

- iOS / native mobile app — defer, "much later".
- Haiku pre-routing cost optimization — defer; future internal lever.
- Dedicated token vault — defer; `tenant_integrations` + envelope encryption
  is the v1 answer.
- Any dashboard page beyond Leads / Conversations inbox / Settings — folded
  into agent functionality, not rebuilt.
- Connectors beyond the nine launch connectors — new connectors arrive via the
  backlog flow post-launch.
