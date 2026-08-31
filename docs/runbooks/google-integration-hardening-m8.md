# Google Integration Hardening — Milestone 8

One focused pass to unblock Calendar + Gmail staging proof without incremental OAuth retry PRs.

## What changed in code (main)

| Area | Change |
|------|--------|
| Gmail OAuth | Default connect requests **`gmail.send` only** (M8 send path). `gmail.modify` removed — no code used it. |
| Gmail inbox | **`gmail.readonly`** only when `GMAIL_INBOX_ENABLED=1` **and** connect uses `?inbox=1`. Inbox poll skips send-only connections. |
| M8 smoke | `agent_os_e2e.db_lead_verification` resolves lead by **execution id / name marker**, not assumed email. |
| Encryption gate | `scripts/m8_verify_integrations_enc.py` — prove `INTEGRATIONS_ENC_KEY` round-trip before OAuth. |

## Owner sequence (do in order)

### 1. Dedicated staging Google Cloud project

Do **not** use the Clemson-managed project for staging OAuth.

1. Create **AgentNexLiFy Staging** GCP project (you control credentials).
2. OAuth consent screen: **External → Testing**.
3. Add your harmless Google account as **Test user**.
4. Create OAuth **Web client** with **exact** redirect URIs:
   - `https://agentnexlify-staging.up.railway.app/api/v1/integrations/google/callback`
   - `https://agentnexlify-staging.up.railway.app/api/v1/integrations/gmail/callback`
5. Enable **Google Calendar API** + **Gmail API**.

### 2. Railway staging variables

Set on staging service only (not production):

```
GOOGLE_CLIENT_ID=<staging web client id>
GOOGLE_CLIENT_SECRET=<staging web client secret>
GOOGLE_REDIRECT_URI=https://agentnexlify-staging.up.railway.app/api/v1/integrations/google/callback
GMAIL_REDIRECT_URI=https://agentnexlify-staging.up.railway.app/api/v1/integrations/gmail/callback
INTEGRATIONS_ENC_KEY=<44-char Fernet key — see ops/docs/runbook-integrations-enc-key.md>
```

Leave **`GMAIL_INBOX_ENABLED` unset** for M8 (send-only Gmail). Do **not** apply migration 176 until encryption is proven.

### 3. Verify encryption before OAuth

```bash
# Local (key in .env.staging)
python3 scripts/m8_verify_integrations_enc.py
```

After Railway redeploy with the key, connect Calendar or Gmail once, then confirm staging `integrations` rows have **`access_token_enc`** populated (not plaintext-only).

### 4. Connect integrations (staging smoke tenant)

Log in as `smoke-test@agentnexlify.invalid` on staging (or use minted auth URLs).

- **Calendar:** `/api/v1/integrations/google/auth` → consent → Connected HTML.
- **Gmail (send-only):** `/api/v1/integrations/gmail/connect` → consent → Connected HTML.

Expect **`connected: true`** on both status endpoints and rows in `integrations` for the smoke tenant.

### 5. Live smoke

```bash
M8_SMOKE_SUITES=calendar,gmail,agent_os_e2e,isolation,rag,crm python3 scripts/m8_live_smoke.py
```

## M8 COMPLETE criteria

- Calendar: OAuth + free/busy + create/read-back/cancel + external-attendee approval path (no duplicate on redrive).
- Gmail **send**: OAuth (send scope) + propose → approve → send → verify.
- Gmail **inbox**: optional post-M8; requires restricted-scope verification + `GMAIL_INBOX_ENABLED=1`.

## Parallel track (post-M8)

Run Google's **restricted-scope verification** for `gmail.readonly` while Milestone 9 starts. Inbox monitoring stays off until approved.

## Cross-refs

- `ops/docs/runbook-integrations-enc-key.md` — key generation
- Issue **#536** — encryption prerequisite for migration 176
- PR **#719** (merged `6c1eecdf`) — staging Supabase credentials + PKCE fix
