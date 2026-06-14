# Agent OS — Connector Group A: Inbound Channels — Spec

**Status:** draft
**Owner:** Aidan
**Created:** 2026-05-25
**Tenant scope:** all
**Priority:** P5 (post-P0/P1-P4 launch gate)
**Parent spec:** `specs/agent-os-overhaul_spec.md`

## Problem

Today the Agent OS orchestrator only receives prompts from one place: the
`AgentOS.jsx` chat shell (POST `/api/v1/os/threads/{id}/messages`). The widget,
email, and SMS are all separate input surfaces that land in `conversations` /
`chat_messages` / nothing. The orchestrator never sees them, so its memory and
backlog only reflect what the owner types in the dashboard.

A real-world tenant has customer messages arriving on the website widget,
inbound email, and SMS replies to campaigns — none of which feed the OS. The
OS can't help with what it can't see.

## Goals

- Every customer-facing inbound message becomes an `os_thread` + `os_message`
  the orchestrator can read, route, and (for tenant-owned threads) act on.
- One bridge per inbound source. Bridges are additive — disabling a bridge
  doesn't break the source.
- Owner opts each bridge on/off per tenant (Settings → Inbound Channels).
- Bridges respect existing per-channel routing: widget messages still land in
  `conversations` for backwards compat; SMS still routes through Twilio
  webhooks; email still notifies the owner.

## Non-Goals

- Replacing the widget conversation surface — widget keeps writing to
  `conversations` + `chat_messages`. Bridge is additive.
- Building new channels (no WhatsApp, no Telegram, no native voice).
- Outbound from these channels — that's Group B (action connectors).
- Authoring a unified inbox UI — owner reads inbound threads in the existing
  Conversations page; OS threads remain a separate surface.

## User Stories

- As an **owner**, a customer messages my widget → orchestrator sees the
  thread, can summarize it into memory, and surfaces it in the no-fit backlog
  if the customer asks for something my agents can't do.
- As an **owner**, a customer emails my connected Gmail → orchestrator opens
  an `os_thread` tagged `inbound:email`, summarizes the message, drafts a
  reply (approval-gated), and posts the draft back to the thread.
- As an **owner**, a lead replies "STOP" to a campaign SMS → orchestrator
  opens an `os_thread`, marks the lead `do_not_contact`, and notifies me in
  the thread.
- As an **owner**, I toggle "Bridge widget → Agent OS" off in Settings →
  Inbound Channels, and new widget messages stop creating `os_threads` (old
  ones stay).
- Edge cases:
  - Customer sends 20 messages in 30 seconds → orchestrator debounces, opens
    one thread, summarizes the burst as one `os_message`.
  - Inbound email is auto-reply / out-of-office → bridge tags
    `inbound_kind: auto_reply` and orchestrator skips routing.
  - Connector revoked mid-flow (e.g. Gmail OAuth expired) → bridge writes a
    Settings banner via existing `tenant_integrations.status='expired'`.

## Architecture

```
Widget message  ─►  widget_chat.py POST handler ─►  conversations + chat_messages
                                                ╰─►  inbound_bridge.bridge_widget(...)
                                                       ╰─► os_threads + os_messages
                                                            ╰─► orchestrator (background)

Inbound email   ─►  email webhook (Postmark/Mailgun) ─► inbound_bridge.bridge_email(...)
Inbound SMS     ─►  Twilio webhook                   ─► inbound_bridge.bridge_sms(...)
Facebook DM     ─►  channels_facebook.py webhook     ─► inbound_bridge.bridge_facebook(...)
```

All bridges land in one service: `backend/services/os_inbound_bridge.py`. One
function per source; each:
1. Resolves or creates the `os_thread` for this conversation (dedup by
   `(client_id, source, source_thread_id)`).
2. Appends an `os_message` with `role='user'`, `inbound_kind=<source>`.
3. Triggers orchestrator background processing (existing
   `orchestrator.handle_thread_message()` path).
4. Returns immediately — the inbound webhook stays under 5s for FB/SMS retry
   policies.

### Reused infra

- `backend/services/orchestrator.py` — orchestrator entrypoint; bridges call
  it as if the message came from the chat shell.
- `backend/routers/widget_chat.py` — widget message handler; bridge plugs in
  via a feature flag check (`tenant_integrations.bridge_widget_enabled`).
- `backend/routers/channels_facebook.py` — Facebook webhook; bridge plugs in
  after existing `channel_manager.ingest_channel_message()` call.
- `backend/services/google_calendar.py` — Google OAuth shared with Gmail
  inbound (Group B extends scopes).

### Net-new code

- `backend/services/os_inbound_bridge.py` — 4 bridge functions
  (`bridge_widget`, `bridge_email`, `bridge_sms`, `bridge_facebook`).
- `backend/routers/os_inbound.py` — new webhook routes for email + SMS
  (existing FB webhook gets a plug-in call).
- Email webhook signature verification (provider-specific — Postmark HMAC or
  Mailgun signature).

## Data Model

One new migration (next free number = 124 at build time, verify with
`ls migrations/`):

- `124_os_threads_inbound.sql` — additive ALTERs on existing `os_threads`:
  - `source TEXT NOT NULL DEFAULT 'chat'` — `chat | widget | email | sms | facebook`
  - `source_thread_id TEXT NULL` — provider-side conversation identifier
    (e.g. widget `conversation_id`, email Message-ID thread, FB thread ID)
  - `source_metadata JSONB NULL` — provider raw context (sender email, phone,
    FB user ID) for the orchestrator to read
  - UNIQUE `(client_id, source, source_thread_id) WHERE source_thread_id IS NOT NULL`
    — bridge dedup key
- ALTERs on `os_messages`:
  - `inbound_kind TEXT NULL` — `auto_reply | normal | system_notice`, populated
    by bridges, NULL for owner-typed messages
  - `source_ref TEXT NULL` — set by bridges to
    `"<source>:<provider_message_id>"` for replay protection; NULL for
    owner-typed messages. UNIQUE partial index on `(client_id, source_ref)
    WHERE source_ref IS NOT NULL` enforces the dedup invariant from
    §Security.

Per-tenant bridge toggles live in `tenant_integrations` as JSON config under
`integration_type='os_inbound_bridges'`:
```json
{
  "widget_enabled": true,
  "email_enabled": false,
  "sms_enabled": true,
  "facebook_enabled": true,
  "email_provider": "postmark",
  "email_inbound_address": "agent@tenant.com"
}
```

## API Surface

- `POST /api/v1/os/inbound/email/{provider}` — Postmark/Mailgun inbound
  webhook. HMAC verified per provider.
- `POST /api/v1/os/inbound/sms` — Twilio inbound SMS webhook. Twilio signature
  verified.
- `POST /api/v1/os/inbound/bridge-toggle` — owner toggles bridge per source
  (`{source: "widget", enabled: false}`). Owner-role only.

Existing routes get a bridge call inline:
- `widget_chat.py` POST handler — after `chat_messages` insert, if widget
  bridge enabled, fire-and-forget `bridge_widget(...)`.
- `channels_facebook.py` POST webhook — after `ingest_channel_message`, if
  FB bridge enabled, fire-and-forget `bridge_facebook(...)`.

## Security

- **Webhook signature verification** mandatory for every inbound provider.
  Reject 401 on signature mismatch (Postmark/Mailgun HMAC, Twilio signature,
  FB hub.verify_token).
- **Tenant isolation** — bridge resolves `client_id` from
  provider→tenant lookup tables (existing for FB, lookup by inbound email
  address for email, lookup by Twilio number for SMS). Reject 404 if
  unmapped — never default to a tenant.
- **Owner-only bridge toggle** — POST `/api/v1/os/inbound/bridge-toggle`
  requires `require_role("owner")`.
- **PII** — inbound messages may contain customer PII; stored in
  `os_messages` (RLS-protected, same as orchestrator-typed messages). Bridges
  redact OAuth tokens from `source_metadata` before insert.
- **Replay protection** — bridges check
  `(source, source_thread_id, provider_message_id)` to avoid double-inserting
  on provider retry. Idempotency key: `(client_id, source, provider_message_id)`.

## Open Questions

- Inbound email provider — Postmark vs Mailgun vs SES. Owner: Aidan. Resolved
  before build by partner/cost choice; bridge supports either via
  `email_provider` config.
- Twilio inbound numbers — do tenants bring their own or do we provision?
  Owner: Aidan. Out of scope here; bridge assumes a number is mapped to a
  tenant somehow.
- Per-bridge rate limit — does a widget message storm risk a Sonnet bill
  spike? Resolved by inheriting existing `usage_meter` cap — orchestrator
  refuses to route when capped, bridge still records the inbound message.

## Out-of-Scope (defer)

- WhatsApp Business inbound — defer; Meta WhatsApp Cloud API not in tenant
  stack yet.
- Voice → text inbound (phone calls) — defer; Twilio voice transcription is
  a separate workflow.
- LinkedIn/Instagram DM inbound — defer to Group B+ (those connectors are
  net-new OAuth apps; outbound ships first).
- Unified inbox UI — defer; owner reads inbound threads in `AgentOS.jsx`.

## Done criteria

- New migration applied via Supabase MCP; `os_threads.source` defaults to
  `'chat'` for existing rows.
- `bridge_widget()` end-to-end test: widget POST → `os_threads` row created,
  orchestrator background job runs, deliverable posts back to thread.
- Email + SMS bridges: webhook signature verification unit tests pass.
- Facebook bridge: existing webhook test still passes; bridge call is
  fire-and-forget (no slowdown on the 5s FB retry budget).
- Settings → Inbound Channels page lets owner toggle all 4 bridges; toggle
  writes `tenant_integrations.config`.
- `usage_meter` cap respected — bridge records the inbound message even when
  orchestrator refuses to route (so the no-fit backlog still works).

## Cross-refs

- `specs/agent-os-overhaul_spec.md` — parent spec; §Connector phase A in the
  overhaul groups by OAuth-app cost, this group is the functional inbound
  grouping per `plans/agent-os-next-steps_plan.md` §1
- `plans/agent-os-next-steps_plan.md` §1 — operative connector group split
- `backend/routers/channels_facebook.py` — existing FB inbound webhook
- `backend/routers/widget_chat.py` — existing widget message handler
- `backend/services/orchestrator.py` — orchestrator entry the bridges call
