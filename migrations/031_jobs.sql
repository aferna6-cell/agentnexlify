-- Migration 031: Job board — job postings for businesses
-- SMS-first applications, no resume required

CREATE TABLE IF NOT EXISTS jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    pay_range TEXT,
    schedule TEXT,
    location TEXT,
    skills TEXT[] DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS job_applications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    applicant_name TEXT NOT NULL,
    applicant_phone TEXT NOT NULL,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jobs_tenant_active ON jobs(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_job_applications_job ON job_applications(job_id, status);
CREATE INDEX IF NOT EXISTS idx_job_applications_tenant ON job_applications(tenant_id, created_at DESC);

-- RLS
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants manage their own jobs"
    ON jobs FOR ALL
    USING (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id')
    WITH CHECK (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id');

CREATE POLICY "Service role full access on jobs"
    ON jobs FOR ALL
    USING (current_setting('role', true) = 'service_role');

CREATE POLICY "Tenants manage their own job applications"
    ON job_applications FOR ALL
    USING (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id')
    WITH CHECK (tenant_id::text = current_setting('request.jwt.claims', true)::json->>'tenant_id');

CREATE POLICY "Service role full access on job_applications"
    ON job_applications FOR ALL
    USING (current_setting('role', true) = 'service_role');
