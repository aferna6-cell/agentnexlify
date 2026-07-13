# Runbook: Provision INTEGRATIONS_ENC_KEY (+ Drive OAuth)

One-time owner action, ~5 minutes. Until this key exists in Railway:
- Drive KB sync returns 503 `encryption_key_required` on connect (by design —
  refresh tokens are never stored plaintext)
- Calendar/HubSpot OAuth token encryption (#266) stays dormant (dual-read
  keeps existing integrations working; prod has 0 integration rows today, so
  there is nothing to backfill yet)

## 1. Generate the key (locally, never commit it)

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output (44-char urlsafe base64 string ending in `=`).

## 2. Set it in Railway

Railway dashboard -> agentnexlify backend service -> Variables:

```
INTEGRATIONS_ENC_KEY=<the generated key>
```

Railway redeploys automatically on variable change.

## 3. Verify

```bash
# Drive auth endpoint should stop returning encryption_key_required.
# (It may still return drive_kb_not_configured until step 5 - that is the
# NEXT gate, and confirms the encryption gate cleared.)
curl -s https://agentnexlify-production.up.railway.app/api/v1/kb/integrations/drive/auth \
  -H "Authorization: Bearer <any dashboard token>"
```

## 4. Backfill existing plaintext secrets (only if integrations rows exist)

```bash
INTEGRATIONS_ENC_KEY=<key> python scripts/backfill_integration_encryption.py --dry-run
INTEGRATIONS_ENC_KEY=<key> python scripts/backfill_integration_encryption.py
```

As of 2026-07-13 prod `integrations` has 0 rows — skip unless that changed.

## 5. Drive OAuth credentials (to light up Drive KB sync)

Google Cloud Console -> the existing OAuth client (same one as calendar) ->
add authorized redirect URI:

```
https://agentnexlify-production.up.railway.app/api/v1/kb/integrations/drive/callback
```

Then in Railway (client id/secret are shared with calendar OAuth; only the
redirect is new):

```
GOOGLE_CLIENT_ID=<existing>
GOOGLE_CLIENT_SECRET=<existing>
GOOGLE_DRIVE_REDIRECT_URI=https://agentnexlify-production.up.railway.app/api/v1/kb/integrations/drive/callback
```

Also enable the Google Drive API for the project in Cloud Console
(APIs & Services -> Library -> Google Drive API -> Enable) and add the
`drive.readonly` scope to the OAuth consent screen if not already listed.

Verify end-to-end: dashboard Knowledge page -> "Connect Google Drive" ->
consent -> redirected back with `?drive=connected` -> pick a folder ->
first sync runs.

## Key rotation (later, when needed)

`integrations_enc_keys` holds older key versions as `"2:keyB,3:keyC"` while
`INTEGRATIONS_ENC_KEY` is always the current (version 1) key. To rotate:
move the current key into `INTEGRATIONS_ENC_KEYS` under the next version
number, set the new key as `INTEGRATIONS_ENC_KEY`, then re-encrypt rows with
the backfill script. Decrypt tries the version tag first, falls back to the
current key.

## Never

- Never commit the key or paste it into logs, issues, or chat
- Never delete the old key from `INTEGRATIONS_ENC_KEYS` until every row's
  version tag confirms re-encryption
