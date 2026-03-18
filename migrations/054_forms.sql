-- Migration 054: Form & Survey Builder
-- Embeddable forms that auto-create leads on submission.

CREATE TABLE IF NOT EXISTS forms (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  fields_json JSONB NOT NULL DEFAULT '[]',
  settings_json JSONB NOT NULL DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  submission_count INTEGER DEFAULT 0,
  public_token TEXT UNIQUE DEFAULT encode(gen_random_bytes(16), 'hex'),
  redirect_url TEXT,
  success_message TEXT DEFAULT 'Thank you for your submission!',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS form_submissions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  form_id UUID NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
  data_json JSONB NOT NULL DEFAULT '{}',
  source_url TEXT,
  ip_address TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_forms_tenant ON forms(tenant_id);
CREATE INDEX IF NOT EXISTS idx_forms_public_token ON forms(public_token);
CREATE INDEX IF NOT EXISTS idx_form_submissions_form ON form_submissions(form_id);
CREATE INDEX IF NOT EXISTS idx_form_submissions_tenant ON form_submissions(tenant_id);

ALTER TABLE forms ENABLE ROW LEVEL SECURITY;
ALTER TABLE form_submissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on forms" ON forms
    FOR ALL USING (current_setting('role', true) = 'service_role');
CREATE POLICY "Service role full access on form_submissions" ON form_submissions
    FOR ALL USING (current_setting('role', true) = 'service_role');
