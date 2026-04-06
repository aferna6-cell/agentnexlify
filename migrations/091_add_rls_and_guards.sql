-- 091: Add RLS to tables created in migrations 086-089 + IF NOT EXISTS guards
-- Security fix: all tenant-scoped tables must have RLS enabled

-- ── RLS for ab_tests tables ──
ALTER TABLE ab_tests ENABLE ROW LEVEL SECURITY;
CREATE POLICY ab_tests_tenant_isolation ON ab_tests
    FOR ALL USING (tenant_id = auth.uid());

ALTER TABLE ab_test_variants ENABLE ROW LEVEL SECURITY;
CREATE POLICY ab_test_variants_isolation ON ab_test_variants
    FOR ALL USING (ab_test_id IN (SELECT id FROM ab_tests WHERE tenant_id = auth.uid()));

ALTER TABLE ab_test_sends ENABLE ROW LEVEL SECURITY;
CREATE POLICY ab_test_sends_tenant_isolation ON ab_test_sends
    FOR ALL USING (tenant_id = auth.uid());

-- ── RLS for automation_rules tables ──
ALTER TABLE automation_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY automation_rules_tenant_isolation ON automation_rules
    FOR ALL USING (tenant_id = auth.uid());

ALTER TABLE automation_rule_executions ENABLE ROW LEVEL SECURITY;
CREATE POLICY automation_rule_executions_tenant_isolation ON automation_rule_executions
    FOR ALL USING (tenant_id = auth.uid());

-- ── RLS for campaign analytics aggregates ──
ALTER TABLE campaign_analytics_aggregates ENABLE ROW LEVEL SECURITY;
CREATE POLICY campaign_analytics_agg_tenant_isolation ON campaign_analytics_aggregates
    FOR ALL USING (tenant_id = auth.uid());

-- ── RLS for admin-only tables (deny all via PostgREST, admin uses service_role) ──
ALTER TABLE admin_promotions ENABLE ROW LEVEL SECURITY;
-- No permissive policy = deny all non-service-role access

ALTER TABLE platform_monthly_revenue ENABLE ROW LEVEL SECURITY;
-- No permissive policy = deny all non-service-role access
