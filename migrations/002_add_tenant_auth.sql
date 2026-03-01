-- AgentNexLiFy Auth Migration
-- Migration: 002_add_tenant_auth.sql
-- Run manually in Supabase SQL Editor before deploying backend.

-- ============================================================
-- 1. Add auth columns to tenants
-- ============================================================
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS password_hash TEXT;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS owner_name TEXT;

-- ============================================================
-- 2. Expand business_type CHECK constraint
-- ============================================================
ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_business_type_check;
ALTER TABLE tenants ADD CONSTRAINT tenants_business_type_check
    CHECK (business_type IN (
        'plumbing','dental','realestate','legal','fitness','restaurant',
        'salon','auto_shop','medical','other'
    ));

-- ============================================================
-- 3. Change api_key from UUID to TEXT (for "anx_" prefix keys)
-- ============================================================
ALTER TABLE widget_configs ALTER COLUMN api_key TYPE TEXT USING api_key::TEXT;
ALTER TABLE widget_configs ALTER COLUMN api_key DROP DEFAULT;
