-- Add password reset token columns to tenants table
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS reset_token TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_tenants_reset_token ON tenants(reset_token) WHERE reset_token IS NOT NULL;
