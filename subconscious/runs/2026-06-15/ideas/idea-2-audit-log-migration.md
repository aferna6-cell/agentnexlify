### Idea 2: Create migration 149_audit_log.sql — unblock integration_key_vault auditing

**Evidence:** 9f9203d (2026-06-15) shipped Fernet AES-128-CBC encryption for ALL integration secrets (Instagram, Google, etc.) via integration_key_vault.py (242L). The `_write_audit()` method calls an `audit_log` table that does not exist — nightly review 87b5eb8 noted: "audit_log table doesn't exist yet; `_write_audit` is best-effort (warns, never blocks). Acceptable until audit_log lands." But "acceptable until" means now. Every encrypt/decrypt operation for every tenant's integration secret silently drops its audit entry.

**Action:** Create migrations/149_audit_log.sql — simple additive table: `(id uuid, tenant_id uuid FK tenants, event_type text, entity_type text, entity_id text, actor_ip text, metadata jsonb, created_at timestamptz)`. Apply via Supabase MCP. Requires RLS: tenant_id = auth.uid(). Zero code changes — integration_key_vault.py already calls `_write_audit()`.

**Impact:** Makes encryption audit trail operational for all tenants. Security compliance: decrypt/encrypt events become queryable. Addresses the one known gap in the new encryption feature flagged by nightly.

**Category:** code_health / operational
