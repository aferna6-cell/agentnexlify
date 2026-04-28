-- 117_zapier_api_keys.sql
-- Zapier CRM export — named alias migration for zapier API keys
-- Adds rate_limit_rpm and notes columns to tenant_api_keys table.
-- The base table was created in 110_tenant_api_keys.sql.
-- Issue: #58

-- Add rate limit column (100 req/min per key per spec)
alter table tenant_api_keys
  add column if not exists rate_limit_rpm integer not null default 100;

-- Add notes column for future use
alter table tenant_api_keys
  add column if not exists notes text;

-- Ensure the prefix index exists (idempotent — may have been created in 110)
create index if not exists idx_tenant_api_keys_prefix
  on tenant_api_keys(key_prefix)
  where revoked_at is null;

create index if not exists idx_tenant_api_keys_client
  on tenant_api_keys(client_id);

-- =============================================================
-- Rollback (commented)
-- =============================================================
-- alter table tenant_api_keys drop column if exists rate_limit_rpm;
-- alter table tenant_api_keys drop column if exists notes;
