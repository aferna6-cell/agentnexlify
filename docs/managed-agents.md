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

15 tests should pass. They exercise the client, error mapping, SSE
parsing, and the registry in isolation — no live API calls.

Hit the health endpoint from your dashboard once the backend is deployed:

```bash
curl -H "Authorization: Bearer $JWT" \
     https://agentnexlify-production.up.railway.app/api/v1/managed-agents/$TENANT_ID/health
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
than latency (code review), `claude-opus-4-6` is fine.

**Rule of thumb:** if you can do it with a single `messages.create()` call
against the existing `llm_runtime.py`, do that instead. Managed Agents is
the right tool when you genuinely need the container + tool loop.

---

## Known limitations

This integration is intentionally minimal. The pieces below are **not
implemented** — read this list before putting a new flow into the request
path.

- **No SSE reconnect / replay.** `ManagedAgentsClient.stream_events` opens a
  single SSE connection and does not retry or de-dupe events after a TCP
  drop. If the connection dies mid-session the client hangs waiting for
  events that will never arrive. Anthropic's `shared/managed-agents-client-patterns.md`
  pattern 1 ("SSE reconnect with replay") describes the fix: call
  `list_events(session_id)` on reconnect, dedupe by event ID, then resume
  `stream_events`. We will add this when we have a flow that runs long
  enough to care. Until then, treat any flow > ~60s as best-effort.
- **No live end-to-end validation against our YAML config.** The
  provisioner's `--dry-run` path has been run against the live API
  (`list_environments` + `list_agents` both returned 200 OK), and the
  read-only smoke test in `scripts/managed_agents/smoke.py` exercises the
  same two endpoints. `create_environment`, `create_agent`, `create_session`,
  `send_user_message`, and the SSE stream have **never** been run against
  the live API with our specific `config/managed_agents.yaml`. The first
  real provisioning run should be treated as a deployment, not a
  development iteration — watch the output closely and keep a human in
  the loop.
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
  wrapper intentionally kept independent of `anthropic==0.42.0`, which is
  pinned by `llm_runtime.py`. When we eventually upgrade the SDK and get
  `client.beta.agents.*`, the wrapper interface is designed to swap 1:1 —
  but the swap hasn't happened and the risks of upgrading the pinned SDK
  are owned by `llm_runtime.py`, not this module.

## Troubleshooting

**`Managed Agent not configured: set LEAD_QUALIFIER_AGENT_ID …`**
`scripts/managed_agents/provision.py` hasn't been run, or its output
(`.env.managed_agents`) isn't being loaded. Verify `settings.model_config`
lists both `.env` and `.env.managed_agents`.

**`HTTP 409 ... cannot delete/archive while running`**
You tried to cleanup a session the moment it went idle. The SSE stream's
`session.status_idle` event arrives a few hundred ms before the status
write lands. Poll `get_session(session_id)` until `status != "running"`
before archiving. See
`shared/managed-agents-client-patterns.md` pattern 6 in the
`claude-api` skill.

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
`stream_events(session_id)`. See
`shared/managed-agents-client-patterns.md` pattern 1.

**Need to upgrade the Anthropic SDK**
Our client uses raw HTTP via httpx specifically so we don't have to
upgrade the pinned `anthropic==0.42.0` SDK in
`backend/requirements.txt` (newer SDKs break
`backend/services/llm_runtime.py` contracts). If you eventually want to
swap the httpx client for `client.beta.agents.*`, the wrapper interface
was designed to be swappable — every method maps 1:1 to an SDK call.

---

## References

- Skill docs (loaded via `/claude-api` skill in Claude Code):
  `shared/managed-agents-*.md`
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
