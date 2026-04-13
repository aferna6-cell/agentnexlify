# Should AgentNexLiFy build SMS deliverability monitoring in-house or outsource to Twilio MessagingService?

**Depth:** quick  |  **Model:** claude-sonnet-4-6  |  **Date:** 2026-04-13

**Infrastructure / Transport:**
- **Twilio** — dominant US SMS transport provider; MessagingService is their number-pooling abstraction layer; Twilio Insights is their native analytics product; 600+ global carrier relationships; $4.6B revenue (2024); pricing ~$0.0079/SMS (US outbound)
- **The Campaign Registry (TCR)** — the US carrier-mandated registry for A2P 10DLC brand/campaign registration; non-registration results in carrier filtering; Twilio is a registered CSP with TCR
- **CTIA (Cellular Telecommunications Industry Association)** — the industry body that mandated A2P 10DLC in 2021; sets SMS compliance rules for US business messaging
- **AT&T / Verizon / T-Mobile** — the three US carriers that handle >95% of US SMS traffic; their filtering algorithms and DLR code conventions define the technical ground truth for deliverability

**Monitoring / Observability Tools (buy-side alternatives):**
- **Twilio Insights** — Twilio's native analytics add-on; provides delivery rate dashboards, error code breakdowns, carrier-level performance; API-accessible
- **Datadog** — general-purpose observability platform; can ingest Twilio webhook data via custom integration; $200–$500+/month depending on data volume
- **Bird (formerly MessageBird)** — alternative SMS transport + analytics platform; has native deliverability monitoring; potential alternative to Twilio for combined transport + monitoring
- **Sinch** — Twilio competitor with built-in analytics; worth evaluating if AgentNexLiFy hasn't committed to Twilio exclusively

**Regulatory / Compliance:**
- **FCC (Federal Communications Commission)** — US regulatory body for TCPA enforcement; $500–$1,500 per-message statutory damages for TCPA violations
- **European Data Protection Board** — GDPR enforcement for SMS data in EU; relevant if AgentNexLiFy serves EU SMBs

**AgentNexLiFy Internal:**
- **Senior Engineer (unnamed)** — the 5–8 week resource that would be consumed by in-house build; opportunity cost = delayed Health Score Dashboard
- **SMB Tenants** — end customers whose agent-driven SMS workflows depend on reliable delivery; their complaints (not internal dashboards) are often the first signal of deliverability problems at AgentNexLiFy's current scale