-- Migration 078: Expand business_type CHECK constraint to include all signup industries
-- Adds: accounting, bakery, bar_nightclub, cafe, catering, chiropractic, cleaning,
--       electrical, food_truck, hvac, landscaping, moving, pest_control, photography,
--       roofing, tutoring, veterinary
-- (and retains all 10 existing values)

ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_business_type_check;
ALTER TABLE tenants ADD CONSTRAINT tenants_business_type_check
    CHECK (business_type IN (
        'accounting',
        'auto_shop',
        'bakery',
        'bar_nightclub',
        'cafe',
        'catering',
        'chiropractic',
        'cleaning',
        'dental',
        'electrical',
        'fitness',
        'food_truck',
        'hvac',
        'landscaping',
        'legal',
        'medical',
        'moving',
        'other',
        'pest_control',
        'photography',
        'plumbing',
        'realestate',
        'restaurant',
        'roofing',
        'salon',
        'tutoring',
        'veterinary'
    ));
