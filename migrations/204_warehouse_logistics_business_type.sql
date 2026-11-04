-- Migration 204: allow warehouse_logistics on tenants.business_type.
--
-- Read-only review of migrations (not applied here):
--   001 creates tenants.business_type as TEXT with a CHECK allowlist.
--   002, 078, and 142 replace tenants_business_type_check with a larger
--   allowlist. 142 is the latest definition. No CREATE TYPE / enum exists
--   for business_type. seo_audit_tables.business_type is unconstrained TEXT.
-- 142 does not include warehouse_logistics, so saving that value fails
-- until this constraint is replaced.
--
-- NOT applied to production or Supabase by the change that added this file.

ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_business_type_check;
ALTER TABLE tenants ADD CONSTRAINT tenants_business_type_check CHECK (
  business_type = ANY (ARRAY[
    'accounting'::text, 'auto_shop'::text, 'bakery'::text,
    'bar_nightclub'::text, 'cafe'::text, 'catering'::text,
    'chiropractic'::text, 'cleaning'::text, 'dental'::text,
    'electrical'::text, 'financial_services'::text, 'fitness'::text,
    'food_truck'::text, 'hvac'::text, 'landscaping'::text, 'legal'::text,
    'medical'::text, 'moving'::text, 'other'::text, 'pest_control'::text,
    'photography'::text, 'plumbing'::text, 'realestate'::text,
    'restaurant'::text, 'roofing'::text, 'salon'::text, 'tutoring'::text,
    'veterinary'::text, 'warehouse_logistics'::text
  ])
);
