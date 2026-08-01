-- Productized lead prospecting (Phase 5 of nexlify-capabilities-roadmap):
-- discover (Google Places API) -> enrich (site crawl) -> verify (email) ->
-- score -> promote to leads. See backend/services/prospecting.py.
--
-- client_id (NOT tenant_id): prospects promote directly into the leads
-- table, which is client_id-scoped (CLAUDE.md invariant #1). Keeping the
-- same scope column across prospects -> leads avoids a translation layer
-- in the promote step and matches the dedup key shape leads already use
-- (migration 166_leads_client_email_unique.sql).

CREATE TABLE IF NOT EXISTS prospects (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  client_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  source TEXT NOT NULL DEFAULT 'places_api',
  external_ref TEXT,
  business_name TEXT NOT NULL,
  category TEXT,
  address TEXT,
  city TEXT,
  region TEXT,
  phone TEXT,
  website TEXT,
  email TEXT,
  email_verified BOOLEAN NOT NULL DEFAULT false,
  score NUMERIC NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'new'
    CHECK (status IN ('new', 'enriched', 'qualified', 'promoted', 'rejected')),
  enrichment JSONB NOT NULL DEFAULT '{}',
  promoted_lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Dedup arbiter for discover() upsert. Plain (non-partial) UNIQUE so
  -- PostgREST can infer it as an on_conflict target (partial/expression
  -- indexes cannot be inferred — same constraint PostgREST has on migration
  -- 166's leads_client_email_uniq). NULL external_ref rows (non-Places
  -- sources) stay DISTINCT under Postgres defaults.
  UNIQUE (client_id, source, external_ref)
);

CREATE INDEX IF NOT EXISTS idx_prospects_client_status ON prospects(client_id, status);

-- Prod has NO shared public updated_at trigger function (verified against
-- pg_proc 2026-08-01: the only update_updated_at_column lives in Supabase's
-- internal `storage` schema — do not depend on it). Define our own,
-- idempotently, in public.
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prospects_updated_at ON prospects;
CREATE TRIGGER trg_prospects_updated_at
  BEFORE UPDATE ON prospects
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE prospects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on prospects" ON prospects
  FOR ALL USING (current_setting('role', true) = 'service_role');
