-- Migration 174: index hygiene — cover unindexed foreign keys + drop duplicate indexes
-- Source: Supabase performance advisors (2026-07-15).
--
-- WHY it matters for us (all backend traffic is service_role, so this is real,
-- not theoretical): Postgres does NOT auto-index foreign keys. Every `lead_id`
-- child table without a covering index gets seq-scanned when a lead is
-- deleted or merged (propose-only-records lead /merge flow) and on every join
-- that filters by the FK. 47 FKs were uncovered; the lead_id / conversation_id
-- / thread_id ones sit on real hot paths.
--
-- Part A self-detects (re-derives the uncovered-FK set), so it is idempotent
-- and safe to re-run. Part B drops the redundant plain index of each
-- identical-column duplicate pair, keeping the UNIQUE/constraint index.
-- Public schema only — auth.* and storage.* are Supabase-managed.

-- Part A: covering index on every single-column public FK that lacks one
DO $$
DECLARE
  r record;
  idx_name text;
BEGIN
  FOR r IN
    SELECT c.conrelid AS relid,
           c.conrelid::regclass::text AS tbl,
           a.attname AS col
    FROM pg_constraint c
    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
    WHERE c.contype = 'f'
      AND c.connamespace = 'public'::regnamespace
      AND array_length(c.conkey, 1) = 1
      AND NOT EXISTS (
        SELECT 1 FROM pg_index i
        WHERE i.indrelid = c.conrelid AND i.indkey[0] = c.conkey[1]
      )
  LOOP
    -- Deterministic, collision-proof name; trim to Postgres' 63-char limit.
    idx_name := left('idx_' || replace(r.tbl, '.', '_') || '_' || r.col || '_fk', 63);
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS %I ON %s (%I)',
      idx_name, r.tbl, r.col
    );
    RAISE NOTICE 'covered FK %.% with %', r.tbl, r.col, idx_name;
  END LOOP;
END $$;

-- Part B: drop the redundant plain index of each identical-column duplicate
-- pair (keep the UNIQUE/constraint index, which enforces integrity AND serves
-- the same lookups). All pairs below share an identical indkey — verified via
-- pg_index grouping on (indrelid, indkey, indpred, indexprs).
DROP INDEX IF EXISTS public.idx_clients_widget_api_key;          -- keep clients_widget_api_key_key (unique)
DROP INDEX IF EXISTS public.idx_business_hours_tenant;           -- keep uq_business_hours_tenant (unique)
DROP INDEX IF EXISTS public.idx_portal_tokens_token;             -- keep portal_tokens_token_key (unique)
DROP INDEX IF EXISTS public.idx_seo_profiles_tenant;             -- keep seo_profiles_tenant_id_key (unique)
DROP INDEX IF EXISTS public.idx_platform_monthly_revenue_month;  -- keep platform_monthly_revenue_month_key (unique)
DROP INDEX IF EXISTS public.idx_forms_public_token;              -- keep forms_public_token_key (unique)
DROP INDEX IF EXISTS public.idx_sms_opt_outs_lookup;             -- keep sms_opt_outs_client_id_phone_last10_key (unique)
DROP INDEX IF EXISTS public.os_tenant_usage_client_idx;          -- keep os_tenant_usage_client_id_cycle_start_key (unique)
DROP INDEX IF EXISTS public.integration_sync_log_client_idx;     -- keep idx_integration_sync_log_client_synced (advisor-flagged)
DROP INDEX IF EXISTS public.tenant_integrations_client_idx;      -- keep idx_tenant_integrations_client (advisor-flagged)
