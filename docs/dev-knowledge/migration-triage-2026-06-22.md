# Migration Triage — 2026-06-22 (re: GH #263, #329)

Read-only audit of `migrations/*.sql` vs the applied migration history on the active Supabase
project `pxserpybmajixqrmzaly` (org VoltOps). No migrations were applied.

## Headline

**The "24 pending migrations" alarm (#263) is largely a false positive caused by tracking
artifacts, not real schema drift.** A number-based diff is unreliable here. Verify by object
existence, not by file number.

## Evidence

- Applied migration history: **112 tracked entries**, oldest `20260315132516` (≈ migration
  033). Migrations **001-024 predate Supabase migration tracking** — they were applied before
  the history table existed, so they show as "missing" by number but their objects exist.
- Many migrations are recorded under **free-form version names without the `NNN_` prefix**, so
  a numeric diff counts them as pending when they are applied. Examples:
  - `108` → `photo_quote_tables_108` (applied)
  - `109` → `tenant_integrations_109` (applied)
  - `110` → `tenant_api_keys_110` (applied)
  - `133` → `os_graph_memory` (applied) · `145` → `145_push_subscriptions` (applied)
- A naive numeric set-diff reports **90** "pending" file numbers — clearly wrong (it includes
  001-024 and dozens applied under other names).

## Live-schema cross-check (from `list_tables`, 2026-06-22)

Headline "pending-by-number" migrations are confirmed **applied** by the presence of their
objects in the live DB:

| Migration | Object | Present? |
|---|---|---|
| 114/116 idempotency | `idempotency_keys` | ✅ |
| os_graph_memory (133) | `os_graph_nodes`, `os_graph_edges` | ✅ |
| 145 push_subscriptions | `push_subscriptions` | ✅ |
| audit_log | `audit_log` | ✅ |
| usage_packs | `tenant_usage_packs` | ✅ |
| pricing_ab_events | `pricing_ab_events` | ✅ |
| 154 sentiment/intent | tracked applied `20260618135149` | ✅ |
| 102 marketing_addon | applied **then dropped** (`drop_marketing_addon_columns`) | ✅ (intentionally reverted) |

## #329 — apply migration 154 to production

Migration `154_conversation_sentiment_intent` **is applied** on the active project
`pxserpybmajixqrmzaly`. If that project is production, **#329 is already resolved** — confirm
which Supabase project the Railway backend's `SUPABASE_URL` points at, then close #329.

## Recommendation (the durable fix for #263)

Stop triaging by file number. Add a deterministic object-existence audit:
for each `migrations/NNN_*.sql`, parse its `CREATE TABLE` / `ADD COLUMN` / `CREATE INDEX`
targets and check them against `information_schema` on the live DB. Output: a precise list of
migrations whose objects are genuinely missing. This kills the recurring "N pending??" false
alarm. (Same Management-API-SQL pattern as `brain/_tools/refresh_connectors.py`.)

Until that exists, treat #263's count as **needs object-level verification**, not 24 real gaps.

## Items that still warrant a real check
- Confirm prod `SUPABASE_URL` project → close #329 if 154 is there.
- Spot-check any migration that adds a **column** (not a table) — column adds are the most
  likely to be genuinely un-applied while the table still exists (e.g. `referral_columns`,
  `tenants_os_auto_send`, `pay_gate_exempt`). These were tracked as applied here, but a column
  audit is the only way to be sure across environments.
