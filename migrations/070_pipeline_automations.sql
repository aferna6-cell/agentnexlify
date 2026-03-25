-- Migration 070: Pipeline stage automations
-- Auto-trigger actions when leads move between pipeline stages.

CREATE TABLE IF NOT EXISTS pipeline_automations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL DEFAULT '',
    trigger_stage TEXT NOT NULL,
    actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_automations_tenant ON pipeline_automations (tenant_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_automations_trigger ON pipeline_automations (tenant_id, trigger_stage) WHERE is_active = TRUE;

COMMENT ON TABLE pipeline_automations IS 'Auto-trigger actions when a lead moves to a specific pipeline stage';
COMMENT ON COLUMN pipeline_automations.trigger_stage IS 'Stage name that triggers this automation when a lead moves into it';
COMMENT ON COLUMN pipeline_automations.actions IS 'Array of action objects: [{type: "email", subject, body}, {type: "create_task", description}, {type: "notify_team", message}]';
