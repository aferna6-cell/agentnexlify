-- Proactive behavior-triggered widget open (time-on-page / exit-intent).
-- JSONB config passed through to the embedded widget by GET /api/v1/widget/config.
-- Shape: {"enabled":bool,"delay_seconds":int,"exit_intent":bool,"message":text|null,"once_per_session":bool}
-- NULL (default) => widget does nothing (fully backward compatible, feature off).
ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS proactive jsonb;
