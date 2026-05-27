# Agent OS — Connector Group C: Data Sync — Spec

**Status:** draft
**Owner:** Aidan
**Created:** 2026-05-25
**Tenant scope:** all
**Priority:** P5 (post-P0/P1-P4 launch gate)
**Parent spec:** `specs/agent-os-overhaul_spec.md`

## Problem

The orchestrator's memory (`os_memory_entries`) is empty when a tenant
signs up. Today the only ways to fill it are:
1. The owner manually types "remember this" into the chat.
2. The orchestrator extracts a slice from a conversation in-flight.

Meanwhile the tenant already has rich, structured data: leads, appointments,
KB articles, calendar events, past widget conversations. None of it
auto-flows into `os_memory_entries`, so the orchestrator answers "do you
have any open leads?" with "I don't have that information" even though the
`leads` table has 200 rows.

Data sync bridges the existing tenant data into the OS's semantic memory so
the orchestrator can answer factual questions about the tenant's own
business without re-asking the owner every time.

## Goals

- Each tenant has a one-time backfill: leads, appointments, KB articles,
  past conversations → `os_memory_entries` slices.
- Each data source has an ongoing sync (incremental, on change) so memory
  stays current without re-syncing the world.
- Sync respects owner control — owner toggles each source on/off; off =
  existing slices stay, no new ones added.
- Sync never blocks user-facing work — runs as `BackgroundTasks` or a
  scheduled job (`backend/services/automation/scheduled_jobs.py`).
- Slices land in `os_memory_entries` with `source` populated
  (`leads_table`, `appointments_table`, `kb_articles`, `widget_conversations`,
  `google_calendar`) so the orchestrator can cite where memory came from.

## Non-Goals

- Real-time push from data sources — incremental sync runs on a
  per-tenant schedule (default 15 min) plus event triggers where cheap.
- Graph-memory layer — semantic only per
  `planning/decisions/2026-05-25-agent-os-graph-memory.md`.
- Cross-tenant data movement — every sync job is `client_id`-scoped.
- Building a new ingestion UI — owner controls live in Settings → Memory.

## User Stories

- As an **owner**, I sign up; within 5 minutes my orchestrator can answer
  "how many leads do I have?" and "when's my next appointment?" without
  me typing anything in.
- As an **owner**, I add a new KB article; orchestrator picks it up on
  next sync (<= 15 min); follow-up question gets the new info.
- As an **owner**, I delete a lead; orchestrator no longer references
  that lead's name in suggestions (memory slice purged within one sync).
- As an **owner**, I toggle "Sync leads" off in Settings; existing
  lead-derived slices stay (owner can purge them via memory CRUD);
  no new lead changes flow.
- Edge cases:
  - 10k-lead tenant signing up → backfill batches to avoid Voyage rate
    limits + Sonnet billing spike; status surfaces in Settings.
  - Widget conversation already summarized into a slice — incremental
    sync recognizes the slice by `source_ref` and skips.
  - Lead PII (email, phone) — slices keep names + summary fields, drop
    raw contact details unless owner explicitly opts in.

## Architecture

```
Scheduled trigger (every 15 min, per-tenant)
   │
   ▼
os_sync_runner.run_due_jobs()
   │
   ├─ leads_sync(client_id) ─────► writes os_memory_entries (kind=fact)
   ├─ appointments_sync(client_id) ► writes os_memory_entries (kind=fact)
   ├─ kb_sync(client_id) ──────────► writes os_memory_entries (kind=preference)
   ├─ widget_conversations_sync(client_id) ► writes os_memory_entries (kind=conversation_summary)
   └─ google_calendar_sync(client_id) ► writes os_memory_entries (kind=fact)
       (only if google_calendar connector connected)
```

### Sync modules (launch set)

| Source | Module | Reads from | Slice kind | Cadence |
|---|---|---|---|---|
| Leads | `os_sync/leads.py` | `leads` table (client_id-scoped) | `fact` | 15 min + on lead create/update |
| Appointments | `os_sync/appointments.py` | `appointments` table (tenant_id-scoped) | `fact` | 15 min + on appointment create/update |
| KB articles | `os_sync/kb.py` | `widget_configs.knowledge_base` JSON | `preference` | 15 min |
| Widget conversations | `os_sync/conversations.py` | `conversations` + `chat_messages` | `conversation_summary` | 15 min, summarize closed conversations |
| Google Calendar events | `os_sync/google_calendar.py` | Google Calendar API (existing `google_calendar.py`) | `fact` | 15 min if connector connected |

Each sync module exposes:
```python
SPEC = SyncSpec(
    name="leads",
    handler=run,        # async (ctx, client_id) -> SyncResult
    requires_connector=None,        # or "google_calendar"
    incremental_key="updated_at",   # which column to track since-last-run
)
```

### Registry

`backend/services/os_sync/__init__.py` — auto-discovers every module,
collects `SPEC`. Mirrors `os_workers/__init__.py` + the
`os_actions/__init__.py` pattern from Group B.

### Scheduler integration

`backend/services/automation/scheduled_jobs.py` already runs periodic
tasks. Add one job: `os_sync_tick` — per-tenant scan of `os_sync_state`,
runs due jobs.

### Slice writing

Each sync uses `backend/services/os_memory.py::write_memory()` (existing).
Slice `content` is a short summary string:
- Lead: `"Lead Sarah Johnson (status: new, source: widget, areas: roofing). Last contact 2026-05-23."`
- Appointment: `"Appointment with Mike Smith 2026-05-30 14:00 for roof inspection. Status: confirmed."`
- KB: `"KB article: 'Pricing for repair vs replacement'. Summary: ..."`
- Conversation: `"Widget conversation closed 2026-05-22 with John Doe. Topic: warranty question. Outcome: referred to support email."`

Slice `source_ref` (new field — see Data Model) points back to the source
row so incremental sync can detect changes + purge on delete.

## Data Model

One new migration (next free number = 126 at build time; verify):

- `126_os_sync_state.sql` — new table tracking per-tenant per-source
  sync state:
  - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `client_id UUID NOT NULL`
  - `source TEXT NOT NULL` — `leads | appointments | kb | conversations | google_calendar`
  - `enabled BOOLEAN NOT NULL DEFAULT true`
  - `last_run_at TIMESTAMPTZ`
  - `last_seen_cursor TEXT` — incremental marker (max `updated_at`,
    or KB checksum, or calendar `syncToken`)
  - `status TEXT NOT NULL DEFAULT 'idle'` — `idle | running | error`
  - `last_error TEXT NULL`
  - UNIQUE `(client_id, source)`
  - INDEX `(status, last_run_at)` for scheduler scans
  - RLS deny-public

ALTERs on existing tables:

- `os_memory_entries`:
  - `source_ref TEXT NULL` — pointer to source row identity (e.g.
    `leads:uuid`, `appointments:uuid`, `kb:article_id`, `conversation:uuid`,
    `gcal:event_id`). NULL for owner-typed memory.
  - UNIQUE `(client_id, source_ref) WHERE source_ref IS NOT NULL` —
    incremental dedup + purge anchor.

## API Surface

- `GET /api/v1/os/sync/status` — returns per-source state for current
  tenant (last_run_at, status, error, slice count). Powers Settings UI.
- `POST /api/v1/os/sync/{source}/toggle` — owner-only; flips `enabled`.
- `POST /api/v1/os/sync/{source}/run-now` — owner-only; force-runs the
  sync for that source. Useful for backfill or after schema repair.
- `POST /api/v1/os/sync/{source}/purge` — owner-only; deletes all slices
  with `source = '<source>'` for this tenant. Two-step confirm in UI.

Pydantic models per endpoint; no `from __future__ import annotations`.

## Security

- **Tenant isolation** — every sync handler reads only via
  `tenant_select(db, "<table>", client_id, ...)` (existing helper at
  `backend/services/tenant_scope.py`).
- **Owner-only sync controls** — toggle, run-now, purge all gated by
  `require_role("owner")`. Reads (`/status`) available to staff.
- **PII handling** — lead/appointment slices keep names + status +
  business-relevant fields; raw email/phone are stored in
  `source_metadata` JSONB (RLS-protected) and never embedded into the
  slice `content` text (which goes into the embedding). Owner opts in
  per source for full-PII embedding.
- **Backfill rate limits** — initial backfill batches Voyage embedding
  calls (50 per batch, 1s pause between batches) to avoid rate limits
  and Sonnet billing spikes.
- **Sync run isolation** — one sync runs per (client_id, source) at a
  time; lock via `os_sync_state.status='running'` row update; expired
  locks (last_run_at > 10 min ago + status='running') reclaimed by
  scheduler.
- **Usage meter** — Voyage embedding calls count against per-tenant API
  spend cap (cheap, but counted). When cap hit, sync pauses; resumes
  next cycle.

## Open Questions

- Conversation summarization cost — each closed widget conversation =
  one Sonnet call to summarize. At 50 conversations/day/tenant that's
  ~50 cents/tenant/day. Owner: Aidan. Decision: cap conversations
  summarized per day at 100; queue overflow.
- KB chunking — long KB articles split into multiple slices, or one
  slice per article with a longer content field? Voyage `voyage-3-lite`
  handles up to 32k tokens but retrieval quality degrades on huge
  chunks. Decision: split at ~500 tokens per chunk, mark
  `source_ref=kb:<article_id>:<chunk_n>`.
- Past data cutoff — backfill all-time vs last 90 days? Owner: Aidan.
  Default: last 180 days for conversations/appointments, all-time for
  leads + KB.
- Calendar sync push — Google Calendar push notifications would beat
  polling but require a public webhook URL + cert. Defer to v2; v1 is
  15 min poll.

## Out-of-Scope (defer)

- Cross-tenant memory dedup — every tenant's memory is its own silo.
- Outbound sync (writing memory back to source-of-truth tables) — memory
  is read-only with respect to leads/appointments/KB. Owner edits in
  source tools; sync picks up changes.
- LinkedIn/X/Microsoft Graph sources — overhaul spec §Connector phase C.
- Sync from non-tenant data (web crawl, public datasets) — separate
  workflow (re-crawl already exists for KB).

## Done criteria

- `os_sync_state` migration applied; `os_memory_entries.source_ref`
  ALTER applied.
- 5 sync modules auto-discovered by `os_sync/__init__.py`.
- New tenant signup → leads + appointments + KB backfill completes
  within 5 minutes; orchestrator can answer "how many leads do I have?"
  with the correct count after.
- 15-min incremental sync picks up a new lead within one cycle.
- Lead delete → slice purged within one cycle (verify
  `source_ref` cleanup).
- Settings → Memory shows per-source status + toggles; owner can pause
  + resume + purge per source.
- Backfill rate-limit test: 1000-lead tenant backfills without
  exceeding Voyage rate cap; no orchestrator slowdown.

## Cross-refs

- `specs/agent-os-overhaul_spec.md` — parent spec; §Memory architecture
- `plans/agent-os-next-steps_plan.md` §1 — operative connector grouping
- `planning/decisions/2026-05-25-agent-os-graph-memory.md` — semantic-only
  decision that scopes this spec
- `backend/services/os_memory.py` — `write_memory()` used by every sync
- `backend/services/tenant_scope.py` — `tenant_select` for read-only sync
- `backend/services/automation/scheduled_jobs.py` — scheduler integration
- `backend/services/embeddings.py` — Voyage `voyage-3-lite` 512d
