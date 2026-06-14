-- Migration 142: add 'financial_services' to the tenants.business_type
-- CHECK constraint (gap G8 — MTOptions vertical depth).
--
-- MTOptions (live beta, options-trading alert subscription) was stuck on
-- 'other' because the 27-value allowlist had no financial vertical. The
-- new value powers the financial_services guidance pack in
-- backend/services/os_kb_feed.py and the tailored Agent OS starters.

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
    'veterinary'::text
  ])
);

-- Move the live beta tenant onto the new vertical
UPDATE tenants SET business_type = 'financial_services'
WHERE business_name = 'MTOptions' AND business_type = 'other';
