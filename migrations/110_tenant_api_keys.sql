-- 110_tenant_api_keys.sql
-- Zapier CRM export — API key table + RLS
-- Source: specs/zapier-crm-export_spec.md (grilled 2026-04-20)
-- Issue: #57

create table if not exists tenant_api_keys (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references tenants(id) on delete cascade,
  key_hash text not null,
  key_prefix text not null,
  name text not null,
  last_used_at timestamptz,
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  created_by_user_id uuid
);

-- Prefix lookup index critical — auth middleware does prefix match before bcrypt verify
create index if not exists idx_tenant_api_keys_prefix on tenant_api_keys(key_prefix) where revoked_at is null;
create index if not exists idx_tenant_api_keys_client on tenant_api_keys(client_id);

alter table tenant_api_keys enable row level security;

drop policy if exists service_role_full_access on tenant_api_keys;
create policy service_role_full_access
  on tenant_api_keys
  for all
  to service_role
  using (true)
  with check (true);

-- =============================================================
-- Rollback (commented)
-- =============================================================
-- drop table if exists tenant_api_keys cascade;
