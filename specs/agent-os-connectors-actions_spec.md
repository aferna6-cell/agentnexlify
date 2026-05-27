# Agent OS — Connector Group B: Action Connectors — Spec

**Status:** draft
**Owner:** Aidan
**Created:** 2026-05-25
**Tenant scope:** all
**Priority:** P5 (post-P0/P1-P4 launch gate)
**Parent spec:** `specs/agent-os-overhaul_spec.md`

## Problem

Worker agents currently produce deliverables and stop. A `booking` worker
writes a draft appointment to `os_agent_runs.deliverable`; approving it
flips a status flag but **no real-world action occurs**. The campaign worker
drafts a Facebook post that never posts; the lead-nurture worker drafts a
Gmail send that never sends.

Without action connectors, the OS is an idea engine, not an automation
engine. Owners get value only when approved deliverables become real-world
effects.

## Goals

- Every approval-gated deliverable in `os_deliverables` has a typed action
  handler. Approving triggers the action; rejecting does nothing; editing
  modifies the deliverable payload before the action runs.
- One handler per (worker, action_type) pair. Handlers are pluggable: drop a
  module in `backend/services/os_actions/` with an
  `ActionSpec` and it auto-registers (mirrors the worker registry pattern at
  `backend/services/os_workers/__init__.py`).
- Failures surface back to the thread as a system message; the deliverable
  flips to `status='action_failed'`. User can retry from the side-panel
  editor.
- Every action records a row in `os_action_runs` for audit (separate from
  `os_agent_runs` which records orchestrator decisions, not external side
  effects).

## Non-Goals

- Autonomous sends — every action requires user approval. No "auto-approve
  if confidence > X" mode.
- Net-new OAuth apps in this spec — Gmail extends existing Google OAuth;
  Instagram extends existing Meta/Facebook app. LinkedIn / X / Microsoft
  Graph are deferred (overhaul spec §Connector phase C).
- Building handler UI affordances — the side-panel editor already exists at
  `frontend/src/components/os/DeliverablePanel.jsx`. New handlers reuse it.
- Outbound SMS sending — Twilio outbound from workers is deferred (cost +
  compliance review needed first).

## User Stories

- As an **owner**, the booking worker drafts an appointment; I approve;
  Google Calendar event is created; the customer gets a calendar invite;
  the deliverable shows `status='action_succeeded'` with the calendar event
  link.
- As an **owner**, the campaign worker drafts a Facebook post; I edit copy;
  I approve; the post publishes to my connected Page; the deliverable shows
  post URL + post ID.
- As an **owner**, the lead-nurture worker drafts an email reply; I approve;
  Gmail sends from my address; the lead receives it; the deliverable shows
  message-id + thread-id.
- As an **owner**, an action fails (Google Calendar quota hit) → deliverable
  flips to `action_failed`, system message posts to thread with the error,
  I can retry from the side-panel.
- Edge cases:
  - Connector revoked between draft and approval → action handler returns
    `connector_expired`, posts a "reconnect" Settings banner, deliverable
    stays `pending_action` until reconnect.
  - User edits deliverable after approval started → action handler is
    already running; UI disables edit on `status='action_running'`.
  - Idempotency: user clicks Approve twice → second click no-ops because
    `os_deliverables.action_run_id` is set after the first.

## Architecture

```
DeliverablePanel.jsx
   │  approve
   ▼
POST /api/v1/os/deliverables/{run_id}/approve
   │
   ▼
os_deliverables.py — flips status=approved, schedules action
   │
   ▼
BackgroundTasks → run_action(deliverable_id)
   │
   ▼
os_actions registry — picks handler by (worker_name, action_type)
   │
   ▼
handler executes (Google Calendar / Gmail / FB Graph / Instagram Graph / CRM write)
   │
   ▼
os_action_runs row written; os_deliverables.status updated;
system message posted to os_thread with result link
```

### Action handlers (launch set)

| Worker | Action type | Handler module | Reused infra |
|---|---|---|---|
| booking | `calendar.event.create` | `os_actions/calendar.py` | `backend/services/google_calendar.py` |
| lead_nurture | `email.send` | `os_actions/email.py` | extends `integrations.py` Gmail OAuth (Group B in overhaul spec) |
| campaign | `social.facebook.post` | `os_actions/social.py` | `backend/routers/channels_facebook.py` Page tokens |
| campaign | `social.instagram.post` | `os_actions/social.py` | Meta Graph (extends FB app) |
| campaign | `gbp.post` | `os_actions/gbp.py` | `backend/routers/gbp.py` |
| lead_nurture | `crm.lead.update` | `os_actions/crm.py` | Zapier outbound (`zapier.py`) for tenants on Zapier; direct CRM connectors deferred |
| customer_question | `widget.reply` | `os_actions/widget.py` | `widget_chat.py` reply path (when inbound bridge created the thread) |

Each handler exposes:
```python
SPEC = ActionSpec(
    name="calendar.event.create",
    worker="booking",
    handler=run,           # async (ctx, deliverable_payload) -> ActionResult
    required_connectors=["google_calendar"],
)
```

### Registry

`backend/services/os_actions/__init__.py` — auto-discovers every module in
the package, collects `SPEC`, indexes by `name`. Matches the worker
registry pattern at `backend/services/os_workers/__init__.py:25-50`.

Orchestrator+worker contract update: workers produce a deliverable with a
`action_type` field. `os_deliverables.action_type` is non-null when the
worker wants the deliverable approval to trigger an action.

## Data Model

One new migration (next free number = 125 at build time; verify):

- `125_os_action_runs.sql` — new table:
  - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `client_id UUID NOT NULL`
  - `deliverable_id UUID NOT NULL REFERENCES os_deliverables(id)` —
    (if `os_deliverables` is a row in `os_agent_runs`, this is the run id)
  - `action_type TEXT NOT NULL` — `calendar.event.create` etc.
  - `status TEXT NOT NULL` — `queued | running | succeeded | failed`
  - `request_payload JSONB NOT NULL` — what was sent to the external API
  - `response_payload JSONB` — what came back (event URL, message id, post id)
  - `error_detail JSONB` — provider error if failed (no token leaks)
  - `started_at TIMESTAMPTZ`, `finished_at TIMESTAMPTZ`
  - INDEX `(client_id, status)`
  - RLS deny-public (same backstop as P0 tables; service-role client bypasses)

ALTERs on existing tables:

- `os_agent_runs` (or `os_deliverables` table — confirm at build time by
  checking `migrations/120_os_agent_runs.sql`):
  - `action_type TEXT NULL` — set by worker when deliverable should trigger
    an action; NULL = pure-text deliverable, no action
  - `action_run_id UUID NULL REFERENCES os_action_runs(id)` — set when
    action queued (idempotency anchor for double-approve)

## API Surface

Existing routes get behavior updates (no new route shapes):

- `POST /api/v1/os/deliverables/{run_id}/approve` — already exists; behavior
  change: if `action_type` is set, schedule `BackgroundTasks` action run +
  set `action_run_id`. Returns immediately with the action run id.
- `GET /api/v1/os/action-runs/{action_run_id}` — net-new; returns
  `os_action_runs` row for the side panel to poll until terminal state.
- `POST /api/v1/os/action-runs/{action_run_id}/retry` — net-new; owner-only;
  resets to `queued` and re-fires the handler. Useful for transient failures.

Pydantic models per endpoint; no `from __future__ import annotations`.

## Security

- **Approval-gate invariant** — handlers refuse to run if
  `os_deliverables.status != 'approved'`. Enforced in handler, not just
  router.
- **Owner-only retry** — `require_role("owner")` on `/retry`. Approve
  itself can be any role with thread access.
- **Connector token isolation** — every handler resolves
  `tenant_integrations` by `client_id`; never accepts a tenant override
  param.
- **Envelope encryption** — OAuth tokens stay encrypted at rest per
  overhaul spec §Security. Handlers decrypt at call time, never log
  plaintext tokens, never include tokens in `os_action_runs.error_detail`.
- **PII** — `response_payload` may include customer email/name (e.g.
  calendar event invitee); RLS-scoped storage. Error reports posted to the
  thread redact PII beyond what's necessary.
- **Usage meter** — actions count against the per-tenant API spend cap iff
  the action handler itself calls an LLM (rare; most actions are pure
  HTTP). Pure-HTTP actions are free.
- **Replay** — `(deliverable_id, action_type)` UNIQUE constraint prevents
  the same approval from creating two calendar events.

## Open Questions

- Gmail OAuth scope extension — `gmail.send` is sensitive; needs Google
  app verification re-review when added to the existing OAuth client.
  Owner: Aidan. Blocks: lead-nurture launch.
- Instagram Graph posting — requires Instagram Business account linked to
  a Facebook Page. Tenant onboarding gate. Owner: Aidan.
- CRM direct connectors (Salesforce, HubSpot) — deferred; Zapier is the
  v1 answer. Decision point: post-launch when first 5 tenants ask for it.
- Retry policy — exponential backoff vs manual-only? Build with
  manual-only; reconsider after observing failure modes.

## Out-of-Scope (defer)

- LinkedIn, X/Twitter posting — overhaul spec §Connector phase C; new
  OAuth apps required.
- Microsoft Graph (Outlook email, Word/Excel, OneDrive) — overhaul spec
  §Connector phase C.
- Outbound SMS via Twilio — defer pending compliance review.
- Paid social ads (Meta Ads Manager, Google Ads) — defer to post-launch.
- Direct CRM write (Salesforce, HubSpot, Pipedrive) — Zapier covers v1.

## Done criteria

- `os_action_runs` migration applied; foreign keys resolve.
- Calendar handler end-to-end test: booking deliverable → approve →
  Google Calendar event created in test calendar, deliverable shows
  `action_succeeded` + event URL.
- Email handler end-to-end test against Gmail sandbox; message-id returned.
- Facebook + Instagram + GBP handlers each have a happy-path test
  (mocked Graph API, verify request payload shape).
- Failure path test: connector expired → deliverable flips to
  `pending_action` with Settings banner trigger.
- Double-approve no-ops (idempotency proven).
- `DeliverablePanel.jsx` disables Edit when `status='action_running'`.

## Cross-refs

- `specs/agent-os-overhaul_spec.md` — parent spec; §Approval gates,
  §Security §OAuth token storage
- `plans/agent-os-next-steps_plan.md` §1 — operative connector grouping
- `backend/services/os_workers/__init__.py` — registry pattern this
  mirrors
- `backend/services/google_calendar.py` — booking handler infra
- `backend/routers/channels_facebook.py` — FB Page tokens for social handler
- `backend/routers/gbp.py` — GBP post handler infra
- `backend/routers/zapier.py` — CRM-via-Zapier outbound
- `backend/routers/os_deliverables.py` — approve/reject/edit endpoint that
  triggers action handlers
