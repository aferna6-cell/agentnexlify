-- 112: Add intent_config JSONB to widget_configs for per-tenant agent intent
ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS intent_config JSONB DEFAULT NULL;

COMMENT ON COLUMN widget_configs.intent_config IS
  'Per-tenant AI intent configuration. Declares primary_goal, tone, constraints, '
  'escalation_triggers, and trade_off_hierarchy. Injected as structured context '
  'into widget system prompts before custom_instructions. NULL = platform default behavior.';

-- Log intent_config version on conversation start for audit trail
ALTER TABLE conversations
  ADD COLUMN IF NOT EXISTS intent_config_snapshot JSONB DEFAULT NULL;

COMMENT ON COLUMN conversations.intent_config_snapshot IS
  'Snapshot of widget_configs.intent_config at conversation start. '
  'Audit trail: allows debugging which intent was active for a given conversation.';
