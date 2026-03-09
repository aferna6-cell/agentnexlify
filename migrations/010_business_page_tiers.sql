-- Business Page tier features: appearance, branding, SEO, custom CSS
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS bp_color_theme TEXT DEFAULT 'default';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS bp_font_family TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS bp_hide_powered_by BOOLEAN DEFAULT false;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS bp_custom_css TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS bp_meta_title TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS bp_meta_description TEXT;
