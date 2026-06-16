-- Migration 153: add stripe_trial_end to store Stripe subscription trial_end timestamp
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS stripe_trial_end timestamptz;
