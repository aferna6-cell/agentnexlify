# Agent OS — Act (Group B) Live Verification Runbook

Status of Group B is "builds + 61 tests pass." That is not "sends a real email to a
real lead." This runbook closes that gap: one live round-trip per action handler
against real provider credentials, in staging, with a known tenant.

Scope: the 8 registered action handlers under `backend/services/os_actions/`.
Source of truth for behavior: `backend/tests/test_os_actions.py` (61 tests).

> Do NOT run this from an ephemeral dev container with no creds — it will fail at
> the `connector` stage and prove nothing. Run against staging (Railway) with the
> tenant integrations actually connected.

---

## How an action runs (the path you are verifying)

```
deliverable (pending_approval, os_agent_runs row)
  → POST /api/v1/os/deliverables/{run_id}/approve   (auth: tenant JWT)
  → run_action() scheduled via BackgroundTasks
  → handler._run(ctx): Haiku extracts payload → validate → pick provider → send
  → os_action_runs row: status running → succeeded | failed
```

Inspect endpoints (all under `/api/v1/os`, tenant-scoped by JWT `tenant_id` claim):

| Action | Endpoint |
|---|---|
| List registered actions | `GET /actions/registered` |
| List pending deliverables | `GET /deliverables/pending` |
| Approve (triggers action) | `POST /deliverables/{run_id}/approve` |
| Check a run | `GET /action-runs/{action_run_id}` |
| Retry a failed run | `POST /action-runs/{action_run_id}/retry` |

A succeeded `os_action_runs` row has `status='succeeded'`, a `response_payload`,
and `error_detail=null`. A failed row has `status='failed'` and an
`error_detail` whose `stage` tells you where it broke (`extract`, `validate`,
`connector`, or a provider stage like `m365` / `gbp_api` / `ig_publish`).

Idempotency: a partial unique index on `(deliverable_id, action_type) WHERE
status='succeeded'` blocks a second successful run for the same deliverable.
Re-approving an already-succeeded deliverable is a no-op by design — verify the
preflight returns the existing run rather than double-sending.

---

## Pre-flight (once per environment)

1. Pick a known staging tenant. Record its `client_id`.
2. Use a test recipient you control (your own email / phone / a sandbox page).
3. Confirm the registry sees all 8: `GET /actions/registered` returns
   `calendar.event.create, crm.contact_upsert, email.send, gbp.post, sms.send,
   social.facebook.post, social.instagram.post, widget.message`.

---

## Per-handler procedure

For each handler: connect the connector, create/approve a deliverable, then assert
the `os_action_runs` row AND the real provider-side effect.

### 1. email.send  (`email.py`)
- **Provider dispatch:** `m365` if the tenant has an M365 integration, else
  `resend` (platform `RESEND_API_KEY`). `required_connectors=[]` — Resend is the
  always-available fallback.
- **Creds:** M365 path needs the tenant's M365 integration row (Mail.Send scope).
  Resend path needs `RESEND_API_KEY` set on the backend.
- **Deliverable:** an `email.send` deliverable whose body contains a recipient +
  message (Haiku extracts `to`, `subject`, `body`).
- **Expected run row:** `status='succeeded'`, `response_payload.provider` is
  `m365` or `resend`.
- **Provider-side effect:** real email lands in the test inbox. Check From, subject,
  body.
- **Rollback:** none needed (email is one-way). Note the run id.

### 2. sms.send  (`sms.py`)
- **Provider dispatch:** `twilio_byo` if tenant has a Twilio integration, else
  `twilio_platform` (`TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` /
  `TWILIO_PHONE_NUMBER`). `required_connectors=[]`.
- **Deliverable:** `sms.send` with a recipient in E.164 (`^\+[1-9]\d{7,14}$`) +
  body.
- **Expected run row:** `status='succeeded'`, `response_payload.provider` is
  `twilio_byo` or `twilio_platform`.
- **Provider-side effect:** real SMS to the test phone.
- **Rollback:** none (SMS is one-way). Use a phone you own.

### 3. calendar.event.create  (`calendar.py`)
- **Provider dispatch:** `google` (google_calendar integration) else `m365`
  (m365_calendar). `required_connectors=["google_calendar", "m365_calendar"]` —
  if NEITHER is connected the run fails at `stage='connector'`.
- **Creds:** one of the two calendar integrations connected for the tenant.
- **Deliverable:** `calendar.event.create` with title + start time (defaults to a
  60-minute event).
- **Expected run row:** `status='succeeded'`, `response_payload` has the created
  event id/link.
- **Provider-side effect:** event appears on the connected calendar.
- **Rollback:** delete the created event from the calendar (capture event id from
  `response_payload`).

### 4. crm.contact_upsert  (`crm.py`)
- **Provider dispatch:** writes a lead to our own DB via `tenant_scope` helpers
  (`status='new'`, `source='agent_os'`, `areas_of_interest`). `required_connectors=[]`.
  Optional HubSpot push if the tenant has a `hubspot_tenant` integration — a push
  failure HARD-FAILS the action while preserving `lead_id`.
- **Deliverable:** `crm.contact_upsert` with a contact (email and/or phone).
- **Expected run row:** `status='succeeded'`, `response_payload.lead_id` set.
  Dedup: same email (then phone) updates the existing lead instead of inserting.
- **Provider-side effect:** `leads` row exists with `client_id` = the tenant,
  `status='new'`. If HubSpot connected, contact exists in HubSpot too.
- **Rollback:** delete the test `leads` row by `lead_id`; remove HubSpot test
  contact if pushed.

### 5. gbp.post  (`gbp.py`)
- **Provider dispatch:** Google Business Profile. `required_connectors=
  ["google_business_profile"]` — integration row keyed on `integrations.tenant_id`
  with `access_token`, `account_id`, `location_id`. Missing → `stage='connector'`.
- **Deliverable:** `gbp.post` with a non-empty summary (empty → `stage='validate'`).
- **Expected run row:** `status='succeeded'`, `response_payload.name` ends in
  `/localPosts/{id}`.
- **Provider-side effect:** local post visible on the Business Profile.
- **Rollback:** delete the local post via GBP API or console.

### 6. social.facebook.post  (`social_facebook.py`)
- **Provider dispatch:** FB Graph `POST /{page_id}/feed`. `required_connectors=
  ["facebook"]` — `integrations` row provider=`facebook` with `page_id` +
  `access_token`. Missing → `stage='connector'`.
- **Deliverable:** `social.facebook.post` with message text.
- **Expected run row:** `status='succeeded'`, `response_payload` has the post id.
- **Provider-side effect:** post on the FB Page feed.
- **Rollback:** delete the post from the Page.

### 7. social.instagram.post  (`social_instagram.py`)
- **Provider dispatch:** two-step Graph — `POST /{ig_user_id}/media` (create
  container) then `POST /{ig_user_id}/media_publish`. `required_connectors=
  ["instagram"]` — integration row provider=`instagram`, OR provider=`facebook`
  with `instagram_business_account_id`. Missing → `stage='connector'`.
- **Creds note:** `image_url` MUST be `https://` (non-HTTPS → `stage='validate'`).
  IG cannot post a local/data image — host the test image on a public HTTPS URL.
- **Deliverable:** `social.instagram.post` with caption + public HTTPS image_url.
- **Expected run row:** `status='succeeded'`, `response_payload.media_id` and
  `response_payload.creation_id` set. Failure stages: `ig_create_container`
  (container leg) vs `ig_publish` (publish leg) — they pinpoint which Graph call
  broke.
- **Provider-side effect:** photo post on the IG business account.
- **Rollback:** delete the IG post.

### 8. widget.message  (`widget.py`)
- **Provider dispatch:** writes an assistant message to `chat_messages`
  (`tenant_id`, `role='assistant'`, content ≤4000 chars). `required_connectors=[]`.
  Needs a resolvable `session_id` (from deliverable.session_id, metadata, or the
  agent_run thread context).
- **Deliverable:** `widget.message` tied to a real widget session.
- **Expected run row:** `status='succeeded'`; a new `chat_messages` row for that
  session.
- **Provider-side effect:** message appears in the live widget conversation for
  that session.
- **Rollback:** delete the test `chat_messages` row.

---

## Pass criteria (all 8)

A handler PASSES live verification when:
1. `os_action_runs.status='succeeded'` with the expected `response_payload` shape.
2. The real provider-side effect is observed (inbox / phone / calendar / page /
   DB row).
3. Re-approving the same deliverable does NOT double-send (idempotency index
   holds).
4. With the connector deliberately disconnected, the run fails at
   `stage='connector'` (negative check — proves the cred guard, not a silent send).

Record results in a table (date, tenant, run id, provider, PASS/FAIL) and attach to
the Group B hardening issue. Until all 8 rows are PASS, "Act works" is unproven.

---

## Failure triage by stage

| `error_detail.stage` | Meaning | Fix |
|---|---|---|
| `extract` | Haiku could not parse a payload from the deliverable body | Check deliverable body has the required fields in plain language |
| `validate` | Payload failed a format guard (bad email/phone, empty summary, non-HTTPS image) | Fix the deliverable content |
| `connector` | Required integration row missing for the tenant | Connect the provider; confirm `integrations` row exists |
| `m365` / `resend` / `twilio_byo` / `twilio` / `gbp_api` / `fb_api` / `ig_create_container` / `ig_publish` | Provider call returned an error | Read `error_detail.message` + `status_code`; check creds/scopes/rate limits |

## Cross-refs
- Handlers: `backend/services/os_actions/*.py`
- Registry + run path: `backend/services/os_actions/__init__.py`
- Approval routes: `backend/routers/os_deliverables.py`
- Tests: `backend/tests/test_os_actions.py`
- Plan: `plans/agent-os-north-star_plan.md` §3 gap #1
