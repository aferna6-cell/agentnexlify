-- Migration 080: Fix conversations RLS + add unique constraint
-- Root cause: conversations table had RLS enabled (migration 001) but NO policies,
-- causing silent INSERT failures when using anon key. Also adds unique constraint
-- on (client_id, session_id) to prevent duplicate conversation records.

-- 1. Add permissive policy for service_role (backend uses this)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'conversations' AND policyname = 'conversations_service_role_all'
    ) THEN
        CREATE POLICY conversations_service_role_all ON conversations
            FOR ALL
            TO service_role
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;

-- 2. Add policy for authenticated users (scoped to their tenant)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'conversations' AND policyname = 'conversations_tenant_access'
    ) THEN
        CREATE POLICY conversations_tenant_access ON conversations
            FOR ALL
            TO authenticated
            USING (client_id = auth.uid())
            WITH CHECK (client_id = auth.uid());
    END IF;
END $$;

-- 3. Add policy for anon role (widget uses this via API key, needs insert/select)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'conversations' AND policyname = 'conversations_anon_access'
    ) THEN
        CREATE POLICY conversations_anon_access ON conversations
            FOR ALL
            TO anon
            USING (true)
            WITH CHECK (true);
    END IF;
END $$;

-- 4. Add unique constraint on (client_id, session_id) to prevent duplicate conversations
-- First deduplicate any existing duplicates (keep the oldest)
DELETE FROM conversations a
    USING conversations b
WHERE a.id > b.id
    AND a.client_id = b.client_id
    AND a.session_id = b.session_id;

-- Now add the unique constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'conversations_client_session_unique'
    ) THEN
        ALTER TABLE conversations ADD CONSTRAINT conversations_client_session_unique
            UNIQUE (client_id, session_id);
    END IF;
END $$;
