# Runbook — Activate Missed-Call Text-Back for MTOptions

**Tenant:** MTOptions
**Tenant ID:** `6d76f24b-dd71-470c-9b86-03ee35b7e887`
**Plan:** enterprise
**Status (2026-05-01):** code shipped, never activated. 0 of 6 tenants have `textback_enabled=true`. 0 textbacks ever sent.

## Prereqs (collect before starting)

| Item | Source | Used in |
|------|--------|---------|
| Owner phone for SMS notifications | MTOptions owner | `tenants.notification_phone` |
| Textback message override (optional) | MTOptions owner — keep default if none | `tenants.textback_message` |
| Twilio account SID + auth token | Twilio console | Backend env (prod already wired) |
| Dedicated Twilio number for MTOptions | Twilio console | Voice webhook target |
| Quiet hours window (optional) | MTOptions owner | `tenants.textback_quiet_start`, `tenants.textback_quiet_end` |

Confirm prod env already has: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` (per-tenant override possible — verify with backend before relying on global default).

## Step 1 — Buy Twilio number for MTOptions

1. Twilio console → Phone Numbers → Buy a Number
2. Pick local number in MTOptions market
3. Capability required: **Voice + SMS**
4. Note the E.164 number, e.g. `+19145551234`

## Step 2 — Wire voice webhook → backend

1. Twilio console → Phone Numbers → Active Numbers → click new MTOptions number
2. **Voice & Fax** section:
   - **A CALL COMES IN**: Webhook
   - URL: `https://api.agentnexlify.com/api/v1/twilio/missed-call` (verify exact prod hostname before saving)
   - HTTP: `POST`
3. **Status callback URL** (optional but recommended): same URL
4. Save

Note: webhook handler at `backend/routers/twilio_webhooks.py:211` performs Twilio signature verification + 5-min replay window check. Signature uses `TWILIO_AUTH_TOKEN` — must match the Twilio account that owns the number.

## Step 3 — Enable in DB (Supabase prod)

Run via Supabase SQL editor or `mcp__supabase__execute_sql`:

```sql
UPDATE tenants
SET
  textback_enabled = true,
  notification_phone = '+1XXXXXXXXXX',          -- MTOptions owner phone, E.164
  textback_message  = COALESCE(textback_message,
    'Hi! Sorry we missed your call at {business_name}. How can we help? Reply here and we''ll get back to you right away.'),
  textback_quiet_start = NULL,                  -- or '21:00' for 9 PM start
  textback_quiet_end   = NULL                   -- or '08:00' for 8 AM end
WHERE id = '6d76f24b-dd71-470c-9b86-03ee35b7e887';

-- verify
SELECT id, business_name, textback_enabled, notification_phone, textback_message,
       textback_quiet_start, textback_quiet_end
FROM tenants
WHERE id = '6d76f24b-dd71-470c-9b86-03ee35b7e887';
```

The handler also checks the `automations` row; MTOptions already has `automations.type='missed_call_textback'` with `is_enabled=true` (verified 2026-05-01). No change needed there.

## Step 4 — Test live

1. From a personal cell (NOT the owner's notification phone — handler ignores self-calls), call the MTOptions Twilio number
2. Hang up before voicemail or after 1 ring
3. Within ~10 seconds, expect SMS from the Twilio number to the calling phone with the textback message
4. Verify DB:
   ```sql
   SELECT * FROM missed_call_texts
   WHERE tenant_id = '6d76f24b-dd71-470c-9b86-03ee35b7e887'
   ORDER BY created_at DESC
   LIMIT 5;

   SELECT * FROM activity_log
   WHERE tenant_id = '6d76f24b-dd71-470c-9b86-03ee35b7e887'
     AND activity_type = 'missed_call_textback'
   ORDER BY created_at DESC
   LIMIT 5;
   ```
5. Verify dashboard: MTOptions login → Dashboard → AutomationActivityCard shows the new event

## Step 5 — Notify MTOptions

Email/text owner:
- Number is live
- Quiet hours setting (if any)
- Where to view activity (dashboard URL)
- How to disable (settings page or contact support)

## Rollback

If anything goes wrong, single-statement disable:

```sql
UPDATE tenants
SET textback_enabled = false
WHERE id = '6d76f24b-dd71-470c-9b86-03ee35b7e887';
```

Twilio webhook can stay configured — `textback_enabled=false` short-circuits at `twilio_webhooks.py:274`. No SMS sent, no DB writes for textback.

## Failure modes to watch

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| No SMS sent, no `missed_call_texts` row | webhook signature fail | Confirm `TWILIO_AUTH_TOKEN` matches account owning the number |
| Webhook 200 but no SMS | Twilio number lacks SMS capability | Re-buy number with Voice + SMS |
| SMS sent to wrong recipient | caller ID anonymous / blocked | Handler logs + skips; expected |
| Multiple SMS for one call | Twilio retry; handler should idempotent-skip via 5-min replay window | Verify only one row in `missed_call_texts` per `call_sid` |
| Quiet hours not respected | bad timezone | `tenants.timezone` must be set; defaults to UTC |

## Cross-refs

- Webhook handler: `backend/routers/twilio_webhooks.py:211-402`
- Tenant config columns: `backend/routers/auth.py:1142` (allowed updates)
- Activity logging: `activity_log` table, `activity_type='missed_call_textback'`
- Dashboard surface: `frontend/src/pages/Dashboard/AutomationActivityCard.jsx`
- Schema: `migrations/111_missed_call_texts.sql`

## Audit gap (informational)

The 6 tenants currently have `automations.type='missed_call_textback' AND is_enabled=true` rows but `tenants.textback_enabled=false`. Two-source-of-truth split. Webhook reads `tenants.textback_enabled`, so the `automations` row is decorative until the tenant flag flips. Consider: future PR to either consolidate (single source) or auto-sync on settings save.
