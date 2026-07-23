-- Migration 187: service_role policy on pending_automations (GH #567)
--
-- Migration 186 created pending_automations with ENABLE ROW LEVEL SECURITY
-- but defined no policy. That state is safe-by-default (RLS with zero
-- policies = deny-all for anon/authenticated via PostgREST; the retry
-- drainer and enqueuers use the service key, which has BYPASSRLS), but it
-- diverges from the repo convention set by migration 173: every service-only
-- table carries an explicit always-true policy scoped TO service_role, as
-- documentation + belt-and-braces against a future role misconfiguration.
--
-- This closes the first half of GH #567. The second half (re-cut the
-- activity_feed_events view from closed PR #517) stays deferred until
-- GH #115 (activity feed reader) starts — a view with no consumer is dead
-- surface.
--
-- Idempotent: DROP IF EXISTS + CREATE.

DROP POLICY IF EXISTS pending_automations_service_role ON public.pending_automations;

CREATE POLICY pending_automations_service_role
    ON public.pending_automations
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Rollback (manual, commented):
-- DROP POLICY IF EXISTS pending_automations_service_role ON public.pending_automations;
