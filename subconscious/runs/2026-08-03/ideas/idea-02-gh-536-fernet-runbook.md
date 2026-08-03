# Idea 02 — GH #536 Fernet Key Provisioning Runbook Comment

**Evidence:**
- `ops/routines/logs/morning-digest-2026-08-03.md` top priority: "Unblock #536 — Provision INTEGRATIONS_ENC_KEY in Railway. Migration 176 cannot land until this is done. High-risk infra blocker, 13 days open."
- `migrations/176_sunset_plaintext_integration_tokens.sql` exists — this migration encrypts all plaintext tokens using Fernet. Cannot apply without key.
- `backend/services/connector_registry.py` (PR #619, b67710c): imports `from cryptography.fernet import Fernet` — all new connector credential storage depends on this encryption. Full connector auth unusable until migration 176 lands.
- Zero action in 14 days (as of 2026-08-03) — human may be deferring due to not knowing exact steps.

**Idea:** Post a specific step-by-step comment on GH #536:
```
To provision INTEGRATIONS_ENC_KEY in Railway:
1. Railway dashboard → project → Variables tab → Add Variable
2. Name: INTEGRATIONS_ENC_KEY
3. Value: (run locally) python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
4. Save, redeploy service
5. Apply: migrations/176_sunset_plaintext_integration_tokens.sql via Supabase MCP
```

**Expected impact:** Unblocks migration 176 + full connector credential encryption. Reduces human friction from "figure out how" to "3 steps, 5 minutes."

**Effort:** XS (one GitHub comment)
**Confidence:** MEDIUM (human must still act; comment reduces friction, doesn't guarantee action)
**Autonomous:** NO (requires human to provision Railway variable)
**Blocker dependency:** GH #536 (14 days open)
