-- Migration 055: Add sending_started_at to marketing_campaigns
-- Required by Fix 1A: campaign send background task. The column records when
-- the send loop was dispatched so the dashboard can detect stalled campaigns.

ALTER TABLE marketing_campaigns
  ADD COLUMN IF NOT EXISTS sending_started_at TIMESTAMPTZ;
