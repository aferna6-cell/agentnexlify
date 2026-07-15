-- Migration 173: lock down anon/PUBLIC access surfaced by Supabase security advisors (2026-07-15)
--
-- Three findings, all exploitable by anyone holding the project's publishable
-- anon key (nothing in this codebase uses the anon key — frontend/widget/demo
-- all go through FastAPI with the service key, verified by repo-wide grep):
--
--  1. `conversations_anon_access` — ALL-commands policy, role `anon`,
--     USING (true): full cross-tenant read/write on conversations via
--     PostgREST. Dropped outright.
--  2. 18 "service role" always-true policies created without TO service_role
--     — polroles = PUBLIC, so they granted every role (incl. anon) full
--     access to clients, leads, messages, documents, integrations (OAuth
--     tokens!), email_events, reviews, team_members, etc. Recreated
--     TO service_role only (service_role also has BYPASSRLS; the policy is
--     documentation + belt-and-braces).
--  3. 8 SECURITY DEFINER functions (AI-token budget reserve/record/release,
--     automation locks, email quota, purge job, rls_auto_enable) were
--     EXECUTE-granted to anon + authenticated via PostgREST /rpc — an anon
--     caller could burn tenants' AI budgets or release automation locks.
--     EXECUTE revoked from PUBLIC/anon/authenticated, kept for service_role.
--
-- Plus: pin search_path on the 3 functions flagged mutable.
-- Idempotent: safe to re-apply (policy/function loops re-derive state).

-- 1. anon full-access policy on conversations
DROP POLICY IF EXISTS conversations_anon_access ON public.conversations;

-- 2. retarget always-true PUBLIC policies to service_role only
DO $$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT c.relname AS tbl, p.polname AS pol
    FROM pg_policy p
    JOIN pg_class c ON c.oid = p.polrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND p.polroles = '{0}'::oid[]  -- policy applies to PUBLIC (every role)
      AND pg_get_expr(p.polqual, p.polrelid) = 'true'
      AND p.polcmd = '*'
  LOOP
    EXECUTE format('DROP POLICY %I ON public.%I', r.pol, r.tbl);
    EXECUTE format(
      'CREATE POLICY %I ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)',
      r.pol, r.tbl
    );
    RAISE NOTICE 'retargeted policy % on % to service_role', r.pol, r.tbl;
  END LOOP;
END $$;

-- 3. SECURITY DEFINER functions: drop PostgREST-exposed EXECUTE
DO $$
DECLARE
  f record;
BEGIN
  FOR f IN
    SELECT p.oid::regprocedure AS sig
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.prosecdef
      AND p.proname IN (
        'purge_photo_quote_images_30d',
        'record_ai_token_usage',
        'release_ai_token_reservation',
        'release_automation_lock',
        'reserve_ai_token_budget',
        'reserve_email_send_quota',
        'rls_auto_enable',
        'try_acquire_automation_lock'
      )
  LOOP
    EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM PUBLIC', f.sig);
    EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM anon', f.sig);
    EXECUTE format('REVOKE EXECUTE ON FUNCTION %s FROM authenticated', f.sig);
    EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO service_role', f.sig);
    RAISE NOTICE 'locked down EXECUTE on %', f.sig;
  END LOOP;
END $$;

-- 4. pin search_path on advisor-flagged functions (mutable search_path)
DO $$
DECLARE
  f record;
BEGIN
  FOR f IN
    SELECT p.oid::regprocedure AS sig
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname IN (
        'purge_photo_quote_images_30d',
        'match_os_memory',
        'match_kb_articles_fts'
      )
  LOOP
    EXECUTE format('ALTER FUNCTION %s SET search_path = public', f.sig);
    RAISE NOTICE 'pinned search_path on %', f.sig;
  END LOOP;
END $$;
