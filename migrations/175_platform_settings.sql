-- Migration 175: platform_settings — DB-backed operational flags
--
-- Several launch-blocking flags live only in Railway env vars
-- (REFERRAL_REWARD_ENABLED — GH #413, day 27) or backend/config.py env
-- settings (widget_kb_rerank_enabled / widget_kb_hybrid_enabled from PR
-- #471), so flipping them requires Railway dashboard access no automation
-- has. This table gives every such flag a DB override with env fallback:
-- backend/services/platform_flags.py reads it (60s cache, fail-open to
-- env), so a flag flip is one service-role UPDATE instead of an operator
-- deploy.
--
-- Service-role only: no anon/authenticated grants, RLS on with no
-- policies (deny-by-default), matching the 173 lockdown posture.

CREATE TABLE IF NOT EXISTS platform_settings (
    key text PRIMARY KEY,
    value text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE platform_settings ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON platform_settings FROM anon, authenticated, PUBLIC;

COMMENT ON TABLE platform_settings IS
    'Operational flag overrides (env fallback in platform_flags.py). Service-role only.';
