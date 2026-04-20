# What is AgentNexLiFy's current telemetry coverage? Are agent task completions, session data, and workflow activations already logged at the tenant level — or does a Health Score Dashboard require backend instrumentation work first?

**Depth:** standard  |  **Model:** claude-sonnet-4-6  |  **Date:** 2026-04-20

## What Did We Learn?

The prior research log establishes that AgentNexLiFy is an early-stage agentic SaaS platform targeting SMB tenants, with known churn problems driven by low value visibility — and a previously recommended Health Score Dashboard as the highest-leverage churn intervention. This research attempts to answer whether that dashboard can be built from existing telemetry or requires new backend instrumentation.

**The honest answer: almost certainly requires backend instrumentation work first — but the extent depends on one architectural question that cannot be answered from available evidence.**

Here is what the multi-lens analysis converges on:

**What is likely already logged (high confidence):** Session-level events (login timestamps, session duration, page views) are the default output of any web application framework and are almost certainly captured in some form — whether in application logs, a database, or a basic analytics SDK. These exist by default unless actively suppressed.

**What is likely NOT automatically logged at the tenant level (high confidence):** Agent task completions and workflow activations are application-semantic events — they require explicit instrumentation calls inserted at the point in the codebase where a task finishes or a workflow fires. No framework logs these automatically. If no developer has written `track("agent_task_completed", {tenant_id, agent_id, outcome})` calls into the execution layer, this data does not exist in queryable form.

**What is structurally unknown:** Whether AgentNexLiFy has any existing event tracking infrastructure (Segment, Mixpanel, PostHog, custom event bus, database audit log) and whether the above events were instrumented when the features were built.

**The risk:** Early-stage teams building agentic products typically instrument UI interactions but neglect backend execution events. The agent task completion event — the most valuable metric for a Health Score — lives deep in backend execution logic, not at the UI layer. There is a high prior probability (estimated 60–75%) that this event is either unlogged or logged only in raw application/error logs without tenant-level tagging that would make it queryable for a dashboard.

**What this means for the Health Score Dashboard decision:** Do not assume the telemetry exists. The correct first step is a telemetry audit — a one-to-two day engineering spike to enumerate what events are currently being captured, with what fields, and in what storage systems. The dashboard build estimate changes dramatically depending on the audit result: if telemetry exists, the dashboard is a frontend + query layer project (2–4 weeks). If instrumentation is absent, it is a backend instrumentation + data pipeline + frontend project (6–12 weeks minimum).

**What remains unknown:** The actual state of AgentNexLiFy's event tracking infrastructure, the schema of any existing logs, whether tenant_id is consistently threaded through backend execution contexts, and whether a data warehouse or queryable analytics store exists.