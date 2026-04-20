-- 108_photo_quote_tables.sql
-- Photo-quote widget — 3 tables + retention function
-- Source: specs/photo-quote_spec.md (grilled 2026-04-20)
-- Issue: #36

create extension if not exists pgcrypto;

-- =============================================================
-- tenant_pricing_rules
-- =============================================================
create table if not exists tenant_pricing_rules (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references tenants(id) on delete cascade,
  industry text not null check (industry in ('plumbing','roofing','hvac','auto_body','landscaping','pest')),
  rules_jsonb jsonb not null default '{}'::jsonb,
  disclaimer_text text,
  min_confidence_threshold numeric check (min_confidence_threshold is null or (min_confidence_threshold >= 0 and min_confidence_threshold <= 1)),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_id, industry)
);

create index if not exists idx_tenant_pricing_rules_client on tenant_pricing_rules(client_id);

alter table tenant_pricing_rules enable row level security;

drop policy if exists service_role_full_access on tenant_pricing_rules;
create policy service_role_full_access
  on tenant_pricing_rules
  for all
  to service_role
  using (true)
  with check (true);

-- =============================================================
-- quote_requests
-- =============================================================
create table if not exists quote_requests (
  id uuid primary key default gen_random_uuid(),
  client_id uuid not null references tenants(id) on delete cascade,
  conversation_id uuid references conversations(id) on delete set null,
  image_url text,
  thumbnail_url text not null,
  full_image_purged_at timestamptz,
  quote_low int,
  quote_high int,
  severity text check (severity in ('minor','major','needs_human')),
  confidence numeric check (confidence is null or (confidence >= 0 and confidence <= 1)),
  claude_summary text,
  needs_human boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists idx_quote_requests_client_created on quote_requests(client_id, created_at desc);
create index if not exists idx_quote_requests_conversation on quote_requests(conversation_id);
create index if not exists idx_quote_requests_purge_candidates on quote_requests(created_at) where full_image_purged_at is null and image_url is not null;

alter table quote_requests enable row level security;

drop policy if exists service_role_full_access on quote_requests;
create policy service_role_full_access
  on quote_requests
  for all
  to service_role
  using (true)
  with check (true);

-- =============================================================
-- tenant_quote_usage
-- =============================================================
create table if not exists tenant_quote_usage (
  client_id uuid not null references tenants(id) on delete cascade,
  period_start date not null,
  quote_count int not null default 0,
  overage_count int not null default 0,
  updated_at timestamptz not null default now(),
  primary key (client_id, period_start)
);

alter table tenant_quote_usage enable row level security;

drop policy if exists service_role_full_access on tenant_quote_usage;
create policy service_role_full_access
  on tenant_quote_usage
  for all
  to service_role
  using (true)
  with check (true);

-- =============================================================
-- Retention function — purge full images >30d
-- Called daily by backend scheduler (issue #40)
-- =============================================================
create or replace function purge_photo_quote_images_30d()
returns int
language plpgsql
security definer
as $$
declare
  purged int := 0;
begin
  update quote_requests
  set image_url = null,
      full_image_purged_at = now()
  where created_at < now() - interval '30 days'
    and full_image_purged_at is null
    and image_url is not null;
  get diagnostics purged = row_count;
  return purged;
end;
$$;

-- =============================================================
-- Rollback (manual, commented — run to undo)
-- =============================================================
-- drop function if exists purge_photo_quote_images_30d();
-- drop table if exists tenant_quote_usage cascade;
-- drop table if exists quote_requests cascade;
-- drop table if exists tenant_pricing_rules cascade;
