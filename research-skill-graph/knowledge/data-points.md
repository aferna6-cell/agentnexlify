# Data Points

Hard numbers collected across research projects. Every entry must carry its source. Base rates live here.

## Format

```
- metric | value | source | date observed | project
```

Example:
```
- global fertility rate | 2.2 (2024) | UN WPP 2024 | 2026-04 | projects/birth-rates
```

---

<!-- entries appended below -->

<!-- from projects/what-is-the-single-highest-leverage-feature-agentn on 2026-04-13 -->
- SMB SaaS monthly churn rate (median) | 4.7% | ChartMogul SaaS Churn Report 2024 | 2024 | projects/agentnexlify-smb-churn
- Login inactivity churn signal threshold | >14 days since last session → ~3.2× baseline churn odds | OpenView SaaS Benchmarks 2024 | 2024 | projects/agentexlify-smb-churn
- Onboarding non-completion → churn correlation | <40% core workflow completion in month 1 → 2.5× higher 90-day churn | Amplitude Product Intelligence Report 2023 | 2023 | projects/agentexlify-smb-churn
- TTFV churn impact | TTFV >7 days → 30–40% higher 60-day SMB churn | Intercom / Product-Led Growth Collective 2023 | 2023 | projects/agentexlify-smb-churn
- Cost differential: early intervention vs. cancellation-save | 8–12× more expensive to save customer at cancellation vs. early in-product nudge | ProfitWell/Paddle Retention Report 2024 | 2024 | projects/agentexlify-smb-churn
- Automated value-recap email churn reduction | 15–25% reduction in voluntary churn | Intercom/Customer.io/Vero studies 2021–2024 | 2021–2024 | projects/agentexlify-smb-churn
- Exit survey stated vs. actual churn reason divergence | "Missing features" cited in ~40% of exit surveys; correlated with low feature adoption in only ~15% of those cases | Baremetrics / FirstOfficer operator studies 2022–2023 | 2022–2023 | projects/agentexlify-smb-churn
- Involuntary churn share of SMB SaaS churn | ~20–30% of SMB churn | ProfitWell/Paddle retention research | 2023 | projects/agentexlify-smb-churn
- SMB SaaS customer acquisition cost range | $200–$800 (self-serve to inside sales) | OpenView SaaS Benchmarks 2024 | 2024 | projects/agentexlify-smb-churn
- Pre-churn engagement drop lead time | 30–45 days before cancellation in 60–70% of SMB cases | Mixpanel/Amplitude benchmark reports 2022–2025 | 2022–2025 | projects/agentexlify-smb-churn

<!-- from projects/what-is-the-fastest-path-for-agentnexlify-to-hit-1 on 2026-04-13 -->
- Self-serve trial-to-paid conversion rate (agentic SaaS, 2025) | <2% | Emerging operator reports, agentic SaaS cohort 2024–2025 | 2025 | projects/agentnexlify-1m-arr
- Self-serve PLG trial-to-paid conversion rate (standard SaaS benchmark) | 5–8% | OpenView PLG benchmarks 2023 | 2023 | projects/agentnexlify-1m-arr
- Agency channel close rate vs. self-serve | 25–40% vs. 2–5% | OpenView SaaS Benchmarks / channel sales research | 2024 | projects/agentnexlify-1m-arr
- Vertical SaaS time-to-$1M ARR advantage vs. horizontal | 2–3× faster (horizontal takes longer at equivalent team size) | SaaS Capital research on vertical vs. horizontal SaaS 2018–2022 | 2022 | projects/agentnexlify-1m-arr
- Typical CAC: inside sales (SMB SaaS) | $800–$1,500 | OpenView SaaS Benchmarks 2024 | 2024 | projects/agentnexlify-1m-arr
- Typical CAC: agency/reseller channel development | $300–$600 per account (excl. channel dev time) | SaaS channel economics research | 2024 | projects/agentnexlify-1m-arr
- MRR required for $1M ARR | $83,333 | Arithmetic | 2026 | projects/agentnexlify-1m-arr
- Monthly churn rate at which 10 customers/month addition leads to $1M ARR in 12 months at $500 ACV | <1.5% | Derived model (Net MRR growth formula) | 2026 | projects/agentnexlify-1m-arr
- Monthly churn rate at which same acquisition rate fails to reach $1M ARR in 12 months | >3.5% | Derived model | 2026 | projects/agentnexlify-1m-arr
- Gross margin range: agentic SaaS with high compute dependency | 40–60% | Andreessen Horowitz AI company benchmarks 2024 | 2024 | projects/agentnexlify-1m-arr

<!-- from projects/should-agentnexlify-build-sms-deliverability-monit on 2026-04-13 -->
- SMS deliverability monitoring MVP build time (senior engineer) | 5–8 weeks | Technical lens analysis, industry benchmarks | 2026-04 | projects/sms-deliverability-build-buy
- SMS deliverability monitoring in-house Year 1 cost (fully loaded) | $47,000–$97,000 | Economic lens calculation (engineering time + maintenance + infra) | 2026-04 | projects/sms-deliverability-build-buy
- Twilio Insights cost at 100K messages/month | ~$10–$100/month | Twilio pricing documentation (estimated) | 2026-04 | projects/sms-deliverability-build-buy
- Twilio Insights cost at 1M messages/month | ~$100–$1,000/month | Twilio pricing documentation (estimated) | 2026-04 | projects/sms-deliverability-build-buy
- Lightweight webhook logger build time (DLR ingestion + basic dashboard) | 3–5 days senior engineer | Technical lens analysis | 2026-04 | projects/sms-deliverability-build-buy
- Twilio SMS outbound price (US) | $0.0079/message | Twilio public pricing 2025 | 2025 | projects/sms-deliverability-build-buy
- TCR direct registration cost (independent CSP path) | $6,000+/year | The Campaign Registry published fees | 2025 | projects/sms-deliverability-build-buy
- TCPA statutory damages per violation | $500–$1,500 per message | 47 U.S.C. § 227 (TCPA) | current | projects/sms-deliverability-build-buy
- In-house SMS monitoring ongoing maintenance | 0.5–1 day/week ($15,000–$30,000/year) | Technical lens analysis, email deliverability analog | 2026-04 | projects/sms-deliverability-build-buy
- SMS volume threshold where in-house monitoring becomes economically competitive vs. buy | ~5–10M messages/month | Economic lens break-even analysis | 2026-04 | projects/sms-deliverability-build-buy
- Twilio global carrier relationships | 600+ | Twilio documentation 2024 | 2024 | projects/sms-deliverability-build-buy
- US SMS carrier market concentration (top 3 carriers) | >95% of US traffic | Industry standard telecom data | 2025 | projects/sms-deliverability-build-buy

<!-- from projects/is-gohighlevel-beatable-at-the-widget-layer-for-th on 2026-04-13 -->
- GHL reported agency customer count | 60,000+ | GoHighLevel company communications | 2024 | projects/ghl-widget-beatable
- GHL estimated ARR | $200M+ | Industry estimates based on $100M ARR (2022) + growth trajectory | 2024 | projects/ghl-widget-beatable
- GHL iOS App Store rating | 3.2/5 | iOS App Store (contractor-facing GHL mobile app) | 2025 | projects/ghl-widget-beatable
- GHL G2 overall rating | 4.5/5 (1,000+ reviews) | G2.com | 2024-2025 | projects/ghl-widget-beatable
- Jobber estimated customer count | 200,000+ | Jobber company communications / press coverage | 2024 | projects/ghl-widget-beatable
- Jobber estimated valuation | ~$500M | Press coverage / funding rounds | 2024 | projects/ghl-widget-beatable
- ServiceTitan IPO valuation | ~$9.5B | IPO filing / public markets | 2024 | projects/ghl-widget-beatable
- Housecall Pro estimated valuation | ~$400M | Press coverage / funding rounds | 2024 | projects/ghl-widget-beatable
- GHL Unlimited plan price | $297/mo | GHL public pricing page | 2025 | projects/ghl-widget-beatable
- GHL SaaS Mode price | $497/mo | GHL public pricing page | 2025 | projects/ghl-widget-beatable
- Typical agency GHL sub-account resale price to contractor | $197–$497/mo | Agency community forums / reported pricing | 2024-2025 | projects/ghl-widget-beatable
- GHL API rate limit (sub-account level) | ~100 req/min | GHL developer documentation / community reports | 2025 | projects/ghl-widget-beatable
- SMB contractor estimated total software spend (target ICP) | $380–$780/mo combined stack | Derived from Jobber + GHL + CompanyCam + QuickBooks pricing | 2025 | projects/ghl-widget-beatable
- ServiceTitan Marketing Pro launch year | 2022 | ServiceTitan product announcements | 2022 | projects/ghl-widget-beatable
- Jobber Grow launch year | 2023 | Jobber product announcements | 2023 | projects/ghl-widget-beatable
- Estimated window for widget-layer competitive entry before GHL AI closes gap | 18 months | Synthesis of GHL AI investment pace + historical all-in-one improvement rates | 2026 | projects/ghl-widget-beatable
- SMB contractor software market TAM (field service + CRM + marketing automation) | $8–12B | Comparable company valuations + market sizing research | 2024 | projects/ghl-widget-beatable
- Procore (construction vertical SaaS) valuation | ~$9B | Public markets | 2024 | projects/ghl-widget-beatable

<!-- from projects/what-is-the-true-12-month-cac-and-churn-profile-of on 2026-04-14 -->
- SMB AI widget monthly churn rate (estimated upper band, 2025–2026) | 5–7% | Inferred from ChartMogul SMB median + AI-specific value visibility discount | 2025-2026 | projects/smb-ai-widget-cac-churn
- SMB AI widget monthly churn rate (best-practice floor, agency channel + high activation) | 2–3% | Inferred from channel research + activation data synthesis | 2025-2026 | projects/smb-ai-widget-cac-churn
- 12-month customer survival rate at 4.7% monthly churn | 56.4% | Derived: (1-0.047)^12 | 2026-04 | projects/smb-ai-widget-cac-churn
- 12-month customer survival rate at 5.5% monthly churn | 50.9% | Derived: (1-0.055)^12 | 2026-04 | projects/smb-ai-widget-cac-churn
- 12-month customer survival rate at 3.0% monthly churn | 69.4% | Derived: (1-0.030)^12 | 2026-04 | projects/smb-ai-widget-cac-churn
- Blended CAC range: self-serve SMB AI widget | $150–$400 | Synthesized from OpenView benchmarks + AI-specific conversion penalty | 2025-2026 | projects/smb-ai-widget-cac-churn
- Blended CAC range: inside-sales SMB AI widget | $700–$1,500 | Synthesized from research log + AI sales cycle extension | 2025-2026 | projects/smb-ai-widget-cac-churn
- Blended CAC range: agency/reseller channel SMB AI widget | $300–$600 | Research log (projects/agentnexlify-1m-arr) confirmed for AI widget context | 2025-2026 | projects/smb-ai-widget-cac-churn
- LTV/CAC ratio (net of compute costs) at $199/month, 5.5% churn, 50% GM | 4.0× | Derived model | 2026-04 | projects/smb-ai-widget-cac-churn
- LTV/CAC ratio (net of compute costs) at $99/month, 5.5% churn, 50% GM | 2.6× | Derived model | 2026-04 | projects/smb-ai-widget-cac-churn
- LTV/CAC ratio (net of compute costs) at $299/month, 4.5% churn, 50% GM | 6.6× | Derived model | 2026-04 | projects/smb-ai-widget-cac-churn
- Share of 12-month churn events occurring in months 1–3 | ~45–55% | Synthesized from Amplitude/Mixpanel activation and engagement drop research | 2022-2025 | projects/smb-ai-widget-cac-churn
- OpenAI API price reduction since GPT-4 launch | ~80% | Public API pricing history (OpenAI.com) | 2023-2025 | projects/smb-ai-widget-cac-churn
- AI SaaS gross margin projected range at 2026 API pricing | 55–70% | Extrapolated from a16z AI benchmarks + API cost trajectory | 2026 | projects/smb-ai-widget-cac-churn
- EU GDPR/AI Act compliance overhead on CAC | +15–25% for EU-market vendors | Estimated from compliance cost research | 2025-2026 | projects/smb-ai-widget-cac-churn
- Historical SMB SaaS widget monthly churn range (2012–2019 analog) | 3–7% early stage; 2–4% mature operators | SaaS Capital historical research | 2019 | projects/smb-ai-widget-cac-churn
- Inside sales CAC breakeven minimum ACV (SMB, 20% close rate) | ~$300/month | Derived: $1,200 sales cost / 20% close rate = $6,000 CAC; requires ~$500/month ACV at 3:1 LTV/CAC and 3% churn for viability | 2026-04 | projects/smb-ai-widget-cac-churn

<!-- from projects/why-do-most-ai-chat-widget-companies-plateau-or-fa on 2026-04-14 -->
- AI chat widget feature half-life (differentiator to table stakes) | ~2-3 quarters | Derived from competitive analysis of GPT-4 integration, RAG, multimodal rollout timelines 2023-2025 | 2025 | projects/ai-chat-widget-plateau
- Estimated full activation rate (widget → configured KB → CRM integration) | 15-20% of installed customers | Derived from OpenView PLG benchmarks and operator reports | 2025 | projects/ai-chat-widget-plateau
- LTV at $197/month pricing with 4.7% monthly churn | $4,137 gross / ~$2,482 at 60% margin | Derived calculation | 2026 | projects/ai-chat-widget-plateau
- LTV/CAC ratio range for AI chat widget companies | 2.75x (stressed) to 8.3x (best case) | Derived from CAC range ($300-$900) and LTV calculation | 2026 | projects/ai-chat-widget-plateau
- Drift acquisition price by Salesloft | est. $50-150M (undisclosed) vs. $1B 2021 valuation | Tech press reports 2023 | 2023 | projects/ai-chat-widget-plateau
- ManyChat Series A raise | $18M | Crunchbase / press reports | 2019 | projects/ai-chat-widget-plateau
- Hallucination rate in production SMB deployments without guardrails | 3-8% of domain-specific queries | Derived from LLM benchmark studies and production deployment reports 2024-2025 | 2025 | projects/ai-chat-widget-plateau
- GPT-4 API cost reduction 2023-2025 | ~80% reduction in per-token cost | OpenAI pricing history | 2025 | projects/ai-chat-widget-plateau
- LLM first-token latency range (production, GPT-4-turbo) | 0.8-3 seconds | Provider documentation and independent benchmarks | 2025 | projects/ai-chat-widget-plateau
- EU AI Act compliance cost estimate for small AI vendors | $50-200K/year | EU AI Act implementation analyses, legal/consulting estimates | 2025 | projects/ai-chat-widget-plateau
- Shopify merchant count | 2.4M | Shopify investor relations | 2024 | projects/ai-chat-widget-plateau
- Tidio estimated ARR | ~$20M | Industry estimates, press coverage | 2024 | projects/ai-chat-widget-plateau
- Live chat consolidation timeline (Cycle 1) | ~6 years (2008-2014) | Historical industry record | 2026 | projects/ai-chat-widget-plateau
- Chatbot consolidation timeline (Cycle 2) | ~3 years (2016-2019) | Historical industry record | 2026 | projects/ai-chat-widget-plateau
- Projected AI chat widget consolidation timeline (Cycle 3) | 18-24 months from first wave (est. 2023-2025) | Historical compression pattern applied to current cycle | 2026 | projects/ai-chat-widget-plateau
