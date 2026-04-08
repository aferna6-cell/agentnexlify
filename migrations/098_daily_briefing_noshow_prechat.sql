-- Migration 098: Add daily briefing, no-show recovery toggles, and pre-chat form config
-- daily_briefing_enabled + noshow_recovery_enabled on tenants
-- pre_chat_form on widget_configs

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS daily_briefing_enabled boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS noshow_recovery_enabled boolean DEFAULT true;

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS pre_chat_form jsonb DEFAULT null;

COMMENT ON COLUMN tenants.daily_briefing_enabled IS 'Morning SMS briefing with leads, appointments, tasks';
COMMENT ON COLUMN tenants.noshow_recovery_enabled IS 'Auto SMS+email to no-show appointments';
COMMENT ON COLUMN widget_configs.pre_chat_form IS 'JSON config for pre-chat form fields [{name, label, type, required}]';
