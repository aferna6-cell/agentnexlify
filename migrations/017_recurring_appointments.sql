-- Migration 017: Add recurrence support to appointments
-- Allows businesses to set up weekly/biweekly/monthly recurring appointments

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS recurrence_rule TEXT DEFAULT NULL;
-- Values: NULL (one-time), 'weekly', 'biweekly', 'monthly'

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS recurrence_parent_id UUID DEFAULT NULL
    REFERENCES appointments(id) ON DELETE CASCADE;
-- Links generated instances back to the parent appointment

ALTER TABLE appointments ADD COLUMN IF NOT EXISTS recurrence_end_date DATE DEFAULT NULL;
-- When the recurring series ends (only set on parent appointment)

-- Index for querying all instances of a recurring series
CREATE INDEX IF NOT EXISTS idx_appointments_recurrence_parent
    ON appointments (recurrence_parent_id) WHERE recurrence_parent_id IS NOT NULL;
