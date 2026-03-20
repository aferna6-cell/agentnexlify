-- Migration 061: Documents & E-Signatures
-- Contracts, proposals, and agreements with digital signature capture

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    template_html TEXT NOT NULL,
    rendered_html TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'viewed', 'signed', 'expired', 'cancelled')),
    signer_name TEXT,
    signer_email TEXT,
    signer_phone TEXT,
    signed_at TIMESTAMPTZ,
    signature_data TEXT,
    signature_ip TEXT,
    sent_at TIMESTAMPTZ,
    sent_via TEXT,
    viewed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    signing_token UUID DEFAULT gen_random_uuid(),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_tenant ON documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_lead ON documents(lead_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_signing_token ON documents(signing_token);

-- Document templates (reusable)
CREATE TABLE IF NOT EXISTS document_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    template_html TEXT NOT NULL,
    variables TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_doc_templates_tenant ON document_templates(tenant_id);

-- RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_documents" ON documents FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE document_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_doc_templates" ON document_templates FOR ALL USING (true) WITH CHECK (true);
