-- Migration 138: Agent OS file uploads metadata table

CREATE TABLE IF NOT EXISTS os_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    thread_id UUID REFERENCES os_threads(id) ON DELETE SET NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    public_url TEXT NOT NULL,
    vision_summary TEXT,
    kind TEXT NOT NULL DEFAULT 'upload' CHECK (kind IN ('upload', 'generated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_os_uploads_client_id ON os_uploads(client_id);
CREATE INDEX IF NOT EXISTS idx_os_uploads_thread_id ON os_uploads(thread_id);
CREATE INDEX IF NOT EXISTS idx_os_uploads_kind ON os_uploads(client_id, kind);

-- RLS: deny public access; service_role handles all writes
ALTER TABLE os_uploads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full_access" ON os_uploads
    FOR ALL USING (true) WITH CHECK (true);
