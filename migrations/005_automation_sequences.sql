-- 005_automation_sequences.sql
-- Multi-step email automation sequences

-- automation_sequences: defines a sequence (e.g., "Welcome Email Series")
CREATE TABLE automation_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    trigger_event TEXT NOT NULL,  -- 'new_lead', 'lead_stage_change', 'no_response_24h'
    trigger_config JSONB DEFAULT '{}'::jsonb,  -- e.g., {"target_stage": "appointment"}
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- automation_steps: individual steps within a sequence
CREATE TABLE automation_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID NOT NULL REFERENCES automation_sequences(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    delay_minutes INTEGER NOT NULL DEFAULT 0,
    action_type TEXT NOT NULL DEFAULT 'email',
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(sequence_id, step_order)
);

-- automation_executions: tracks a lead's progress through a sequence
CREATE TABLE automation_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID NOT NULL REFERENCES automation_sequences(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    current_step INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'in_progress',  -- in_progress, completed, paused, failed
    next_run_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE(sequence_id, lead_id)  -- prevent duplicate enrollments
);

-- automation_logs: audit trail
CREATE TABLE automation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES automation_executions(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES automation_steps(id) ON DELETE CASCADE,
    action TEXT NOT NULL,  -- 'email_sent', 'email_failed', 'skipped'
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_auto_seq_tenant ON automation_sequences(tenant_id);
CREATE INDEX idx_auto_steps_seq ON automation_steps(sequence_id);
CREATE INDEX idx_auto_exec_next ON automation_executions(next_run_at) WHERE status = 'in_progress';
CREATE INDEX idx_auto_exec_tenant ON automation_executions(tenant_id);
CREATE INDEX idx_auto_logs_exec ON automation_logs(execution_id);

-- RLS
ALTER TABLE automation_sequences ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_logs ENABLE ROW LEVEL SECURITY;
