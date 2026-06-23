-- Migration 159: Add referred_by_widget_key to tenants
--
-- Completes the widget-watermark referral loop.  When a visitor signs up
-- via a ?ref=<api_key> link in an embedded widget, this column stores the
-- referrer tenant's widget_configs.api_key so we can count referred signups
-- on the referral stats endpoint.
--
-- Separate from tenants.referred_by (UUID FK from the promo-code system,
-- migration 135) — this column tracks the widget-watermark channel.

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS referred_by_widget_key TEXT;

CREATE INDEX IF NOT EXISTS tenants_referred_by_widget_key_idx
    ON tenants (referred_by_widget_key)
    WHERE referred_by_widget_key IS NOT NULL;
