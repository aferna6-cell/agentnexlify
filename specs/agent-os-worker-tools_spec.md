# Agent OS — Worker Tool Layer — Spec

**Status:** draft
**Owner:** Aidan
**Created:** 2026-05-25
**Tenant scope:** all
**Priority:** P0.5 (blocks Groups B + C from being meaningful)
**Parent spec:** `specs/agent-os-overhaul_spec.md`

## Problem

Workers in `backend/services/os_workers/` are prompt-shaped: each one is a
single `call_claude_messages` with the user's chat message as input. They
do NOT see:

- `leads` (widget-captured customers)
- `conversations` + `chat_messages` (widget chat history)
- `appointments` (calendar bookings)
- `tenants` profile (business hours, services, owner contact)
- Knowledge base (vertical KB articles, pgvector search)

A booking-reply worker drafts blind to whether the customer ever booked
before, what they asked about in widget chat, or what the owner's business
hours are. The orchestrator sees `os_memory` semantic hits — durable facts
the orchestrator itself has written — but not the underlying widget data.

This came up in conversation 2026-05-25: the partner described Agent OS
as "tenant talks to chatbot, orchestrator spins up an agent with access
to business info + everything the widget connects to." The chat + spawn
half is built. The data-access half is not.

Until workers can read tenant data, Group B (outbound actions — send the
SMS / send the email / book the calendar slot) ships pipes that have no
water. Group C (sync between os_threads and widget conversations) syncs
a thread that has no awareness of the conversation it's syncing with.

## Goals

- Workers get a read-only `WorkerTools` handle on `WorkerContext` that
  exposes typed methods over the data layer the widget already uses.
- Every method is tenant-scoped via `client_id` — no worker can read
  another tenant's data even if the worker is buggy.
- Methods are deterministic Python wrappers around existing Supabase
  queries — workers do NOT get a raw DB cursor.
- Workers opt in per call site — existing 5 workers keep working without
  changes; rewrite is staged worker-by-worker.
- Tool calls are surfaced in `thought_process` so the owner can see what
  the worker looked at before drafting.

## Non-Goals

- Write access from workers. Drafts stay approval-gated. Writes to
  `leads`, `appointments`, etc. are Group B action connectors, not this.
- Tool USE protocol (Claude-side tool calling). Workers stay
  prompt-shaped; the tool layer is Python helpers the worker calls
  before/after the Claude call. No Anthropic tools API surface here.
- New tables. Every method reads existing tables via existing
  `tenant_scope` helpers.
- Cross-tenant analytics or aggregation. One worker = one tenant = one
  read scope.
- KB write/ingest from workers. Read-only against existing pgvector
  index.

## User Stories

- As an **owner**, I ask Agent OS "draft a booking reply for the
  customer who asked about Tuesday" → booking worker reads my widget
  conversation history, finds the Tuesday discussion, drafts a reply
  that references the specific service the customer asked about.
- As an **owner**, I ask "what's the status of leads from this week?"
  → orchestrator routes to a worker that calls
  `tools.recent_leads(days=7)`, summarizes counts by status, and posts
  back without me typing the data into chat.
- As an **owner**, I ask "draft a follow-up for the leads who haven't
  responded in 14 days" → lead_nurture worker calls
  `tools.stale_leads(days=14)`, generates per-lead drafts, returns a
  batch deliverable.
- As an **owner**, the booking worker drafts a reply that mentions my
  actual business hours (read from `tenants` profile), not generic
  "during business hours" filler.
- Edge cases:
  - Worker calls a tool that errors → tool returns empty result + logs
    warning, worker continues with degraded context (caveman fallback
    rather than crash).
  - Worker reads 10k leads → tool enforces `limit ≤ 200` default + 1000
    hard cap. Pagination cursor available for cases that need it.
  - Worker reads KB → pgvector search top-k; never full-table dump.

## Architecture

```
chat message → orchestrator (sees memory) → delegate → run_worker
                                                          │
                                                          ▼
                                                   WorkerContext
                                                     ├─ db (existing)
                                                     ├─ client_id (existing)
                                                     ├─ user_message (existing)
                                                     └─ tools: WorkerTools  ← NEW
                                                                │
                                                                ├─ recent_leads(days, status, limit)
                                                                ├─ lead_by_id(lead_id)
                                                                ├─ widget_conversation(conversation_id)
                                                                ├─ recent_widget_conversations(days, limit)
                                                                ├─ appointments_between(start, end)
                                                                ├─ tenant_profile()
                                                                ├─ kb_search(query, top_k=5)
                                                                └─ stale_leads(days_since_last_touch)
```

All methods return plain dicts or lists of dicts — no ORM objects, no
Supabase response wrappers. Worker passes them into the Claude call as
context strings.

### Reused infra

- `backend/services/tenant_scope.py` — `tenant_table`, `tenant_select`
  — every tool method goes through these for `client_id` enforcement
- `backend/services/os_workers/base.py::WorkerContext` — add
  `tools: "WorkerTools"` field
- `backend/services/kb_embeddings.py` (existing pgvector search) —
  `kb_search` wraps it
- `backend/models/database.py::get_service_supabase` — already injected
  via `WorkerContext.db`

### Net-new code

- `backend/services/os_workers/tools.py` — `WorkerTools` dataclass with
  ~8 read-only methods.
- Updates to `WorkerContext` in `os_workers/base.py` — add tools field.
- Updates to `os_workers/__init__.py::run_worker` — construct
  `WorkerTools(db, client_id)` and pass into `WorkerContext`.
- Rewrite of 3 of 5 workers to use tools (booking, lead_nurture,
  customer_question). Campaign + generalist stay prompt-shaped because
  they don't need data context.

## Data Model

No schema changes. All reads against existing tables:

| Table | Tenant column | Tool methods that read it |
|---|---|---|
| `leads` | `client_id` | `recent_leads`, `lead_by_id`, `stale_leads` |
| `conversations` | `client_id` | `widget_conversation`, `recent_widget_conversations` |
| `chat_messages` | `tenant_id` | `widget_conversation` (joined by conversation_id) |
| `appointments` | `tenant_id` | `appointments_between` |
| `tenants` | `id` | `tenant_profile` |
| `kb_articles` + `kb_embeddings` | `client_id` | `kb_search` |

Schema-discipline reminder per `.claude/rules/schema-discipline.md`:
- `leads.client_id` (NOT tenant_id)
- `conversations.client_id` (NOT tenant_id)
- `chat_messages.tenant_id` (CORRECT — different from leads)
- `appointments.tenant_id` (CORRECT)
- `leads.status` (NOT lead_stage)
- `leads.areas_of_interest` (NOT service_interest)

`tenant_scope` helpers already handle this mapping.

## API Surface

No HTTP routes. `WorkerTools` is a Python class. Workers call it
directly:

```python
async def _run(ctx: WorkerContext) -> WorkerResult:
    ctx.step("Reading recent leads", "Pulling last 7 days for context")
    leads = await ctx.tools.recent_leads(days=7, limit=20)
    ctx.step("Reading tenant profile", "Business hours, services")
    profile = await ctx.tools.tenant_profile()
    response = await call_claude_messages(
        system=_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Recent leads: {leads}\n\nProfile: {profile}\n\nRequest: {ctx.user_message}",
        }],
    )
    return WorkerResult(deliverable={"body": response.text}, summary="Draft ready")
```

### `WorkerTools` method signatures

```python
@dataclass
class WorkerTools:
    db: object       # Supabase client
    client_id: str   # Tenant scope; immutable per worker run

    async def recent_leads(
        self, *, days: int = 30, status: str | None = None, limit: int = 50,
    ) -> list[dict]: ...

    async def lead_by_id(self, lead_id: str) -> dict | None: ...

    async def stale_leads(
        self, *, days_since_last_touch: int = 14, limit: int = 50,
    ) -> list[dict]: ...

    async def widget_conversation(
        self, conversation_id: str, *, message_limit: int = 50,
    ) -> dict | None: ...

    async def recent_widget_conversations(
        self, *, days: int = 7, limit: int = 20,
    ) -> list[dict]: ...

    async def appointments_between(
        self, *, start: str, end: str, limit: int = 100,
    ) -> list[dict]: ...

    async def tenant_profile(self) -> dict: ...

    async def kb_search(self, query: str, *, top_k: int = 5) -> list[dict]: ...
```

Every method:
- Logs the call (operation + client_id + arg summary) for observability
- Caps result count (hard limit ≤ 1000)
- Returns plain JSON-serializable dicts
- Catches exceptions, logs warning, returns empty result (degraded
  rather than crash)

## Security

- **Tenant isolation** — every method goes through `tenant_scope`
  helpers, which enforce `client_id` / `tenant_id` filters at the
  query layer. No raw SQL. No worker-supplied tenant ID.
- **No PII leakage** — methods scope by `WorkerTools.client_id` at
  construction time. Worker code cannot read another tenant by passing
  a different ID; the field is dataclass-immutable.
- **Read-only** — `WorkerTools` exposes no `.insert`, `.update`,
  `.delete`. Writes go through Group B action connectors with
  approval-gating.
- **Result-size caps** — every method has a `limit` arg with a sane
  default and a hard cap (1000). Workers cannot pull entire tables.
- **Logging** — every tool call appends to `WorkerContext.thought` so
  the owner sees what data the worker read before the draft. Audit
  trail for compliance / debugging.
- **KB search redaction** — pgvector hits may include customer-typed
  text; `kb_search` returns only the article body + score, not the
  query log.

## Open Questions

- **Cache layer** — should `tenant_profile` and `kb_search` cache
  within a single worker run (e.g. 5-min memo)? Owner: Aidan. Defer
  until profiling shows cost; first version reads fresh each call.
- **Pagination** — do any workers actually need >200 rows in one call?
  Owner: Aidan. Default `limit=50`, ship without cursor pagination,
  add if a real worker hits the cap.
- **Async vs sync** — Supabase Python client is sync. Wrapping in
  `asyncio.to_thread` for tool methods? Owner: Aidan. Decision:
  initial version stays sync (Supabase client is fast enough); revisit
  if a worker run exceeds 5s.
- **Should orchestrator also get tool access** — could call
  `tools.tenant_profile()` to enrich routing decisions. Owner: Aidan.
  Defer to v2; orchestrator currently routes well enough on memory +
  available-agents list.

## Out-of-Scope (defer)

- Write tools (send_sms, send_email, create_appointment) — Group B
  action connectors handle these; they're approval-gated, not free
  worker-side calls.
- Multi-tenant analytics tools — cross-tenant rollups for the platform
  operator (us), not for worker agents.
- LLM tool-use protocol (Anthropic Messages API `tools` parameter) —
  workers stay prompt-shaped. Tools are Python helpers called before
  the Claude call, not within it.
- Streaming results — every method returns a complete list; no async
  iterators.

## Done criteria

- `WorkerTools` class in `backend/services/os_workers/tools.py` with
  8 methods, each tenant-scoped via existing helpers.
- `WorkerContext` field added; `run_worker` constructs `WorkerTools`
  and passes it in.
- Booking, lead_nurture, customer_question workers rewritten to call
  tools before the Claude `call_claude_messages` step.
- Tool calls appear in `thought_process` for owner visibility.
- Unit tests: each tool method tested for `client_id` enforcement
  (positive: returns own-tenant data; negative: cannot read
  cross-tenant rows).
- End-to-end test: booking worker, given a user message referencing a
  customer name, reads recent leads, includes the matching lead in the
  Claude prompt, drafts a reply that names the customer correctly.
- No regression in existing 5 workers — campaign + generalist stay
  byte-identical (they don't need tools).

## Build order (for the plan doc)

1. `WorkerTools` class + tests (1 file + 1 test file)
2. Wire into `WorkerContext` + `run_worker` (2 file edits)
3. Rewrite booking worker → use `tenant_profile` + `recent_widget_conversations`
4. Rewrite lead_nurture worker → use `stale_leads`
5. Rewrite customer_question worker → use `kb_search`
6. End-to-end smoke test in CI
7. Update docs/dev-knowledge/architecture-decisions.md with the
   prompt-shaped → tool-using worker shift

## Cross-refs

- `specs/agent-os-overhaul_spec.md` — parent spec
- `specs/agent-os-connectors-inbound_spec.md` — Group A (feeds messages
  into os_threads; complementary)
- `plans/agent-os-next-steps_plan.md` — operative connector group split
- `backend/services/os_workers/base.py` — `WorkerContext` lives here
- `backend/services/os_workers/__init__.py::run_worker` — construction
  point for `WorkerTools`
- `backend/services/tenant_scope.py` — enforcement layer
- `.claude/rules/schema-discipline.md` — `client_id` / `tenant_id`
  column-name discipline
- `docs/agent-os-rehaul-partner-brief.md` §8 — DIY vs Managed Agents
  decision; this spec is the DIY path
