-- Migration 166: review_responses table
--
-- Reviews AI — approval-gated AI review responses (GoHighLevel AI Employee
-- parity). Drafts an AI reply to a customer review and holds it for human
-- approval before it is ever posted anywhere. Mirrors the os_agent_runs
-- approval-gated pattern in backend/services/os_sms_approval.py: the AI
-- never auto-posts, only proposes (see .claude/rules/propose-only-records.md).
--
-- Separate from the existing `reviews` table (migration 009-era Reputation
-- Manager) and its POST /api/v1/reviews/{tenant_id}/{review_id}/ai-draft
-- endpoint, which writes ai_draft_response directly onto the review row with
-- no status/approval lifecycle. This table adds the explicit
-- draft -> approved -> posted/rejected state machine plus who approved it
-- and when, independent of whether the source review already lives in our
-- `reviews` table or arrives from an external platform.
--
-- review_id references reviews.id when the review already exists in our
-- `reviews` table; external_ref holds a platform review id when it does not
-- (e.g. pulled from a future Google Business Profile API integration before
-- it is backfilled into `reviews`). No hard FK is added — matches the
-- no-FK-to-tenants convention used elsewhere in this migration set
-- (see migrations/162_referral_rewards.sql) and keeps this table decoupled
-- from `reviews` schema churn.

CREATE TABLE IF NOT EXISTS review_responses (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL,
    review_id     uuid,             -- FK-less pointer to reviews.id, when known
    external_ref  text,             -- platform review id, when review_id is unknown
    review_text   text NOT NULL,
    review_rating integer NOT NULL CHECK (review_rating BETWEEN 1 AND 5),
    draft_reply   text NOT NULL,
    status        text NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'approved', 'posted', 'rejected')),
    approved_by   text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    approved_at   timestamptz
);

-- Pending-approval inbox query: "give me tenant X's drafts awaiting review".
CREATE INDEX IF NOT EXISTS review_responses_tenant_status_idx
    ON review_responses (tenant_id, status);
