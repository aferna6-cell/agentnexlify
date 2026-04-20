# What is AgentNexLiFy's current telemetry coverage? Are agent task completions, session data, and workflow activations already logged at the tenant level — or does a Health Score Dashboard require backend instrumentation work first?

**Depth:** standard  |  **Model:** claude-sonnet-4-6  |  **Date:** 2026-04-20

**Internal to AgentNexLiFy:**
- **Engineering Lead / Backend Engineer(s):** The only people who can answer whether tenant-tagged execution records exist in the application database or whether any analytics SDK has been configured. This research cannot resolve the core question — they can, in 1–2 days.
- **Product Manager (or equivalent):** Needs to scope the dashboard build correctly; scoping without a telemetry audit risks a 2–3× cost overrun.
- **Early Tenants (design partners):** Their usage patterns define what the Health Score inputs should prioritize; their feedback on v1 would validate whether the signals chosen actually predict health.

**Infrastructure / Tooling Vendors (relevant if instrumentation work is needed):**
- **PostHog** — open-source product analytics with group analytics (tenant-level), self-hostable, strong fit for SMB agentic SaaS at early stage; pricing is volume-based and affordable at AgentNexLiFy's current scale
- **Segment** — event routing layer; allows sending one event to multiple destinations; higher cost than PostHog but more flexible for future data warehouse integrations
- **Langfuse / LangSmith** — purpose-built LLM/agent observability platforms; if AgentNexLiFy uses LangChain or a compatible framework, these may provide agent task completion telemetry out of the box with minimal integration work
- **Mixpanel / Amplitude** — traditional product analytics; both have group analytics for tenant-level views; Mixpanel is cheaper at early stage

**Relevant Prior Research Projects:**
- [[projects/what-is-the-single-highest-leverage-feature-agentn]] — established Health Score Dashboard as the recommendation; this project fills the implementation gap that project left open
- [[projects/why-do-most-ai-chat-widget-companies-plateau-or-fa]] — identified value visibility as a structural failure mode; telemetry is the technical prerequisite for fixing it