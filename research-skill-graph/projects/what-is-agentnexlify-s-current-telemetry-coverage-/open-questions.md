# What is AgentNexLiFy's current telemetry coverage? Are agent task completions, session data, and workflow activations already logged at the tenant level — or does a Health Score Dashboard require backend instrumentation work first?

**Depth:** standard  |  **Model:** claude-sonnet-4-6  |  **Date:** 2026-04-20

- [ ] Does AgentNexLiFy's application database contain tenant-tagged records for agent task completions (e.g., a table with tenant_id, completed_at, status columns)? This single question determines whether a v1 Health Score Dashboard can be built without new instrumentation.
- [ ] Is tenant_id consistently present and populated in the database records for agent executions and workflow runs, or is it absent/nullable for some record types?
- [ ] Does AgentNexLiFy currently have any analytics SDK (PostHog, Segment, Mixpanel, Amplitude) installed and configured? If yes, are group/tenant identifiers being passed in the SDK initialization?
- [ ] Are workflows executed via a job queue system (Sidekiq, BullMQ, Celery, Temporal)? If yes, do those systems retain execution logs with tenant context that could be queried?
- [ ] Does AgentNexLiFy use LangChain, LlamaIndex, or another agent framework that has a compatible observability integration (LangSmith, Langfuse)? If yes, agent task completion telemetry may be available with minimal integration effort.
- [ ] What is the expected refresh frequency requirement for the Health Score Dashboard — daily batch (compatible with database queries), hourly (borderline), or real-time (requires event stream)?
- [ ] How many tenants are currently active? If fewer than ~500, database query-based dashboards are technically feasible without performance concerns; above ~5,000 active tenants, a separate analytics layer becomes necessary.
- [ ] Has any churn prediction or tenant health scoring been attempted previously in an ad-hoc way (e.g., a spreadsheet, a manual SQL query run by a CSM)? If yes, those queries reveal what data already exists.
- [ ] What data residency requirements do current tenants impose? EU GDPR compliance may constrain where tenant behavioral data can be stored and processed.
- [ ] Is there an existing data warehouse or business intelligence tool (Metabase, Redash, Looker, dbt) connected to the production database? If yes, the dashboard build is significantly simplified — the data layer may already exist.