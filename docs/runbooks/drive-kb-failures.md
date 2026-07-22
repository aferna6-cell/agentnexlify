# Runbook — Drive-KB Sync Failures

Operational playbook for the Google Drive knowledge-base integration
(`backend/services/drive_kb_sync.py`, `backend/routers/kb_integrations.py`).
Every DB touch in the sync path is fail-open, so a failure degrades a single
tenant's sync — it never stalls the automation loop or blocks the dashboard.

Related: KB `knowledge-base/wiki/integrations/drive-kb-onboarding.md`,
ADR-2026-07-22-001.

## Symptom → cause → action

### OAuth token expired / revoked
- **Symptom:** dashboard sync log shows repeated errors; `/status` returns
  `connected: true` but syncs stop adding files. `last_sync_status` is an error.
- **Cause:** the tenant revoked access in their Google account, or the refresh
  token was invalidated (password reset, security event). Refresh flow can no
  longer mint an access token.
- **Action:** the tenant re-connects from Knowledge → Connect Google Drive
  (`/auth` → consent → `/callback`). The folder selection is preserved where
  possible; if not, re-pick the folder. No data is lost — already-synced
  documents remain in the knowledge base.

### Google Drive API down / 5xx / rate-limited (429)
- **Symptom:** one or more tenants' syncs error in `integration_sync_log`;
  errors clear on the next daily pass.
- **Cause:** transient Google API outage or per-app quota exhaustion.
- **Action:** none required for a single bad pass — the diff-based sync retries
  on the next cadence and the fail-open wrapper keeps other tenants syncing. If
  errors persist across multiple passes for ALL tenants, check the Google Cloud
  project quota and the OAuth app status. Downloads use exponential backoff on
  429; a sustained 429 means the project needs a quota increase.

### Drive folder deleted or unshared
- **Symptom:** sync log shows the folder listing failing (409/empty); no new
  files sync.
- **Cause:** the tenant deleted, moved, or unshared the folder that was
  selected as the KB source.
- **Action:** the tenant re-picks a valid folder via the folder picker
  (`/folders` → `/folder`). Previously synced documents stay in the KB until
  the tenant removes them; disconnecting Drive also leaves them in place.

### Encryption key rotation (INTEGRATIONS_ENC_KEY)
- **Symptom:** planned maintenance; not a failure.
- **Cause:** rotating the Fernet key that protects stored provider tokens.
- **Action:** add the new key version alongside the old (the vault supports
  versioned keys), re-encrypt stored tokens to the new version, then retire the
  old version. Do NOT drop the old key until every stored token is re-encrypted,
  or existing connections fail closed on the next refresh. Coordinate with the
  integrations-secret encryption work (issue #266); the enc key must be
  provisioned in Railway before any live token operations.

### Tier limit hit (documents beyond plan cap)
- **Symptom:** sync log shows files skipped; document count on the dashboard is
  pinned at the tier cap (Free 10 / Growth 100 / Pro unlimited).
- **Cause:** the connected folder holds more documents than the tenant's plan
  allows.
- **Action:** expected behavior, not a failure. Files beyond the cap are skipped
  and logged, not errored. The tenant upgrades the plan, or trims the folder to
  fit the cap. Upgrading raises the cap on the next sync automatically.

## Escalation
Alert fires after 3 consecutive sync errors for a single tenant. Check the
tenant's `integration_sync_log` error column first; most causes above are
tenant-side (revoked access, deleted folder) and resolve with a re-connect or
re-pick, not a code change.
