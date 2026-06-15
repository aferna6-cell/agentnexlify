# Nightly Commit Review — 2026-06-15

**Run:** automated nightly, 2026-06-15 UTC  
**Commits reviewed:** 4  
**Issues found:** 0 (no action required)

---

## Commits

### 1. `65a8a40` — python-multipart 0.0.26 → 0.0.27 | Risk: LOW

Dependabot patch bump. No code changes beyond `backend/requirements.txt`. No action.

### 2. `01fa4e5` — sentry-sdk 2.20.0 → 2.58.0 | Risk: LOW

Dependabot minor-series bump (38 minor releases). Usage in `backend/main.py:133-142` is
standard: `sentry_sdk.init()` with `FastApiIntegration()` + `StarletteIntegration()`, stable
API surface. `send_default_pii=False` correct. CI tested via dependabot PR. No action.

**Observation:** Large gap (2.20 → 2.58). Monitor Sentry dashboard after next deploy for any
init errors. Not a blocker.

### 3. `9f9203d` — Encrypt integrations secrets at rest | Risk: HIGH (reviewed, no action)

Security feature. Full review performed.

**Design verified correct:**
- Fernet (AES-128-CBC + HMAC-SHA256) via `cryptography` — authenticated encryption, fail-closed
- Wrong key / tampered ciphertext → `IntegrationKeyVaultError` raised, never silently returns empty
- Missing key → raises (fail closed), no default-key fallback
- Plaintext never logged — only `tenant_id + provider` in INFO lines
- `save_integration_key` writes only `access_token_enc` (BYTEA); never touches `access_token` (plaintext column retained per Rule 8 until sunset migration)
- Schema: migration 148 additive only (BYTEA columns + pgcrypto ext); RLS untouched
- `integrations` table uses `tenant_id` — correct (only `leads` + `conversations` use `client_id`)
- No `from __future__ import annotations` in any new file — PASS
- 100% line+branch test coverage gate in CI

**Residual notes (awareness only):**
- `audit_log` table doesn't exist yet; `_write_audit` is best-effort (warns, never blocks). Acceptable until audit_log lands.
- FastAPI cap to `<0.136` in `requirements.txt` is a pre-existing regression fix bundled here. Worth revisiting when Starlette 0.49.x + FastAPI compatibility is resolved upstream.

No bugs. No action required.

### 4. `cfdd6e3` — Launch-readiness batch 2 | Risk: MEDIUM (reviewed, no action)

Four sub-changes:

**CI eval wiring (`#110`):** lead-qualifier eval was pointing at non-existent `lead_qualifier.py`
(real file: `lead_qualification.py`). Fixed. New offline structural gate (`test_lead_qualifier_structure.py`)
runs blocking on every PR. Live golden eval now Monday-cron-only (non-blocking). Correct.

**Schema-log resolution (`#2,#5`):** 22 stale `Applied: Pending` markers flipped to `Applied`
after live Supabase introspection. One migration (147) confirmed genuinely pending. No schema
drift. Correct.

**Email sequences N+1 fix (`#112, #113`):** `list_sequences` replaced O(N) per-sequence DB count
calls with two bulk queries + Python tally. `_count_by_sequence_id` helper verified:
- Fetches `sequence_id` column only for tenant's own `seq_ids` (already tenant-scoped upstream)
- No tenant isolation risk — cross-tenant leakage not possible
- Syntax + compile: PASS

`_process_pending_sends` and `run_sequence_processor` refactored to share logic.
Compile + parse: PASS.

**Frontend tests:** `AgentQualifierSettings.test.jsx` + `IntegrationHealthDashboard.test.jsx` added.
Standard Vitest + testing-library pattern. No issues.

No bugs. No action required.

---

## Summary

All 4 commits clean. No LOW-risk bugs auto-fixed. No GH issues created. Codebase healthy.

**Next watch:** sentry-sdk 2.58 runtime behaviour post-deploy; audit_log table for vault audit writes.
