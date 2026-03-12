-- Migration 020: Auto review request configuration
-- Adds review request config to tenants and tracking to appointments

-- Review request settings on tenants (enabled, delay, method, custom message)
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS review_request_config JSONB DEFAULT '{"enabled": false, "delay_hours": 24, "method": "email"}';

-- Track which appointments have had review requests sent
ALTER TABLE appointments
ADD COLUMN IF NOT EXISTS review_request_sent_at TIMESTAMPTZ;
