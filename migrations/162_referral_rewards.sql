-- Migration 160: referral_rewards table
--
-- Records the monetary reward granted to a referrer when a tenant they
-- referred pays their FIRST invoice. Reward is a flat $20 (2000 cents)
-- Stripe customer-balance credit applied to the referrer's Stripe customer.
--
-- Attribution is resolved from one of the two existing referral channels on
-- the tenants table:
--   tenants.referred_by             UUID → promo-code path (migration 135)
--   tenants.referred_by_widget_key  TEXT → widget-watermark path (migration 159)
--
-- Idempotency: the UNIQUE index on referred_tenant_id guarantees at most ONE
-- reward per referred tenant, ever. This is what enforces "first paid invoice
-- only" and makes the grant safe against Stripe webhook redeliveries and the
-- two parallel webhook endpoints (billing.py + stripe_webhooks.py).

CREATE TABLE IF NOT EXISTS referral_rewards (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_tenant_id   uuid NOT NULL,
    referred_tenant_id   uuid NOT NULL,
    amount_cents         integer NOT NULL,
    currency             text NOT NULL DEFAULT 'usd',
    attribution_channel  text NOT NULL,           -- 'promo_code' | 'widget_watermark'
    stripe_customer_id   text,
    stripe_balance_txn_id text,
    status               text NOT NULL DEFAULT 'pending',  -- pending | granted | failed
    error                text,
    created_at           timestamptz NOT NULL DEFAULT now(),
    granted_at           timestamptz
);

-- One reward per referred tenant, ever. Claim-row-first + this constraint =
-- idempotent grant across concurrent/duplicate webhook deliveries.
CREATE UNIQUE INDEX IF NOT EXISTS referral_rewards_referred_tenant_id_uniq
    ON referral_rewards (referred_tenant_id);

-- Fast lookup of a referrer's earned rewards (referral my-stats earnings panel).
CREATE INDEX IF NOT EXISTS referral_rewards_referrer_tenant_id_idx
    ON referral_rewards (referrer_tenant_id);
