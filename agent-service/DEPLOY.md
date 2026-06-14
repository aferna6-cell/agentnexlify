# agent-service — Railway deploy + v2 engine activation

The FastAPI backend routes the dashboard Agent OS through this service when
`AGENT_SERVICE_URL` is set, and falls back to the legacy Python orchestrator
when it is not. Deploying this service and setting that var activates the v2
engine. The public customer widget is unaffected — the inbound widget bridge
defaults off (`os_inbound_bridge` `widget_enabled=False`) and the widget
AI-fallback path is gated per-tenant on `enable_ai_fallback`.

## Security model

agent-service is pure compute and holds no database credentials, but it can
spend Anthropic credits. Two layers protect it:

1. **Railway private networking** — deploy in the **same Railway project** as
   the backend and call it over `*.railway.internal`. Do not assign a public
   domain.
2. **Shared secret** — set `AGENT_SERVICE_TOKEN` on both services. agent-service
   rejects any compute request missing a matching `X-Agent-Token` header
   (`401`). `/health` stays open for the Railway healthcheck. With the token
   unset, the service runs in open mode (local dev only).

## One-time deploy

1. New Railway service in the backend's project:
   - **Root Directory:** `/` (repo root — the Dockerfile `COPY`s both
     `agent-service/` and `.claude/`).
   - **Dockerfile Path:** `agent-service/Dockerfile` (pins `node:22-alpine`).
   - Healthcheck `/health` is already declared in `agent-service/railway.json`.
2. Set env vars on **agent-service**:
   - `ANTHROPIC_API_KEY` — required; without it the engine returns
     `ModelUnavailableError` and the backend falls back to legacy.
   - `AGENT_SERVICE_TOKEN` — shared secret (generate a long random value).
   - `PORT` — optional, defaults to `3100`.
3. Deploy. Confirm the service logs `listening on :3100` and the Railway
   healthcheck is green.

## Activate the engine

Set on the **backend** service, then redeploy it:

- `AGENT_SERVICE_URL=http://<agent-service-name>.railway.internal:3100`
- `AGENT_SERVICE_TOKEN=<same secret as above>`

FastAPI reads env at startup, so the backend must restart to pick these up.

## Verify

1. Backend → service reachability: a dashboard Agent OS "ask" returns a draft
   and writes one `os_agent_runs` row (with engine trace metadata).
2. Trace quality (the v2 fixes): department-head name + confidence %, no
   literal `[Business Name]`, no markdown in SMS drafts.
3. Auth: a request to `/orchestrate` without `X-Agent-Token` returns `401`
   (only testable if the service has a reachable URL; internal-only is fine).

## Rollback

Unset `AGENT_SERVICE_URL` on the backend and redeploy. Every call site falls
back to the legacy path. Persisted `os_*` rows stay readable; no cleanup
needed.
