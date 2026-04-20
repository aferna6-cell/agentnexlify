-- 109_tenant_integrations.sql
-- Drive KB onboarding — 3 tables + RLS
-- Source: specs/drive-kb-onboarding_spec.md (grilled 2026-04-20)
-- Issue: #48

create extension if not exists pgcrypto;

-- =============================================================
-- tenant_integrations
-- =============================================================
create table if not exists tenant_integrations (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references tenants(id) on delete cascade,
  provider text not null check (provider in ('drive','dropbox','onedrive','box')),
  config_jsonb jsonb not null default '{}'::jsonb,
  oauth_token_enc bytea,
  oauth_refresh_token_enc bytea,
  oauth_expires_at timestamptz,
  enabled boolean not null default true,
  last_synced_at timestamptz,
  last_sync_status text check (last_sync_status is null or last_sync_status in ('ok','error','partial')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_id, provider)
);

create index if not exists idx_tenant_integrations_client on tenant_integrations(client_id);
create index if not exists idx_tenant_integrations_enabled on tenant_integrations(enabled) where enabled = true;

alter table tenant_integrations enable row level security;

drop policy if exists service_role_full_access on tenant_integrations;
create policy service_role_full_access
  on tenant_integrations
  for all
  to service_role
  using (true)
  with check (true);

-- =============================================================
-- integration_sync_log
-- =============================================================
create table if not exists integration_sync_log (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references tenants(id) on delete cascade,
  integration_id uuid not null references tenant_integrations(id) on delete cascade,
  provider text not null,
  synced_at timestamptz not null default now(),
  files_added int not null default 0,
  files_updated int not null default 0,
  files_skipped int not null default 0,
  files_pii_flagged int not null default 0,
  sections_reembedded int not null default 0,
  sections_skipped int not null default 0,
  error text
);

create index if not exists idx_integration_sync_log_client_synced on integration_sync_log(client_id, synced_at desc);
create index if not exists idx_integration_sync_log_integration on integration_sync_log(integration_id, synced_at desc);

alter table integration_sync_log enable row level security;

drop policy if exists service_role_full_access on integration_sync_log;
create policy service_role_full_access
  on integration_sync_log
  for all
  to service_role
  using (true)
  with check (true);

-- =============================================================
-- kb_section_hashes
-- =============================================================
create table if not exists kb_section_hashes (
  client_id uuid not null references tenants(id) on delete cascade,
  section_id text not null,
  content_sha256 text not null,
  embedded_at timestamptz not null default now(),
  primary key (client_id, section_id)
);

create index if not exists idx_kb_section_hashes_client on kb_section_hashes(client_id);

alter table kb_section_hashes enable row level security;

drop policy if exists service_role_full_access on kb_section_hashes;
create policy service_role_full_access
  on kb_section_hashes
  for all
  to service_role
  using (true)
  with check (true);

-- =============================================================
-- Rollback (commented)
-- =============================================================
-- drop table if exists kb_section_hashes cascade;
-- drop table if exists integration_sync_log cascade;
-- drop table if exists tenant_integrations cascade;
