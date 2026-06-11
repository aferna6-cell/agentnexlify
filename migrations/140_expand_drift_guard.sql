-- Migration 140: expand the drift guard from 7 hot tables to the FULL
-- public schema (audit 2026-06-10 H3).
--
-- hot_table_columns() now returns every public table's columns; coverage
-- is scoped by ops/schema/expected-columns.json (regenerated post-apply),
-- so the function never needs another migration when tables are added.
-- Still SECURITY DEFINER + service-role-only — schema enumeration stays
-- off-limits to anon/authenticated.

CREATE OR REPLACE FUNCTION public.hot_table_columns()
RETURNS TABLE (table_name text, column_name text)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT c.table_name::text, c.column_name::text
  FROM information_schema.columns c
  JOIN information_schema.tables t
    ON t.table_schema = c.table_schema AND t.table_name = c.table_name
  WHERE c.table_schema = 'public'
    AND t.table_type = 'BASE TABLE'
  ORDER BY c.table_name, c.column_name;
$$;

REVOKE ALL ON FUNCTION public.hot_table_columns() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.hot_table_columns() FROM anon;
REVOKE ALL ON FUNCTION public.hot_table_columns() FROM authenticated;
GRANT EXECUTE ON FUNCTION public.hot_table_columns() TO service_role;
