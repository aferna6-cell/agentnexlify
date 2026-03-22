-- Migration 065: Client accounts for white-label client login
-- Allows business owners to give their clients a login to see appointments/invoices/documents.
-- Clients register via portal token, then log in with email + password.

CREATE TABLE client_accounts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, email),
    UNIQUE(tenant_id, lead_id)
);

CREATE INDEX idx_client_accounts_tenant ON client_accounts(tenant_id);
CREATE INDEX idx_client_accounts_email ON client_accounts(email);

ALTER TABLE client_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON client_accounts
    FOR ALL USING (auth.role() = 'service_role');

-- Tenant toggle for client login
ALTER TABLE tenants ADD COLUMN client_login_enabled BOOLEAN DEFAULT false;
