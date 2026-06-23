# Schema Drift Audit — Issue #263 "24 pending migrations"

**Date:** 2026-06-23
**Author:** Claude (read-only audit, branch `claude/agent-nexlify-testing-28d597`)
**Scope:** `migrations/*.sql` vs live Supabase DB
**Linked Supabase project:** `pxserpybmajixqrmzaly` ("aferna6-cell's Project", ACTIVE_HEALTHY, us-east-1) — confirmed as the AgentNexLiFy production DB by table fingerprint (`leads`, `conversations`, `widget_configs`, `os_threads`, etc.).

> Other projects in the org (`qmlrecmgmqniitkplpqv` BetBrain, `oqmnnloktcwqeicnkqcy` agentnexlify-os-demo) are unrelated / INACTIVE and were not used.

---

## TL;DR

- The claimed **"24 pending migrations" is wrong.** The real count of unapplied schema is **2 migrations**.
- The migration-history table in Supabase is **incomplete and unreliable** as a drift signal: it records only **112** of **157** migration files, yet ~all of the "missing 45" objects already exist live (early baseline 001–048, plus many later files, were applied directly via SQL editor / `db reset` without being recorded). Drift must be measured by **object existence**, not by the history table.
- **2 genuine pending migrations** (objects verified absent live):
  - `117_zapier_api_keys.sql` — `tenant_api_keys.rate_limit_rpm`, `tenant_api_keys.notes` absent.
  - `129_chat_messages_os_mirror.sql` — `chat_messages.os_message_id` absent.
- Both are **SAFE-IDEMPOTENT** (pure `ADD COLUMN IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`, defaults present, no DROP, no un-defaulted NOT NULL backfill). Re-runnable with zero data risk.
- **2 duplicate migration-number collisions** in the file tree (not a live-DB problem, but a numbering-hygiene problem): `005` (×2) and `007` (×3).

---

## 1. File inventory

- **157** `.sql` files in `migrations/`.
- Highest sequential number: **154** (`154_conversation_sentiment_intent.sql`).
- 157 vs 154 explained entirely by duplicate-number collisions (3 extra files).

### Duplicate migration-number collisions

| Number | Files sharing it |
|--------|------------------|
| **005** | `005_appointments.sql`, `005_automation_sequences.sql` |
| **007** | `007_google_calendar_integration.sql`, `007_team_members.sql`, `007_webhooks.sql` |

All five objects exist live (`appointments`, `automation_sequences`, `integrations`/gcal, `team_members`, `webhooks`). The collision is cosmetic for the running DB but **breaks any tooling that keys on `NNN`** and is almost certainly part of what produced the bogus "24 pending" count. Recommend renumbering the later-authored duplicates in a follow-up (file-rename only — do NOT re-apply).

---

## 2. Migration-history vs reality

- Supabase `list_migrations` returns **112** entries.
- The history table is **not** a reliable applied-set: it omits the entire 001–024 baseline, 049–050, 059–064, 071–072, 075–085, 088, 091, 094–105 (most), 118–138 (most), 144, 146, 149–153 — yet the corresponding tables/columns are all present live.
- History entries are also inconsistently named: many lack the `NNN_` prefix (e.g. `widget_custom_instructions` = file 072, `kb_articles_and_sources` = file 081), and one is mislabeled — log entry `068_password_reset_tokens` corresponds to **file 085** (`068` is also legitimately the invoice-unique file). Number-based matching against the history table is therefore unsafe.

**Conclusion:** drift was determined by querying live `information_schema` / `pg_constraint` / `to_regclass`, not by diffing the history table.

---

## 3. Verification method

For every uncertain migration, the exact object name was read from the `.sql` file (not guessed) and then probed live. Representative spot-checks confirmed applied:

- Tables: `seo_audits` (049), `social_posts` (050), `invoice_item_templates` (059), `documents` (061), `service_types` (063), `client_accounts` (065), `email_sequences` (073), `kb_articles` (081), `waitlist_entries` (083), `scoring_configs` (084), `campaign_analytics_aggregates` (088), `admin_promotions` (089), `tenant_integrations` (109), `tenant_api_keys` (110), `platform_support_messages` (149), `tenant_usage_packs` (150), `audit_log` (151), all `os_*` tables (118–138).
- Columns: `leads.insurance_carrier` (062), `leads.date_of_birth` (064), `leads.enrichment_source` (105), `leads.qualification_json` (099), `tenants.reset_token` (085), `tenants.voice_ai_enabled` (143), `tenants.is_demo` (144), `tenants.pay_gate_exempt` (152), `tenants.stripe_trial_end` (153), `tenants.os_auto_send_enabled` (128), `tenants.os_auto_send_rules` (141), `widget_configs.enable_ai_fallback` (101), `widget_configs.enable_structured_lead_parser` (103), `widget_configs.custom_instructions` (072), `conversations.sentiment` (154), `conversations.notified_at` (146), `conversations.memory` (095), `documents.kind` (100), `os_threads.source` (124), `integrations.access_token_enc` (148).
- Constraint: `tenants_business_type_check` includes `financial_services` (142) — applied.
- Invariants intact live: `leads.client_id`, `leads.status`, `leads.areas_of_interest` all present (schema-discipline rules hold).

> Note: several first-pass probes used wrong column names and produced false "missing" hits (e.g. `insurance_provider` vs real `insurance_carrier`; `ai_fallback_enabled` vs `enable_ai_fallback`; `os_auto_send` vs `os_auto_send_enabled`). All were re-probed with the exact names from the migration files and resolved to **applied**. Only the two below survived correct-name verification.

---

## 4. Genuine pending migrations (per-migration classification)

| Migration file | Object(s) | Live status | Classification | Risk |
|---|---|---|---|---|
| `117_zapier_api_keys.sql` | `tenant_api_keys.rate_limit_rpm` (int NOT NULL DEFAULT 100), `tenant_api_keys.notes` (text), idx `idx_tenant_api_keys_prefix`, idx `idx_tenant_api_keys_client` | **ABSENT** (both columns = 0) | **SAFE-IDEMPOTENT** | Low — all `IF NOT EXISTS`; NOT NULL column has a default; base table exists and has 0 rows |
| `129_chat_messages_os_mirror.sql` | `chat_messages.os_message_id` (UUID NULL) | **ABSENT** (= 0) | **SAFE-IDEMPOTENT** | Low — single nullable column, `ADD COLUMN IF NOT EXISTS`; `chat_messages` has 2,717 rows but new col is NULL-able with no backfill |

No RISKY or NEEDS-REVIEW migrations among the pending set. No `DROP`, no data backfill, no un-defaulted `NOT NULL` on a populated table.

---

## 5. Ordered reconcile plan

Both pending migrations are independent (different tables) and idempotent. Recommended order:

1. **`129_chat_messages_os_mirror.sql`** — apply first. Adds `chat_messages.os_message_id`; the OS outbound mirror (already live via 130 `os_outbound_log`) references this column, so it is the higher-impact gap. Single nullable column, instant.
2. **`117_zapier_api_keys.sql`** — apply second. Adds Zapier rate-limit + notes columns and indexes to `tenant_api_keys` (0 rows live → trivial).

**Apply mechanism (OWNER-GATED — do NOT auto-apply):**
- This is a READ-ONLY audit. Prod application requires owner sign-off per CLAUDE.md Rule 8 (no half migrations) and the migration-workflow skill.
- When approved, apply via `mcp__supabase__apply_migration` against `pxserpybmajixqrmzaly`, one migration per call, then re-probe the two objects to confirm, then update `docs/dev-knowledge/schema-log.md`.
- Both are idempotent, so a re-run is safe if status is uncertain.

### Follow-up (separate session, not blocking #263)

- **Renumber duplicate-number files** (`005`, `007` collisions) — file-rename only, no re-apply. Pick the next free numbers (155+) for the later-authored duplicates and update any tooling/index that references them.
- **Stop trusting the Supabase migration-history table for drift detection.** The "24 pending" claim came from diffing files against an incomplete history table. Drift checks should query live `information_schema` (the existing `check_plan_drift.py` / migration-workflow approach), not the history log.
- Consider backfilling the history table so file count and recorded count converge (optional; cosmetic).

---

## 6. Answer to Issue #263

- Claimed pending: **24**. Actual pending: **2** (`117`, `129`).
- Root cause of the inflated number: (a) the Supabase migration-history table records only 112/157 files because the baseline + many later migrations were applied out-of-band, and (b) two duplicate-number collisions (`005`, `007`) break number-keyed diff tooling. Neither indicates real schema loss.
- Real drift is limited to two safe, idempotent column-add migrations. Prod apply is owner-gated.
