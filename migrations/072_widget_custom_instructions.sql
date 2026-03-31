-- Add custom_instructions to widget_configs
-- Allows per-tenant system prompt overrides (identity, business-specific rules, disclaimers)
ALTER TABLE widget_configs ADD COLUMN IF NOT EXISTS custom_instructions TEXT;
COMMENT ON COLUMN widget_configs.custom_instructions IS 'Tenant-specific AI system prompt instructions. Replaces the generic identity line and adds business-specific rules/context. Injected at the top of the system prompt before standard platform rules.';
