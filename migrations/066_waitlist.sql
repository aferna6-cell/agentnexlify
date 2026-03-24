-- 066: Appointment Waitlist
-- Allows customers to join a waitlist when no slots are available.
-- When a cancellation opens a slot, the business can notify waitlisted customers.

CREATE TABLE IF NOT EXISTS waitlist_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    customer_name TEXT NOT NULL,
    customer_email TEXT,
    customer_phone TEXT,
    preferred_date DATE NOT NULL,
    preferred_time_start TEXT,  -- e.g. "09:00"
    preferred_time_end TEXT,    -- e.g. "12:00"
    service_type_id UUID REFERENCES service_types(id) ON DELETE SET NULL,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'notified', 'booked', 'expired', 'cancelled')),
    notified_at TIMESTAMPTZ,
    booked_appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_waitlist_tenant_status ON waitlist_entries(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_waitlist_tenant_date ON waitlist_entries(tenant_id, preferred_date) WHERE status = 'waiting';

ALTER TABLE waitlist_entries ENABLE ROW LEVEL SECURITY;
