# Claude Managed Agents — AgentNexLiFy Integration

This doc covers how AgentNexLiFy uses Anthropic's **Claude Managed Agents**
(beta, `managed-agents-2026-04-01`) — the server-managed agent runtime where
Anthropic provisions a per-session container, runs the agent loop on their
orchestration layer, and streams events back to us.

If you are setting up Managed Agents for the first time on this repo, read
the **Setup** section end-to-end. If you already have agents provisioned and
want to call one from the backend, jump to **Using an agent from code**.

---

## Why

The existing `backend/services/llm_runtime.py` calls Claude through the
stateless `/v1/messages` endpoint. That is the right tool for:

- Widget chat replies
- Quick classification / extraction
- Anything where the whole task fits in a single request/response

Managed Agents is the right tool when we want:

- **Long, stateful runs** — research, multi-step planning, code review
- **Anthropic-hosted tool execution** — bash, file edits, code execution
  without us running a sandbox
- **Pre-built skills** — DOCX / XLSX / PDF generation via
  `skills: [{type: "anthropic", skill_id: "xlsx"}]`
- **Versioned configs** — the agent persona/tools/prompt live as a stored
  object we can update + pin per session

The trade-off is latency (minutes, not seconds) and cost (a session's
worth of tool calls). Use it for the cases where that is justified.

---

## Architecture

```
┌─ config/managed_agents.yaml ─┐   ┌─ scripts/managed_agents/ ──────┐
│  Declarative agent + env      │──▶│ provision.py  (one-time setup)│
│  definitions (checked in)     │   │ review_branch.py (dev runner) │
└───────────────────────────────┘   └──────────┬────────────────────┘
                                               │ reads/writes
                                               ▼
                          .env.managed_agents (NOT committed)
                                               │
                                               ▼
┌─ backend/config.py ─────────────┐   ┌─ backend/services/ ────────────────┐
│  Settings(...AGENT_ID fields)   │──▶│ managed_agents.py (httpx client)   │
│  BaseSettings reads .env        │   │ managed_agents_registry.py (typed) │
│  AND .env.managed_agents        │   └──────────┬─────────────────────────┘
└─────────────────────────────────┘              │
                                                 ▼
                                   ┌─ backend/routers/managed_agent_runs.py ─┐
                                   │  POST /api/v1/managed-agents/{tid}/...  │
                                   │  GET  /api/v1/managed-agents/{tid}/...  │
                                   └─────────────────────────────────────────┘

                  Anthropic API (api.anthropic.com)
                  POST /v1/agents       → persistent, versioned
                  POST /v1/environments → shared, reusable
                  POST /v1/sessions     → per run
                  GET  /v1/sessions/{id}/events/stream  (SSE)
                  POST /v1/sessions/{id}/events         (send user.*)
```

The **mandatory flow** is: Agent (created once) → Session (created every
run). `model`, `system`, `tools`, `mcp_servers`, `skills` all live on the
agent object — never on the session. `sessions.create()` only takes a
pointer (`agent="agent_abc123"` or `{type: "agent", id, version}`).

We **never call `create_agent()` in the request path**. Agents are
provisioned once by `scripts/managed_agents/provision.py`, the returned IDs
are persisted to `.env.managed_agents`, and the backend reads them at
startup.

---

## Setup

### 1. Prerequisites

- `ANTHROPIC_API_KEY` set in `.env` with an API key from an org that has
  Managed Agents beta access.
- Python 3.11+ with `httpx` and `pyyaml` (both already pinned in
  `backend/requirements.txt`).

### 2. Edit the YAML

Open `config/managed_agents.yaml` and customize:

- `environment.name` — needs to be unique per org. The default
  (`agentnexlify-shared`) is fine.
- `environment.networking` — `unrestricted` for full egress, or
  `package_managers_and_custom` with an `allowed_hosts` list if you want
  to lock the sandbox down.
- `agents.<slug>.system` — the system prompt. Iterate on this during setup
  and re-run `provision.py` each time; every update bumps the agent's
  version so running sessions are unaffected.
- `agents.<slug>.tools` / `.skills` / `.mcp_servers` — attach whatever
  capabilities the agent needs. See **Tools & Skills** below.

### 3. Dry-run the provisioner

```bash
python -m scripts.managed_agents.provision --dry-run
```

This will list existing environments and agents without mutating anything.
Expect output like:

```
[dry-run] would create environment name=agentnexlify-shared
[dry-run] would create agent lead_qualifier
[dry-run] would create agent document_drafter
[dry-run] would create agent codebase_reviewer
```

### 4. Provision for real

```bash
python -m scripts.managed_agents.provision
```

The script:

1. Creates the environment if it doesn't exist (looked up by name).
2. For each agent in the YAML:
   - If `.env.managed_agents` already has a matching `*_AGENT_ID`, it
     calls `POST /v1/agents/{id}` to update in place (new version).
   - Otherwise it looks up by name in `list_agents()`.
   - Otherwise it calls `POST /v1/agents` to create a fresh one.
3. Writes all IDs to `.env.managed_agents` (gitignored).

It's **idempotent** — run it again after editing the YAML to roll out
prompt/tool changes. Use `--recreate lead_qualifier` to archive the
existing agent and build a fresh one from scratch.

### 5. Deploy env vars to Railway / Vercel

`.env.managed_agents` is local-only. For production, copy the IDs it
generates into your Railway backend environment variables:

```
MANAGED_AGENTS_ENVIRONMENT_ID=env_...
LEAD_QUALIFIER_AGENT_ID=agent_...
DOCUMENT_DRAFTER_AGENT_ID=agent_...
CODEBASE_REVIEWER_AGENT_ID=agent_...
```

The backend's `Settings` class loads both `.env` and `.env.managed_agents`,
and the `extra: "ignore"` policy means Railway's bare env vars work the
same way.

### 6. Verify

```bash
python3 -m pytest backend/tests/test_managed_agents.py -v
```

49 tests should pass (as of 2026-04-10 — 32 service + registry, 17
router HTTP). They exercise the client, error mapping, SSE parsing,
the registry, the tenant-facing services, and the new `/support-query`
`/extract` endpoints in isolation — no live API calls.

#### Live smoke tests (hit real Anthropic API)

Each smoke script creates a real session, streams events, and asserts
the session_id contract. Run with your `ANTHROPIC_API_KEY` in the
environment. Approximate cost per run:

| Script | Agent | Model | ~Cost | Notes |
|---|---|---|---|---|
| `session_smoke` | lead_qualifier | Sonnet | $0.05 | pre-existing |
| `drafter_smoke` | document_drafter | Opus | $0.30 | pre-existing |
| `support_smoke` | support_agent | Sonnet | $0.05 | new 2026-04-10 |
| `extractor_smoke` | structured_extractor | Haiku | $0.01 | new 2026-04-10 |
| `researcher_smoke` | deep_researcher | Opus | $0.30-1.00 | new 2026-04-10 |
| `field_monitor_smoke` | field_monitor | Sonnet | $0.10-0.40 | new 2026-04-10 |
| `analyst_smoke` | data_analyst | Opus | $0.20-0.60 | new 2026-04-10 |

```bash
set -a && source .env && source .env.managed_agents && set +a

python3 -m scripts.managed_agents.support_smoke
python3 -m scripts.managed_agents.extractor_smoke
python3 -m scripts.managed_agents.researcher_smoke
python3 -m scripts.managed_agents.field_monitor_smoke
python3 -m scripts.managed_agents.analyst_smoke
```

Total for all 5 new smokes: ~$1-3 per full pass.

#### Production health check

After Railway picks up the new env vars, hit the health endpoint from
your dashboard to confirm all 8 agents register:

```bash
export JWT="<dashboard JWT from a valid tenant session>"
export TENANT_ID="<your tenant UUID>"

curl -s -H "Authorization: Bearer $JWT" \
     "https://agentnexlify-production.up.railway.app/api/v1/managed-agents/$TENANT_ID/health" \
     | python3 -m json.tool
```

Expected response shape:

```json
{
  "environment_id": "env_019YgeAySxkW8BsXaFGvXJ3j",
  "lead_qualifier":       true,
  "document_drafter":     true,
  "codebase_reviewer":    true,
  "support_agent":        true,
  "structured_extractor": true,
  "deep_researcher":      true,
  "field_monitor":        true,
  "data_analyst":         true
}
```

If any agent is `false`, the corresponding `*_AGENT_ID` env var is
missing from Railway production. Re-sync with:

```bash
railway variables set --service agentnexlify \
    SUPPORT_AGENT_ID=<id> \
    STRUCTURED_EXTRACTOR_AGENT_ID=<id> \
    DEEP_RESEARCHER_AGENT_ID=<id> \
    FIELD_MONITOR_AGENT_ID=<id> \
    DATA_ANALYST_AGENT_ID=<id>
```

#### Live endpoint smoke tests

Once health returns all-true, verify the 2 new tenant-facing routes
with real traffic:

```bash
# Support query (tenant-scoped, KB-grounded)
curl -s -X POST \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"question": "What are your hours?"}' \
     "https://agentnexlify-production.up.railway.app/api/v1/managed-agents/$TENANT_ID/support-query"

# Structured extraction (text → typed JSON)
curl -s -X POST \
     -H "Authorization: Bearer $JWT" \
     -H "Content-Type: application/json" \
     -d '{"raw_text": "Hi Im Maria, 973-555-0134, want a pressure wash", "target_schema": "lead"}' \
     "https://agentnexlify-production.up.railway.app/api/v1/managed-agents/$TENANT_ID/extract"
```

---

## Using an agent from code

### From a FastAPI route (backend)

```python
from backend.services.managed_agents import ManagedAgentsClient
from backend.services.managed_agents_registry import lead_qualifier

handle = lead_qualifier()              # raises ManagedAgentNotConfigured if unset
client = ManagedAgentsClient()

session = client.create_session(
    agent_id=handle.agent_id,
    environment_id=handle.environment_id,
    title="lead-qualify inbound",
    metadata={"tenant_id": tenant_id},
)

# Stream-first: open the stream before sending the first user message.
stream = client.stream_events(session["id"])
client.send_user_message(session["id"], "Qualify this lead: ...")

for event in stream:
    if event["type"] == "agent.message":
        # Accumulate the assistant's text blocks and send them back to your caller
        ...
    if event["type"] == "session.status_terminated":
        break
    if event["type"] == "session.status_idle":
        stop = event.get("stop_reason") or {}
        if stop.get("type") != "requires_action":
            break
```

The Managed Agents client is **blocking** (sync httpx). In FastAPI
routes, wrap the streaming loop in `fastapi.concurrency.run_in_threadpool`
so you don't block the event loop — see
`backend/routers/managed_agent_runs.py` for a full example.

**Never** break on bare `session.status_idle` — that event fires
transiently whenever the agent is waiting on a user tool confirmation or a
custom-tool result. The correct break gate is:

> `status_terminated` OR (`status_idle` AND `stop_reason.type != "requires_action"`)

### Document drafter (quotes / invoices / proposals)

The `document_drafter` agent produces real DOCX / XLSX / PDF files via
Anthropic's pre-built skills. Wire-up lives in
`backend/services/document_drafting.py` and is exposed at:

```
POST /api/v1/managed-agents/{tenant_id}/draft-document
GET  /api/v1/managed-agents/{tenant_id}/documents/{document_id}/download
```

The POST endpoint runs the agent, the GET endpoint streams the file.
**V1 stores bytes inline** — `document_drafting.py` decodes the agent's
`content_base64` reply, persists it in `documents.file_bytes`, and the
download endpoint streams those stored bytes directly. `anthropic_file_id`
is retained as optional debugging metadata rather than the source of truth.

### Preflight + smoke workflow

For a safe, no-cost local verification pass:

```bash
python -m scripts.managed_agents.preflight
```

That checks backend importability, managed-agent route registration, and
the migration/schema-log contract for the managed-agents features.

If you have real Anthropic credentials configured and want a read-only
API verification on top:

```bash
python -m scripts.managed_agents.preflight --live-readonly
```

For the cost-incurring end-to-end session checks, run the specialized
scripts directly:

```bash
python -m scripts.managed_agents.session_smoke
python -m scripts.managed_agents.drafter_smoke --save-events out.jsonl
```

Plan gating is the same as lead qualification: free tier is blocked
server-side before the agent is invoked.

### From a dev script (repo review)

```bash
export GITHUB_TOKEN=ghp_...       # PAT with Contents: Read
python -m scripts.managed_agents.review_branch --branch my-feature
```

This mounts the current repo at `/workspace/agentnexlify` inside the
agent's container via a `github_repository` resource, kicks off the
`codebase_reviewer` agent, streams events to your terminal, and exits
when the session goes idle. Use `--save-events out.jsonl` to capture the
full event stream for post-hoc inspection.

---

## Tools & Skills

Each agent in `config/managed_agents.yaml` can declare:

- **`tools`** — the `agent_toolset_20260401` built-in tools (`bash`,
  `read`, `write`, `edit`, `glob`, `grep`, `web_fetch`, `web_search`),
  `mcp_toolset` entries, and `custom` tools.
- **`mcp_servers`** — URLs for third-party MCP servers (GitHub, Linear,
  Notion, etc.). Credentials go in a separate **vault** and are attached
  at session create via `vault_ids: [...]`.
- **`skills`** — pre-built Anthropic skills (`xlsx`, `docx`, `pptx`,
  `pdf`) or custom skills uploaded via the Skills API.

The default configuration in this repo is conservative:

| Agent               | Bash | Web  | File ops | Skills          |
|---------------------|------|------|----------|-----------------|
| `lead_qualifier`    | ✗    | ✓    | read only| —               |
| `document_drafter`  | ✗    | ✗    | ✓        | docx, xlsx, pdf |
| `codebase_reviewer` | ✓    | ✓    | ✓        | —               |

`lead_qualifier` has bash disabled because it's called from the
request path and we don't want an LLM running arbitrary shell on behalf of
tenants. `document_drafter` has bash disabled because the doc-generation
skills handle file writes themselves. `codebase_reviewer` needs bash for
`git log` / `git diff`.

To change a tool or skill, edit the YAML and re-run `provision.py`. It
will call `POST /v1/agents/{id}` with the new config and bump the agent
version. Existing sessions keep their pinned version; new sessions
(created with the string shorthand) pick up the latest.

---

## Cost model

Sessions are billed:

- **Model inference** against your standard Anthropic token quotas — use
  `span.model_request_end` events to track `model_usage` per turn.
- **Container runtime** per second a session is `running`.
- **Tool execution** where applicable.

For high-volume product flows (e.g. lead qualification) prefer
`claude-sonnet-4-6`. For developer flows where correctness matters more
than latency (code review), `claude-opus-4-7` is fine.

**Rule of thumb:** if you can do it with a single `messages.create()` call
against the existing `llm_runtime.py`, do that instead. Managed Agents is
the right tool when you genuinely need the container + tool loop.

---

## Widget chat fallback (support_agent as second tier)

**Status: shipped 2026-04-10, off by default, opt-in per tenant.**

The widget chat endpoint (`backend/routers/widget_chat.py`) now supports a
second-tier fallback to the `support_agent` managed agent for hard
questions the inline Claude call can't answer from the tenant KB alone.

### Flow

```
User → widget → inline Claude (sonnet, KB in system prompt)
  ├─ confident answer → reply directly
  ├─ "HANDOFF_REQUESTED" → human handoff (SMS + email + webhook)
  └─ "FALLBACK_TO_SUPPORT_AGENT" (new)
       └─ support_agent managed agent (with 8s timeout)
            ├─ confidence=high/medium → swap reply, log success
            ├─ confidence=low → append HANDOFF_REQUESTED, log low-confidence
            └─ timeout / error / not_configured → force HANDOFF_REQUESTED
```

### Enabling the fallback

Per-tenant opt-in via `widget_configs.enable_ai_fallback` (migration
`101_widget_ai_fallback_flag.sql`). Default `false`.

```sql
UPDATE widget_configs
SET enable_ai_fallback = true
WHERE tenant_id = '<tenant_uuid>';
```

Tenants can also toggle this themselves from the Widget Settings page
(checkbox: **AI deep fallback**, under Customization).

When the flag is on, the inline Claude system prompt receives an extra
FALLBACK PROTOCOL instruction telling it to emit the marker instead of
guessing. When the flag is off, the inline Claude prompt does not mention
the marker at all, and the helper strips any leaked marker defensively.

### Where the code lives

- `backend/routers/widget_chat.py::_run_support_fallback` — helper that
  owns the entire fallback decision + execution + logging. Returns
  `(new_assistant_text, ai_fallback_fired)`. The endpoint calls it
  unconditionally after the inline Claude reply is finalized.
- `FALLBACK_MARKER` — module-level constant so both the prompt builder
  and the detector stay in sync.
- `FALLBACK_TIMEOUT_SECONDS = 8.0` — hard ceiling on the round-trip.

### Observability

Every fallback invocation writes an `ai_fallback_fired` row to
`activity_log` with metadata:

```
{
  session_id,
  confidence,          # 'high' / 'medium' / 'low' / null on error
  escalate_reason,     # support_agent's own escalate_reason, if any
  duration_ms,
  success,             # true iff high/medium and an answer was returned
  error                # 'timeout' | 'not_configured: ...' | 'exception: ClassName' | null
}
```

Ops dashboard query:

```sql
SELECT
  date_trunc('hour', created_at) AS hour,
  count(*) FILTER (WHERE (metadata->>'success')::boolean) AS successes,
  count(*) FILTER (WHERE NOT (metadata->>'success')::boolean) AS degraded,
  avg((metadata->>'duration_ms')::int) AS avg_ms
FROM activity_log
WHERE activity_type = 'ai_fallback_fired'
  AND created_at > now() - interval '24 hours'
GROUP BY 1 ORDER BY 1 DESC;
```

### Cost model

Each fallback invocation runs the full `support_agent` session — Sonnet
with `web_search` + `web_fetch` tools. Empirically ~$0.03-0.08 per
invocation based on the 2026-04-10 live smoke. Budget ~$0.05/fallback
when sizing monthly limits.

The fallback ONLY fires when the inline Claude emits the marker. On the
2026-04-10 smoke with MTOptions's KB, the marker fired on roughly 5-10%
of widget messages, so the average per-message cost uplift is well under
a penny. Monitor `activity_log` for fallback volume per tenant.

### Testing

Unit tests live in `backend/tests/test_widget_chat_fallback.py`. 13
tests cover: marker absent, marker + flag off (strip), success paths
(high/medium confidence), low-confidence forcing handoff, timeout,
`ManagedAgentNotConfigured`, generic exception, and the log_activity
failure resilience case. All mocks — no live API calls in this file.

### Rollout plan

1. Ship with default `false`. No impact on existing tenants.
2. Enable for Aidan's test tenant → run 10+ real messages.
3. Enable for MTOptions (top widget driver) → monitor activity_log for
   24 hours.
4. Roll to remaining 4 testers if MTOptions results are clean.
5. Default new widget configs to `true` after 1 week of clean prod data.

---

## Known limitations

This integration is intentionally minimal. The pieces below are **not
implemented** — read this list before putting a new flow into the request
path.

- **No SSE reconnect / replay.** `ManagedAgentsClient.stream_events` opens a
  single SSE connection and does not retry or de-dupe events after a TCP
  drop. If the connection dies mid-session the client hangs waiting for
  events that will never arrive. The fix (from Anthropic's client-patterns
  handout, `shared/managed-agents-client-patterns.md` — an external document
  that was never vendored into this repo, so do not go looking for it here)
  is: call
  `list_events(session_id)` on reconnect, dedupe by event ID, then resume
  `stream_events`. We will add this when we have a flow that runs long
  enough to care. Until then, treat any flow > ~60s as best-effort.
- **Live end-to-end validated on 2026-04-09.** The provisioner has been
  run against the live API with our specific `config/managed_agents.yaml`
  — environment `agentnexlify-shared` and all three agents
  (`lead_qualifier`, `document_drafter`, `codebase_reviewer`) were created
  and their IDs written to `.env.managed_agents`. The session-level smoke
  test in `scripts/managed_agents/session_smoke.py` ran successfully
  against `lead_qualifier`: `POST /v1/sessions` → 200 OK,
  `POST /v1/sessions/{id}/events` → 200 OK, SSE stream returned 7 events
  (status_running → user.message → model_request_start → agent.thinking →
  agent.message → model_request_end → session.status_idle with
  `stop_reason.type == "end_turn"`), and the break-gate correctly
  terminated the loop. Re-run `session_smoke.py` any time you touch the
  client, the registry, or the YAML.
- **No correlation IDs in router logs.** `backend/routers/managed_agent_runs.py`
  logs at session create time but does not attach a `trace_id` or propagate
  one through the event loop. Debugging a failed session against Railway
  logs means grepping by `session_id`, which is fine for one-off postmortems
  but not good enough for a production flow.
- **No Managed Agents rate-limit tracking.** Managed Agents has its own
  RPM limits (~60 RPM on creates, ~600 RPM on other endpoints) separate
  from the `/v1/messages` quota. Our client does not read or expose
  `anthropic-ratelimit-*` headers, and the only backpressure is
  `limiter.limit("10/minute")` on the FastAPI route. If we drive more than
  one flow from managed agents in parallel we need to wire the headers
  into a shared budget.
- **No vault / MCP credential helper.** `ManagedAgentsClient` does not
  expose `create_vault` / `attach_vault` wrappers. If we add an MCP server
  that needs an OAuth token (GitHub, Linear, Notion) we have to call the
  vault endpoints via raw HTTP or add SDK coverage. For the three
  template agents in `config/managed_agents.yaml` this is fine — none
  need credentials.
- **No SDK swap-in.** `backend/services/managed_agents.py` is a raw-HTTP
  wrapper. It was originally kept independent of an `anthropic==0.42.0` pin
  that predated `client.beta.agents.*`; **that pin is gone** —
  `backend/requirements.txt` now pins `anthropic>=0.95.0,<1`, which does
  expose those bindings. So the blocker is no longer capability, just that
  nobody has done the swap. The wrapper interface is designed to swap 1:1
  whenever someone wants to.

## Troubleshooting

**`Managed Agent not configured: set LEAD_QUALIFIER_AGENT_ID …`**
`scripts/managed_agents/provision.py` hasn't been run, or its output
(`.env.managed_agents`) isn't being loaded. Verify `settings.model_config`
lists both `.env` and `.env.managed_agents`.

**`HTTP 409 ... cannot delete/archive while running`**
You tried to cleanup a session the moment it went idle. The SSE stream's
`session.status_idle` event arrives a few hundred ms before the status
write lands. Poll `get_session(session_id)` until `status != "running"`
before archiving. (Pattern 6 of Anthropic's external client-patterns
handout; not a file in this repo.)

**`HTTP 400 invalid_request_error: agent field …`**
You passed `model` / `system` / `tools` on the session body. Those all
live on `agents.create()`, not `sessions.create()`. Re-check the call
site — the common mistake is copy-pasting an inline agent config into
the session.

**Stream disconnects mid-session and the client hangs**
The SSE stream has no replay. If the TCP connection drops while an
`agent.tool_use` is waiting on your `user.tool_confirmation`, the session
deadlocks. On reconnect, call `client.list_events(session_id)` first to
catch up, dedupe by event ID, then continue tailing
`stream_events(session_id)`. (Pattern 1 of Anthropic's external
client-patterns handout; not a file in this repo.)

**Need to upgrade the Anthropic SDK**
Historically our client used raw HTTP via httpx to avoid upgrading a pinned
`anthropic==0.42.0` SDK that predated the beta agent bindings. **That pin is
long gone** — `backend/requirements.txt` now pins `anthropic>=0.95.0,<1`,
which does expose `client.beta.agents.*`. The httpx wrapper is kept because
it works and is tested, not because the SDK can't do it. If you want to swap
it, the wrapper interface was designed to be swappable — every method maps
1:1 to an SDK call.

---

## References

- Anthropic client-patterns handouts, referenced as `shared/managed-agents-*.md`
  and surfaced through the `claude-api` skill in Claude Code. **External — these
  are not files in this repo.** The patterns we rely on are written out in this
  document instead.
- API reference:
  https://platform.claude.com/docs/en/managed-agents/overview
- Live Anthropic CLI (another way to provision via YAML):
  https://platform.claude.com/docs/en/api/sdks/cli
- Source files in this repo:
  - `config/managed_agents.yaml`
  - `backend/services/managed_agents.py`
  - `backend/services/managed_agents_registry.py`
  - `backend/routers/managed_agent_runs.py`
  - `scripts/managed_agents/provision.py`
  - `scripts/managed_agents/review_branch.py`
  - `backend/tests/test_managed_agents.py`
