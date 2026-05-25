# Agent OS — Connector Group A: Inbound Channels — Build Plan

**Source spec:** `specs/agent-os-connectors-inbound_spec.md`
**Status:** active
**Owner:** Aidan
**Branch:** `claude/agent-os-grill-resume-cHznV` (PR #177 draft)
**Created:** 2026-05-25

## Goal

Bridge widget, email, SMS, Facebook inbound messages into `os_threads` + `os_messages` so the Agent OS orchestrator can read, route, and (for tenant-owned threads) act on every customer-facing message — not just owner chat-shell prompts.

## Pre-flight (verify, do not assume)

- [x] Spec written + committed
- [x] Migration number free: `migrations/` highest = 123 → next = 124
- [ ] `os_threads` + `os_messages` shape matches spec ALTER assumptions
- [ ] `tenant_integrations` table supports `integration_type='os_inbound_bridges'`
- [ ] `widget_chat.py` POST handler is the right plug-in point
- [ ] `channels_facebook.py` webhook is the right plug-in point
- [ ] No existing `os_inbound*` routes/services (avoid collision)

## Build order (smallest → largest; commit at each ☑)

### Phase 1 — Foundation (migration + service skeleton)

**1.1 Migration 124 — `124_os_threads_inbound.sql`**
- ALTER `os_threads`: ADD `source TEXT NOT NULL DEFAULT 'chat'`
- ALTER `os_threads`: ADD `source_thread_id TEXT NULL`
- ALTER `os_threads`: ADD `source_metadata JSONB NULL`
- CREATE UNIQUE INDEX `os_threads_source_thread_uniq ON os_threads (client_id, source, source_thread_id) WHERE source_thread_id IS NOT NULL`
- ALTER `os_messages`: ADD `inbound_kind TEXT NULL`
- CHECK constraint on `os_threads.source`: `IN ('chat','widget','email','sms','facebook')`
- CHECK constraint on `os_messages.inbound_kind`: `IN ('auto_reply','normal','system_notice')`
- Apply via `mcp__supabase__apply_migration`
- Verify via `mcp__supabase__list_tables` that ALTERs landed

**1.2 Bridge service skeleton — `backend/services/os_inbound_bridge.py`**
- Module-level constants: `VALID_SOURCES`, `VALID_INBOUND_KINDS`
- 4 async fns: `bridge_widget`, `bridge_email`, `bridge_sms`, `bridge_facebook`
- Shared helper: `_resolve_or_create_thread(db, client_id, source, source_thread_id, source_metadata) -> thread_id`
- Shared helper: `_append_inbound_message(db, thread_id, content, inbound_kind, provider_message_id) -> message_id`
- Shared helper: `_trigger_orchestrator_bg(background_tasks, thread_id, client_id)` — calls existing `orchestrator.handle_thread_message`
- Idempotency: helper `_already_ingested(db, client_id, source, provider_message_id) -> bool` (look for matching `os_messages.source_ref`)
- Each bridge fn: log entry/exit at INFO; never raise back to webhook (return `(thread_id, message_id)` or `None` on dedup/disabled)
- Type hints. No `from __future__ import annotations`. Logger via `logging.getLogger(__name__)`.

**1.3 Toggle helpers — extend `backend/services/tenant_integration_config.py` (or create if missing)**
- `get_inbound_bridge_config(db, client_id) -> dict` — read `tenant_integrations` row where `integration_type='os_inbound_bridges'`, return config dict with safe defaults (`widget_enabled: True`, `email_enabled: False`, `sms_enabled: True`, `facebook_enabled: True`)
- `set_inbound_bridge_toggle(db, client_id, source, enabled) -> dict` — upsert config; returns new config

**Commit checkpoint:** "feat(agent-os): migration 124 + os_inbound_bridge service skeleton"

### Phase 2 — Widget bridge (lowest risk; existing infra)

**2.1 Plug into `widget_chat.py` POST handler**
- After `chat_messages` insert succeeds + tenant identified
- Read `get_inbound_bridge_config(db, client_id)`; if `widget_enabled` False → skip
- Fire-and-forget via `background_tasks.add_task(bridge_widget, ...)` (BackgroundTasks already in scope per FastAPI handler)
- Pass: `client_id`, `conversation_id` (as `source_thread_id`), customer name/email from `chat_messages.metadata` (as `source_metadata`), message content
- Bridge must NOT block the widget response — fail-open

**2.2 `bridge_widget` impl**
- Resolve/create thread with `source='widget'`, `source_thread_id=conversation_id`, `source_metadata={...}`
- Append `os_message` with `role='user'`, `inbound_kind='normal'`, `content=<message body>`, `source_ref=f"widget:{provider_message_id}"`
- Trigger orchestrator background processing
- Wrap whole fn in `try/except`; log exceptions, never raise

**2.3 Test — `tests/test_os_inbound_bridge_widget.py`**
- Happy path: POST widget chat → 200 → thread exists with `source='widget'` → message exists with `inbound_kind='normal'`
- Disabled path: toggle off → POST → 200 → no os_thread row created
- Idempotency: POST same message twice → 1 thread, 1 message (dedup by provider_message_id via `source_ref`)
- Fire-and-forget non-blocking: widget POST returns even if bridge raises (mock bridge to raise; assert 200 returned)

**Commit checkpoint:** "feat(agent-os): bridge widget messages into os_threads"

### Phase 3 — Settings router (toggle endpoint)

**3.1 `backend/routers/os_inbound.py`**
- `POST /api/v1/os/inbound/bridge-toggle` — Pydantic body `{source: str, enabled: bool}`; `require_role("owner")`; calls `set_inbound_bridge_toggle`
- `GET /api/v1/os/inbound/bridge-config` — read role any; returns current toggle config
- Register in `backend/main.py` route registration block

**3.2 Test — `tests/test_os_inbound_routes.py`**
- Owner can toggle; non-owner gets 403
- Toggle persists; GET reflects new state
- Source validation: invalid `source` → 422

**Commit checkpoint:** "feat(agent-os): inbound bridge owner-only toggle API"

### Phase 4 — Email bridge (Postmark, signature-verified webhook)

**4.1 Email signature verification helper — `backend/services/inbound_email_verify.py`**
- `verify_postmark(request) -> bool` — HMAC-SHA256 over body using `POSTMARK_WEBHOOK_SECRET` env
- `verify_mailgun(request) -> bool` — Mailgun signature scheme (timestamp + token + key)
- Provider dispatch: `verify(provider, request) -> bool`

**4.2 `bridge_email` impl + `POST /api/v1/os/inbound/email/{provider}` route**
- Webhook handler verifies sig first → 401 on mismatch
- Resolve tenant by inbound email address (lookup table — query `tenant_integrations.config->>'email_inbound_address'`); 404 if unmapped
- Detect `auto_reply` via headers (`Auto-Submitted`, `Precedence: bulk/auto_reply`, `X-Autoreply`)
- Append `os_message` with `inbound_kind='auto_reply'` or `'normal'`
- Trigger orchestrator background processing

**4.3 Test — `tests/test_os_inbound_email.py`**
- Postmark sig pass → 200, thread + message created
- Postmark sig fail → 401
- Unmapped sender → 404, no thread
- Auto-reply detection sets `inbound_kind='auto_reply'`
- Subject line + sender email captured in `source_metadata`

**Commit checkpoint:** "feat(agent-os): email inbound bridge (Postmark + Mailgun)"

### Phase 5 — SMS bridge (Twilio webhook)

**5.1 `bridge_sms` impl + `POST /api/v1/os/inbound/sms` route**
- Twilio signature verification via `twilio.request_validator.RequestValidator`
- Resolve tenant by `To` phone number (lookup table — see existing Twilio config)
- Special handling: body matches `STOP|UNSUBSCRIBE|CANCEL` (case-insensitive) → also flip `leads.do_not_contact = true` for any lead with this phone
- Append `os_message` with `inbound_kind='normal'`
- Return TwiML empty response (Twilio expects XML); do NOT block

**5.2 Test — `tests/test_os_inbound_sms.py`**
- Valid Twilio sig → 200 + thread/message
- Invalid sig → 401
- STOP message → `leads.do_not_contact` flipped + `os_message` posted
- Unknown `To` number → 404

**Commit checkpoint:** "feat(agent-os): SMS inbound bridge (Twilio + STOP keyword)"

### Phase 6 — Facebook bridge (existing webhook plug-in)

**6.1 Plug into `channels_facebook.py` POST webhook**
- After existing `channel_manager.ingest_channel_message()` call
- Read `get_inbound_bridge_config(db, client_id)`; if `facebook_enabled` False → skip
- Fire-and-forget `bridge_facebook(...)`

**6.2 `bridge_facebook` impl**
- Resolve/create thread with `source='facebook'`, `source_thread_id=fb_thread_id`, `source_metadata={sender_id, page_id, ...}`
- Append message; trigger orchestrator
- Same fail-open pattern

**6.3 Test — `tests/test_os_inbound_facebook.py`**
- Existing FB webhook test still passes
- Plug-in fires when enabled; no-ops when disabled
- Bridge exceptions do not slow 5s FB retry budget

**Commit checkpoint:** "feat(agent-os): Facebook DM inbound bridge"

### Phase 7 — Settings UI (frontend)

**7.1 `frontend/src/pages/SettingsInboundChannels.jsx`**
- 4 toggles: Widget, Email, SMS, Facebook
- Email row: text field for `email_inbound_address`, provider dropdown (Postmark/Mailgun)
- Load via `GET /api/v1/os/inbound/bridge-config`
- Save via `POST /api/v1/os/inbound/bridge-toggle` (one source at a time)
- Dark theme, helpful empty state
- Sidebar entry in `Sidebar.jsx`; route in `App.jsx`

**Commit checkpoint:** "feat(agent-os): Settings -> Inbound Channels UI"

### Phase 8 — Self-verification + done-criteria check

- Run `pytest tests/test_os_inbound*.py -v` — all pass
- Run `pytest tests/test_os_mvp_e2e.py -v` — still passes (no regression)
- Run `cd frontend && npm run build` — clean
- Manually exercise: send widget message in dev → confirm `os_threads` row appears with `source='widget'`
- Bridge respects toggle: flip off → next message does NOT create `os_thread`
- Idempotency proven via test
- Verification line in PR description

## Risk register

| Risk | Mitigation |
|---|---|
| Widget bridge slows the chat response | Strict fire-and-forget; no `await bridge_widget(...)` — only `background_tasks.add_task` |
| Postmark/Mailgun sig wrong → all inbound 401 | Unit test sig fn with known-good fixture per provider |
| Twilio STOP loop (STOP triggers reply triggers STOP) | Orchestrator already respects `leads.do_not_contact`; verify before shipping |
| 10k-msg-burst from single customer | Inherit existing `usage_meter.py` cap; bridge writes os_message but orchestrator refuses to route |
| Schema drift after applying 124 | Run `schema-guardian` before any new model touching `os_threads`/`os_messages` |
| Migration 124 conflicts with concurrent work on main | Branch is isolated; verify free number AGAIN at apply time |

## Out of plan (in spec, deferred to follow-on plans)

- Unified inbox UI — owner reads inbound threads in `AgentOS.jsx`
- WhatsApp / voice / LinkedIn / Instagram DM inbound
- Replacing the widget conversation surface (bridge stays additive)

## Done criteria

Mirrors spec §"Done criteria" — all 6 items must pass before this plan closes:

1. Migration 124 applied; `os_threads.source` defaults to `'chat'` for existing rows
2. `bridge_widget()` end-to-end test passes
3. Email + SMS bridge sig verification unit tests pass
4. Facebook bridge: existing webhook test still passes; plug-in non-blocking
5. Settings → Inbound Channels page lets owner toggle all 4 bridges
6. `usage_meter` cap respected — bridge records message even when orchestrator refuses

## Cross-refs

- `specs/agent-os-connectors-inbound_spec.md` — source spec
- `plans/agent-os-next-steps_plan.md` §1 — connector ordering
- `plans/agent-os-p0_plan.md` — Phase C cleanup gate (runs AFTER all 3 groups)
- `backend/services/orchestrator.py` — orchestrator entry the bridges call
- `backend/services/tenant_scope.py` — tenant-scoped DB helpers
- `backend/routers/widget_chat.py:POST` — widget plug-in point
- `backend/routers/channels_facebook.py:POST` — FB plug-in point
- `migrations/118_os_threads.sql` + `migrations/119_os_messages.sql` — base tables being ALTERed
