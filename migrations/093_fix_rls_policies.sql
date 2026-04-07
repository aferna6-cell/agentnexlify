-- 093: Fix RLS policies from migration 091
-- The policies used auth.uid() which is Supabase Auth — this codebase uses
-- JWT-based auth via FastAPI with the service_role key (bypasses RLS).
-- Correct pattern: deny all non-service-role access via RLS, let FastAPI
-- handle tenant isolation in application code.
--
-- Previous policies using auth.uid() would silently return 0 rows if anyone
-- ever queried these tables through PostgREST with an anon/authenticated key.

-- ── Fix ab_tests RLS ──
DROP POLICY IF EXISTS ab_tests_tenant_isolation ON ab_tests;
CREATE POLICY ab_tests_tenant_isolation ON ab_tests
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS ab_test_variants_isolation ON ab_test_variants;
CREATE POLICY ab_test_variants_isolation ON ab_test_variants
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS ab_test_sends_tenant_isolation ON ab_test_sends;
CREATE POLICY ab_test_sends_tenant_isolation ON ab_test_sends
    FOR ALL USING (auth.role() = 'service_role');

-- ── Fix automation_rules RLS ──
DROP POLICY IF EXISTS automation_rules_tenant_isolation ON automation_rules;
CREATE POLICY automation_rules_tenant_isolation ON automation_rules
    FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS automation_rule_executions_tenant_isolation ON automation_rule_executions;
CREATE POLICY automation_rule_executions_tenant_isolation ON automation_rule_executions
    FOR ALL USING (auth.role() = 'service_role');

-- ── Fix campaign_analytics_aggregates RLS ──
DROP POLICY IF EXISTS campaign_analytics_agg_tenant_isolation ON campaign_analytics_aggregates;
CREATE POLICY campaign_analytics_agg_tenant_isolation ON campaign_analytics_aggregates
    FOR ALL USING (auth.role() = 'service_role');
