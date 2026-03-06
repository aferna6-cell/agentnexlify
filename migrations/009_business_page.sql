-- Business Page feature: hosted pages at /biz/{slug}
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_slug TEXT UNIQUE;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_description TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_phone TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_address TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_city TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_state TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_hours_display TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_logo_url TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_cover_url TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_page_enabled BOOLEAN DEFAULT false;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_services TEXT[];

CREATE INDEX IF NOT EXISTS idx_tenants_business_slug ON tenants (business_slug)
  WHERE business_slug IS NOT NULL;
