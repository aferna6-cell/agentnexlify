-- Migration 190: escalations — first-class handoff/escalation records for
-- widget/email/sms/OS threads.
--
-- Phase 1a of plans/nexlify-capabilities-roadmap_plan.md: replaces the
-- "handoff" magic-string-only flow (a conversations.tags entry with no
-- queryable row behind it) with a real table backend/services/escalations.py
-- can create, list, assign, and resolve. client_id scope — matches
-- leads/conversations (see .claude/rules/schema-discipline.md), not
-- tenant_id, because an escalation is anchored to a customer-facing
-- conversation the same way a lead is.
--
-- Idempotency: UNIQUE (client_id, source, source_ref) lets create_escalation
-- call itself safely on retry (widget re-detecting HANDOFF_REQUESTED on the
-- same conversation, a webhook redelivery, etc.) without duplicating rows —
-- same pattern as os_messages.source_ref (migration 124) and
-- pending_automations.
--
-- RLS: enabled with an explicit always-true service_role policy, per the
-- convention set by migration 173 and reinforced in 187/189 — the backend
-- always writes through the service-role key (which also has BYPASSRLS),
-- this policy is documentation + belt-and-braces against a future role
-- misconfiguration.
--
-- Additive + idempotent.

CREATE TABLE IF NOT EXISTS escalations (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id          uuid NOT NULL,
    source             text NOT NULL CHECK (source IN ('widget', 'email', 'sms', 'os')),
    source_ref         text NOT NULL,
    conversation_id    uuid REFERENCES conversations(id) ON DELETE SET NULL,
    os_thread_id       uuid REFERENCES os_threads(id) ON DELETE SET NULL,
    reason             text NOT NULL DEFAULT '',
    priority           text NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status             text NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'in_progress', 'resolved', 'dismissed')),
    assigned_to        text,
    metadata           jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at         timestamptz NOT NULL DEFAULT now(),
    first_response_at  timestamptz,
    resolved_at        timestamptz,
    UNIQUE (client_id, source, source_ref)
);

CREATE INDEX IF NOT EXISTS escalations_client_status_idx
    ON escalations (client_id, status);

-- resolve_escalation's "any other open escalation on this conversation?"
-- lookup — the return-to-bot check that clears the handoff tag.
CREATE INDEX IF NOT EXISTS escalations_conversation_idx
    ON escalations (conversation_id)
    WHERE conversation_id IS NOT NULL;

ALTER TABLE escalations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS escalations_service_role ON public.escalations;

CREATE POLICY escalations_service_role
    ON public.escalations
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Rollback (manual, commented):
-- DROP POLICY IF EXISTS escalations_service_role ON public.escalations;
-- DROP TABLE IF EXISTS escalations;
