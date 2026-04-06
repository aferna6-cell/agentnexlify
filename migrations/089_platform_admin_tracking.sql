-- 089: Platform Admin Tracking
-- Track free/discounted businesses, admin notes, and platform-wide growth metrics

-- Add admin management columns to tenants
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS admin_discount_pct INTEGER DEFAULT 0;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS admin_notes TEXT DEFAULT '';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS acquired_at TIMESTAMPTZ;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS first_paid_at TIMESTAMPTZ;

-- Index for month-by-month growth queries
-- DATE_TRUNC not IMMUTABLE, index on created_at directly instead
CREATE INDEX IF NOT EXISTS idx_tenants_created_at ON tenants(created_at);
CREATE INDEX IF NOT EXISTS idx_tenants_plan_status ON tenants(plan, plan_status);

-- Track promotional arrangements (free tiers, discounts, partner deals)
CREATE TABLE IF NOT EXISTS admin_promotions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    promotion_type TEXT NOT NULL CHECK (promotion_type IN ('free_tier', 'discount', 'extended_trial', 'partner_deal', 'case_study', 'referral')),
    discount_pct INTEGER DEFAULT 0 CHECK (discount_pct >= 0 AND discount_pct <= 100),
    reason TEXT,
    approved_by TEXT,
    starts_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_promotions_tenant ON admin_promotions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_admin_promotions_type ON admin_promotions(promotion_type);

-- Monthly platform revenue aggregates (pre-computed for fast dashboard queries)
CREATE TABLE IF NOT EXISTS platform_monthly_revenue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    month DATE NOT NULL UNIQUE, -- First day of the month (e.g., 2026-04-01)
    total_revenue_cents INTEGER DEFAULT 0,
    total_subscriptions INTEGER DEFAULT 0,
    new_signups INTEGER DEFAULT 0,
    churned INTEGER DEFAULT 0,
    plan_breakdown JSONB DEFAULT '{}',  -- {"growth": 5, "professional": 3, ...}
    mrr_cents INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_monthly_revenue_month ON platform_monthly_revenue(month);
