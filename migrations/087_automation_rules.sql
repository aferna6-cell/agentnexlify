-- 087: Automation Rules Tables
-- Event-driven automation rules with trigger conditions and action execution

CREATE TABLE automation_rules (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN (
        'lead_captured', 'tag_added', 'tag_removed',
        'form_submitted', 'appointment_created', 'appointment_completed',
        'pipeline_stage_changed', 'lead_score_threshold',
        'email_opened', 'email_clicked',
        'scheduled_daily', 'scheduled_weekly',
        'website_visit', 'smart_list_matched'
    )),
    trigger_config JSONB DEFAULT '{}',
    conditions JSONB DEFAULT '[]',
    actions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    triggered_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE automation_rule_executions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    automation_rule_id UUID REFERENCES automation_rules(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    trigger_event JSONB NOT NULL,
    actions_run JSONB DEFAULT '[]',
    status TEXT DEFAULT 'success' CHECK (status IN ('success', 'partial', 'failed')),
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_automation_rules_tenant ON automation_rules(tenant_id);
CREATE INDEX idx_automation_rules_trigger ON automation_rules(tenant_id, trigger_type);
CREATE INDEX idx_automation_rules_active ON automation_rules(tenant_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_automation_rule_executions_rule ON automation_rule_executions(automation_rule_id);
CREATE INDEX idx_automation_rule_executions_tenant ON automation_rule_executions(tenant_id);
