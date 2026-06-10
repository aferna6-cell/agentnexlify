-- Migration 136: hot_table_columns() — live schema introspection for the
-- drift guard (scripts/check_schema_drift.py). PostgREST does not expose
-- information_schema, so CI needs an RPC to read live columns.
--
-- Why: 2026-06-10 incident — migrations/001 listed referral columns the live
-- schema never had; code trusted the file and /register 500'd in prod.
-- See docs/dev-knowledge/bug-patterns.md "Migration files ≠ live schema".

CREATE OR REPLACE FUNCTION public.hot_table_columns()
RETURNS TABLE (table_name text, column_name text)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT c.table_name::text, c.column_name::text
  FROM information_schema.columns c
  WHERE c.table_schema = 'public'
    AND c.table_name IN (
      'tenants', 'leads', 'conversations', 'invoices',
      'appointments', 'chat_messages', 'widget_configs'
    )
  ORDER BY c.table_name, c.column_name;
$$;

-- service-role only — no reason for anon/authenticated to enumerate schema
REVOKE ALL ON FUNCTION public.hot_table_columns() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.hot_table_columns() FROM anon;
REVOKE ALL ON FUNCTION public.hot_table_columns() FROM authenticated;
GRANT EXECUTE ON FUNCTION public.hot_table_columns() TO service_role;
