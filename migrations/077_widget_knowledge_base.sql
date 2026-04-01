-- 077_widget_knowledge_base.sql
-- Add AI-generated knowledge base storage to widget_configs.
-- Produced during the onboarding wizard (step 3); injected into the chat system prompt.

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS knowledge_base TEXT;

COMMENT ON COLUMN widget_configs.knowledge_base IS
  'AI-generated markdown knowledge base produced during onboarding wizard. '
  'Injected into the chat system prompt when present. Editable post-onboarding.';
