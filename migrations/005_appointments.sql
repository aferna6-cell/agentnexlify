-- Appointment booking system: business_hours + appointments tables
-- Run in Supabase SQL editor

-- Required for EXCLUDE USING gist (double-booking prevention)
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- business_hours: per-tenant availability configuration
CREATE TABLE business_hours (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    timezone             TEXT NOT NULL DEFAULT 'America/New_York',
    hours                JSONB NOT NULL DEFAULT '{
        "monday":    {"enabled": true, "start": "09:00", "end": "17:00"},
        "tuesday":   {"enabled": true, "start": "09:00", "end": "17:00"},
        "wednesday": {"enabled": true, "start": "09:00", "end": "17:00"},
        "thursday":  {"enabled": true, "start": "09:00", "end": "17:00"},
        "friday":    {"enabled": true, "start": "09:00", "end": "17:00"},
        "saturday":  {"enabled": false, "start": "09:00", "end": "17:00"},
        "sunday":    {"enabled": false, "start": "09:00", "end": "17:00"}
    }'::jsonb,
    slot_duration_minutes INTEGER NOT NULL DEFAULT 30,
    buffer_minutes        INTEGER NOT NULL DEFAULT 0,
    max_advance_days      INTEGER NOT NULL DEFAULT 30,
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_business_hours_tenant UNIQUE (tenant_id)
);

-- appointments: booked appointment slots
CREATE TABLE appointments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id         UUID REFERENCES leads(id) ON DELETE SET NULL,
    customer_name   TEXT NOT NULL,
    customer_email  TEXT NOT NULL,
    customer_phone  TEXT,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    status          TEXT NOT NULL DEFAULT 'confirmed'
                    CHECK (status IN ('confirmed', 'cancelled', 'completed', 'no_show')),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    -- Prevent double-booking: no two confirmed appointments can overlap for the same tenant
    EXCLUDE USING gist (
        tenant_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status = 'confirmed')
);

-- Indexes
CREATE INDEX idx_business_hours_tenant ON business_hours(tenant_id);
CREATE INDEX idx_appointments_tenant_start ON appointments(tenant_id, start_time);
CREATE INDEX idx_appointments_tenant_status ON appointments(tenant_id, status);

-- Add booking_enabled to widget_configs
ALTER TABLE widget_configs ADD COLUMN IF NOT EXISTS booking_enabled BOOLEAN DEFAULT false;

-- RLS
ALTER TABLE business_hours ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on business_hours"
    ON business_hours FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on appointments"
    ON appointments FOR ALL
    USING (auth.role() = 'service_role');
