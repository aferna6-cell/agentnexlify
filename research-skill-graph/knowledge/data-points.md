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

<!-- from projects/what-happens-to-agentnexlify-unit-economics-if-ant on 2026-04-14 -->
- Anthropic Claude 3.5 Sonnet pricing (input) | ~$3.00/MTok | Anthropic pricing page | 2026-Q1 | projects/agentnexlify-anthropic-price-shock
- Anthropic Claude 3.5 Sonnet pricing (output) | ~$15.00/MTok | Anthropic pricing page | 2026-Q1 | projects/agentnexlify-anthropic-price-shock
- Anthropic Claude Haiku pricing (input/output) | ~$0.25/$1.25/MTok | Anthropic pricing page | 2026-Q1 | projects/agentnexlify-anthropic-price-shock
- Google Gemini 1.5/2.0 Flash pricing (input/output) | ~$0.075/$0.30/MTok | Google AI pricing page | 2026-Q1 | projects/agentnexlify-anthropic-price-shock
- Self-hosted Llama 3.x 70B inference cost equivalent | ~$0.20–$0.50/MTok (RunPod/Lambda Labs) | Derived from GPU rental pricing + inference throughput benchmarks | 2026-Q1 | projects/agentnexlify-anthropic-price-shock
- Estimated API cost per 10-turn agentic conversation (Claude Sonnet) | $0.08–$0.35 per session | Derived from token pricing × estimated agentic workflow token consumption | 2026 | projects/agentnexlify-anthropic-price-shock
- Prompt caching savings potential (agentic workflow) | 30–90% reduction in input token cost | Anthropic prompt caching documentation + engineering benchmarks | 2026 | projects/agentnexlify-anthropic-price-shock
- Model tiering cost reduction potential | 40–55% blended cost reduction if 60% of interactions routed to cheap models | Derived from pricing differential × interaction complexity distribution | 2026 | projects/agentnexlify-anthropic-price-shock
- Required price increase to restore 60% GM after 3× API cost shock (API = 25% of revenue) | ~2.25× current price | Derived arithmetic model | 2026 | projects/agentnexlify-anthropic-price-shock
- Gross margin impact: API cost 20% of revenue, 3× increase, no mitigation | 60% → 20% | Derived arithmetic model | 2026 | projects/agentnexlify-anthropic-price-shock
- Gross margin impact: API cost 35% of revenue, 3× increase, no mitigation | 50% → negative | Derived arithmetic model | 2026 | projects/agentnexlify-anthropic-price-shock
- LTV/CAC post-shock (API = 20% revenue, GM drops 60%→20%, CAC $600, MRR $300) | ~2.1× (below 3:1 minimum viable) | Derived model | 2026 | projects/agentnexlify-anthropic-price-shock
- Historical frequency of 3× LLM API price increase within 12 months | 0 observed cases 2020–2026 (direction has been deflationary) | Review of OpenAI, Anthropic, Google pricing history | 2026 | projects/agentnexlify-anthropic-price-shock
- LLM frontier model price reduction 2023→2024 | ~80–95% real-terms reduction across major providers | Multiple provider pricing histories | 2024 | projects/agentnexlify-anthropic-price-shock
- Estimated probability of 3× Anthropic price increase in any 12-month period | 10–20% (tail risk estimate, not base case) | Derived from historical LLM pricing behavior + competitive dynamics analysis | 2026 | projects/agentnexlify-anthropic-price-shock

<<<<<<< HEAD
<!-- from projects/should-agentnexlify-vertical-specialize-contractor on 2026-04-17 -->
- Horizontal SMB AI widget monthly churn rate | 4.5–5.0% | ChartMogul SaaS Churn Report 2024 (cross-reference) | 2024 | projects/vertical-vs-horizontal
- Vertical SMB SaaS monthly churn rate | 2.0–3.0% | SaaS Capital Vertical SaaS Benchmarks 2023 | 2023 | projects/vertical-vs-horizontal
- Contractor-native AI widget pricing range (Hatch, Signpost, Podium contractor tier) | $299–$599/month | Published pricing pages April 2026 | 2026-04 | projects/vertical-vs-horizontal
- Horizontal AI widget pricing range (GHL white-label, BotPenguin, Tidio SMB) | $79–$297/month | Published pricing pages April 2026 | 2026-04 | projects/vertical-vs-horizontal
- Vertical SaaS revenue multiple premium vs. horizontal (2019–2021 market) | 2–3× | SaaS Capital / Bessemer Cloud Index | 2021 | projects/vertical-vs-horizontal
- Contractor CAC via trade association / concentrated vertical channels | $150–$400 per account | SaaS channel economics research; trade association partner program disclosures | 2024 | projects/vertical-vs-horizontal
- Jobber contractor user base | 200,000+ contractors | Jobber Series D investor materials | 2022 | projects/vertical-vs-horizontal
- ServiceTitan contractor customer base | ~8,000 commercial/residential contractors | ServiceTitan marketplace documentation | 2024 | projects/vertical-vs-horizontal
- ACCA membership (HVAC contractors) | 60,000 contractors | ACCA membership data | 2025 | projects/vertical-vs-horizontal
- PHCC membership (plumbing/heating/cooling) | 3,500+ firms | PHCC membership data | 2025 | projects/vertical-vs-horizontal
- US active specialty trade contractor businesses (NAICS 238xxx) | 800,000–1,200,000 | US Census Bureau NAICS data | 2023 | projects/vertical-vs-horizontal
- Estimated digitally-addressable SMB contractors (30–40% of total) | 240,000–480,000 | Derived from Census data + digital adoption estimates | 2026 | projects/vertical-vs-horizontal
- Contractor-vertical LTV/CAC ratio (modeled) | 2.5–4.5× | Derived model (vertical churn + pricing + CAC estimates) | 2026 | projects/vertical-vs-horizontal
- Horizontal SMB AI widget LTV/CAC ratio (modeled) | 0.7–1.4× | Derived model (horizontal churn + pricing + CAC estimates) | 2026 | projects/vertical-vs-horizontal
- Lead response time benchmark for contractors (conversion impact) | <5 minutes = 8× conversion lift | Hatch / Signpost benchmark reports 2023 | 2023 | projects/vertical-vs-horizontal
- Contractor estimate-to-close rate benchmark (residential) | 35–55% | Hatch / Signpost field-service benchmark data 2022–2024 | 2024 | projects/vertical-vs-horizontal
- Review solicitation response rate via automated SMS (contractor) | 15–30% | Podium contractor benchmark reports 2024 | 2024 | projects/vertical-vs-horizontal
- GHL agency reseller network size (estimated) | 10,000+ agency resellers | GHL partner program disclosures / community data | 2025 | projects/vertical-vs-horizontal
- Vertical-to-horizontal SaaS time-to-$1M ARR advantage | 2–3× faster | SaaS Capital vertical SaaS research 2018–2022 | 2022 | projects/vertical-vs-horizontal (confirmed from research log)
- Contractor vertical competitive field (native AI widget competitors) | 3–5 credible competitors (Hatch, Signpost, Siro, partial Podium/Birdeye) | G2 category data April 2026 | 2026-04 | projects/vertical-vs-horizontal
- Horizontal SMB AI widget competitive field | 15+ credible competitors at sub-$500/month | G2 category data April 2026 | 2026-04 | projects/vertical-vs-horizontal
=======
<!-- from projects/should-agentnexlify-vertical-specialize-contractor on 2026-04-15 -->
- US licensed contractor businesses (total) | ~10M | IBIS World Contractor Industry Reports | 2024–2025 | projects/agentnexlify-vertical-horizontal
- US contractor businesses (top 4 trades: HVAC, plumbing, electrical, roofing) | ~3–4M | IBIS World trade segment breakdowns | 2024–2025 | projects/agentnexlify-vertical-horizontal
- Contractor SAM for AI widget ($149–$249/mo) — businesses >$300K revenue, >2 employees | ~1.5–2M | Derived from IBIS World + SBA small business size data | 2025 | projects/agentnexlify-vertical-horizontal
- AgentNexLiFy contractor vertical ARR potential at 1% SAM penetration, $199/mo | $29M–$47M ARR | Derived model | 2026 | projects/agentnexlify-vertical-horizontal
- ServiceTitan valuation | $9.5B | Reported financing round | 2022 | projects/agentnexlify-vertical-horizontal
- ServiceTitan founding to $9.5B valuation timeline | 10 years (founded 2012) | Public records | 2022 | projects/agentnexlify-vertical-horizontal
- Jobber pricing range | $69–$349/month | Jobber.com published pricing | 2025 | projects/agentnexlify-vertical-horizontal
- ServiceTitan pricing range | $250–$600/month per location | Industry reports / operator surveys | 2024 | projects/agentnexlify-vertical-horizontal
- Housecall Pro pricing range | $49–$199/month | Housecall Pro published pricing | 2025 | projects/agentnexlify-vertical-horizontal
- Contractor vertical LTV/CAC estimate (agency channel, $199/mo, 2.5% monthly churn) | 9:1 to 17:1 | Derived model using prior research CAC and LTV assumptions | 2026 | projects/agentnexlify-vertical-horizontal
- Horizontal SMB LTV/CAC estimate (self-serve, $149/mo, 4.7% monthly churn) | 2.7:1 to 7:1 | Derived model using prior research data points | 2026 | projects/agentnexlify-vertical-horizontal
- Vertical SaaS historical success rate (started vertical, expanded to $10M+ ARR) | >80% of sample companies studied | SaaS Capital / Bessemer Venture Partners vertical SaaS research 2018–2022 | 2022 | projects/agentnexlify-vertical-horizontal
- US skilled trades unfilled jobs | ~650,000 | Bureau of Labor Statistics | 2024–2025 | projects/agentnexlify-vertical-horizontal
- Google LSA share of contractor digital leads | ~60–70% | Industry practitioner estimates / Search Engine Land contractor marketing reports | 2024 | projects/agentnexlify-vertical-horizontal
- 30-year US mortgage rate (2026 context) | ~6.5–7% | Federal Reserve / Freddie Mac PMMS | 2026-Q1 | projects/agentnexlify-vertical-horizontal
- GoHighLevel ARR (estimated) | $200M+ | Industry reports / founder interviews | 2024–2025 | projects/agentnexlify-vertical-horizontal
- ServiceTitan acquisition of Hatch (AI sales comms) | confirmed acquisition | Public announcement | 2022 | projects/agentnexlify-vertical-horizontal
- Typical contractor job value range | $300–$3,000 per service call | Industry trade association data / contractor operator surveys | 2024 | projects/agentnexlify-vertical-horizontal
>>>>>>> 6662e74 (research: should-agentnexlify-vertical-specialize-contractor)

<!-- from projects/how-have-historical-document-automation-waves-fax- on 2026-04-18 -->
- US fax machine installed base | ~300K (1984) → 4M (1988) → 22M (1994) → peak ~30M (1997) | FCC Historical Reports / industry data | 1984–1997 | projects/document-automation-waves
- Fax machine price at mass SMB adoption inflection | <$300 (1991–1992) | Consumer electronics industry data | 1991–1992 | projects/document-automation-waves
- US business email accounts | ~10M (1995) → 55M (1999) → 130M (2003) | IDC/Radicati Group historical email statistics | 1995–2003 | projects/document-automation-waves
- SMB email adoption rate | ~60% by 2000, ~90% by 2004 | IDC SMB technology adoption surveys | 2000–2004 | projects/document-automation-waves
- DocuSign paying customers | ~50K (2008) → 300K (2013) → 1M (2016) → 4M+ (2020) | DocuSign SEC filings / investor reports | 2008–2020 | projects/document-automation-waves
- SMB e-signature adoption (US) | ~15% (2015) → ~35% (2019) → ~50% (2023) | DocuSign/Adobe market research estimates | 2015–2023 | projects/document-automation-waves
- DocuSign personal plan price | $30/month (2010) → $15/month (2017) → $10/month (2023) | DocuSign public pricing pages | 2010–2023 | projects/document-automation-waves
- HelloSign paying customers at Dropbox acquisition | ~80,000 | Dropbox acquisition announcement / press reports | 2019 | projects/document-automation-waves
- DocuSign SMB customer mix from Salesforce AppExchange | estimated 30–40% of SMB customers via partner channels | Salesforce AppExchange partner reports / DocuSign investor day | 2015–2018 | projects/document-automation-waves
- GPT-4 inference cost | ~$0.06/1K tokens (2023) | OpenAI pricing page | 2023 | projects/document-automation-waves
- GPT-4o inference cost | ~$0.005/1K tokens input (2024) | OpenAI pricing page | 2024 | projects/document-automation-waves
- AI inference cost reduction rate | approximately 10× per 24 months | Epoch AI ML Compute Research | 2024 | projects/document-automation-waves
- Microsoft 365 US SMB installed base share | ~60% | Salesforce SMB Trends Report / IDC | 2024 | projects/document-automation-waves
- Google Workspace US SMB installed base share | ~28% | IDC workplace software market share | 2024 | projects/document-automation-waves
- Shopify global merchant count | ~4.4M | Shopify Q4 2024 earnings report | 2024 | projects/document-automation-waves
- Intuit/QuickBooks global small business users | ~30M | Intuit fiscal year 2024 earnings | 2024 | projects/document-automation-waves
- Median US SMB annual software spend (5–50 employees) | $10,000–$15,000 total | Salesforce SMB Trends Report 2023 | 2023 | projects/document-automation-waves
- SMB per-tool monthly spend ceiling (no-justification-required) | ~$100–$150/month | Salesforce/Gartner SMB purchasing behavior research | 2023–2024 | projects/document-automation-waves
- Heavy user concentration in B2B AI SaaS | top 10% of customers consume 60–70% of compute | Andreessen Horowitz AI SaaS usage research | 2024 | projects/document-automation-waves
- Time from fax availability to 50% SMB penetration | ~9 years (1984→1993) | FCC/industry installed base data | historical | projects/document-automation-waves
- Time from Hotmail launch to 50% SMB email adoption | ~4 years (1996→2000) | IDC historical data | historical | projects/document-automation-waves
- HubSpot AI tools adoption within HubSpot SMB base | ~35% enabled | HubSpot 2025 State of Marketing Report | 2025 | projects/document-automation-waves
- Notion AI adoption among Notion Business tier users | ~40% | Notion usage reports / press | 2024–2025 | projects/document-automation-waves
- Copilot for Microsoft 365 organizational adoption | 400,000+ organizations | Microsoft earnings / press | early 2025 | projects/document-automation-waves
- PandaDoc SMB pricing | $19/month (2014) → $35/month (2024) | PandaDoc public pricing history | 2014–2024 | projects/document-automation-waves

<!-- from projects/what-is-the-real-defensibility-of-a-widget-first-a on 2026-04-18 -->
- GPT-4 API input price at launch | $0.06/1K tokens | OpenAI pricing history | 2023-03 | projects/widget-defensibility
- GPT-4o API input price (April 2026) | ~$0.0025/1K tokens | OpenAI pricing page | 2026-04 | projects/widget-defensibility
- Frontier API price decline over 36 months | ~96% reduction | OpenAI pricing history (derived) | 2023–2026 | projects/widget-defensibility
- Open-weight model parity with GPT-4 class (MMLU/MT-Bench) | ~95% (Llama 3 405B, Qwen 2.5 72B) | Meta AI / Alibaba Qwen technical reports | 2024–2025 | projects/widget-defensibility
- Time for open-weight model to reach frontier capability parity | 4–8 quarters | LMSYS Chatbot Arena / Papers With Code benchmark tracking | 2023–2025 | projects/widget-defensibility
- DeepSeek V3/R1 claimed training cost | $5–6M (vs. $50–100M+ for comparable US models) | DeepSeek technical report / industry analysis | 2024–2025 | projects/widget-defensibility
- Platform feature absorption rate (standalone SaaS features) | ~70% lose >50% TAM within 24 months of platform entry | a16z "Innovator's Dilemma in SaaS" / CBInsights platform-kill analysis | 2021–2023 | projects/widget-defensibility
- Standalone feature survival rate post-platform absorption | ~20% survive by vertical deepening or upmarket move; ~10% acquired | a16z / CBInsights | 2021–2023 | projects/widget-defensibility
- Behavioral switching cost estimate (SMB AI widget, 12+ month user) | 40–80 hours operator re-implementation time | Derived from SMB operational complexity benchmarks | 2025–2026 | projects/widget-defensibility
- Time lag between technical parity and customer switching | 12–24 months (historical analog: cloud storage, ESP commoditization) | a16z cloud economics research / ESP industry history | 2022–2024 | projects/widget-defensibility
- Deep vertical integration engineering investment | $200K–$500K equivalent per segment | Derived from integration complexity benchmarks | 2025 | projects/widget-defensibility
- Capability moat depreciation rate (AI widget layer) | ~80% per year in current environment | Derived from API price decline + open-weight parity timeline | 2026 | projects/widget-defensibility
- GoHighLevel estimated ARR | $200M+ | Industry reports / SaaS community estimates | 2025 | projects/widget-defensibility
- Minimum customer volume to activate multi-tenant data flywheel | ~1,000+ active customers in specific vertical | Derived from data science benchmarks on behavioral pattern detection | 2025 | projects/widget-defensibility

<!-- from projects/which-smb-verticals-have-the-highest-willingness-t on 2026-04-18 -->
- Home services inbound call answer rate (solo operator) | 38% | Marchex SMB call analytics 2024 | 2024 | projects/smb-ai-booking-wtp
- Home services inbound call answer rate (3-5 person shop) | ~65% | Marchex SMB call analytics 2024 | 2024 | projects/smb-ai-booking-wtp
- After-hours booking request share (home services) | 35–60% | Broadly/ServiceTitan operator data 2024 | 2024 | projects/smb-ai-booking-wtp
- Missed call to competitor booking rate (home services) | 30–50% within 24 hours | BrightLocal local service research 2023 | 2023 | projects/smb-ai-booking-wtp
- Dental practice no-show/cancellation rate | 15–25% | American Dental Association 2023 | 2023 | projects/smb-ai-booking-wtp
- Med-spa no-show/cancellation rate | 20–35% | AmSpa industry data 2023 | 2023 | projects/smb-ai-booking-wtp
- After-hours booking request share (dental/medical) | 40–55% | Zocdoc + Mindbody platform data aggregates 2024 | 2024 | projects/smb-ai-booking-wtp
- AI confirmation loop no-show reduction rate | 25–40% | Klara Health / Weave platform data 2023 | 2023 | projects/smb-ai-booking-wtp
- Dental front-desk wage increase 2021-2024 | 18–22% | ADA + BLS data 2024 | 2024 | projects/smb-ai-booking-wtp
- Dental front-desk annual turnover rate | 35–45% | Dental Economics 2023 | 2023 | projects/smb-ai-booking-wtp
- Solo attorney average annual revenue | $200,000–$600,000 | Clio Legal Trends Report 2023 | 2023 | projects/smb-ai-booking-wtp
- Solo attorney billing rate | $200–$500/hour | Clio Legal Trends Report 2023 | 2023 | projects/smb-ai-booking-wtp
- US unfilled trade jobs (home services labor shortage) | 650,000+ | Associated Builders and Contractors 2024 | 2024 | projects/smb-ai-booking-wtp
- US trade labor shortage projected duration | Through 2035 (worsening) | ABC demographic analysis 2024 | 2024 | projects/smb-ai-booking-wtp
- Clio legal platform user count | 150,000+ legal professionals | Clio company data 2024 | 2024 | projects/smb-ai-booking-wtp
- LegalTech adoption acceleration | +40% since 2022 | Clio Legal Trends Report 2024 | 2024 | projects/smb-ai-booking-wtp
- SMB average annual software stack spend 2017 | $1,100/year | Vendr SaaS spending data | 2017 | projects/smb-ai-booking-wtp
- SMB average annual software stack spend 2024 | $5,200/year | Vendr SaaS spending data | 2024 | projects/smb-ai-booking-wtp
- Boulevard (salon SaaS) funding raised | $70M | Crunchbase / company announcements | 2023 | projects/smb-ai-booking-wtp
- Boulevard salon SaaS pricing (multi-chair) | $175/month | Boulevard pricing page 2024 | 2024 | projects/smb-ai-booking-wtp
- Vagaro salon SaaS pricing range | $30–$130/month | Vagaro pricing page 2024 | 2024 | projects/smb-ai-booking-wtp
- OpenTable acquisition price (Priceline) | $2.6B | Public record 2014 | 2014 | projects/smb-ai-booking-wtp
- OpenTable base subscription price | $249/month | OpenTable pricing 2024 | 2024 | projects/smb-ai-booking-wtp
- Mindbody acquisition price (Vista Equity) | $1.9B | Public record 2019 | 2019 | projects/smb-ai-booking-wtp
- Weave platform estimated ARR | ~$200M | Public analyst estimates 2024 | 2024 | projects/smb-ai-booking-wtp
- ServiceTitan estimated ARR | ~$600M | Public analyst estimates 2024 | 2024 | projects/smb-ai-booking-wtp
- Slang.ai funding raised | $20M | Crunchbase 2023 | 2023 | projects/smb-ai-booking-wtp
- Jobber estimated ARR | $250M+ | Public analyst estimates 2024 | 2024 | projects/smb-ai-booking-wtp
- Median home services business annual revenue (solo/2-person) | $300,000–$1.2M | US Census Bureau SUSB 2022 | 2022 | projects/smb-ai-booking-wtp
- Median dental practice annual revenue | $800,000–$1.2M | ADA Health Policy Institute 2023 | 2023 | projects/smb-ai-booking-wtp
- Median med-spa annual revenue | $500,000–$1.5M | AmSpa 2023 | 2023 | projects/smb-ai-booking-wtp
- AI booking WTP range (home services) | $200–$500/month | Derived from competitive pricing + ROI analysis | 2026 | projects/smb-ai-booking-wtp
- AI booking WTP range (dental) | $400–$700/month | Derived from competitive pricing + ROI analysis | 2026 | projects/smb-ai-booking-wtp
- AI booking WTP range (med-spa) | $200–$450/month | Derived from competitive pricing + ROI analysis | 2026 | projects/smb-ai-booking-wtp
- AI booking WTP range (legal solo) | $200–$600/month | Derived from competitive pricing + ROI analysis | 2026 | projects/smb-ai-booking-wtp
- AI booking WTP range (hair salon multi-chair 4+) | $100–$200/month | Derived from competitive pricing + ROI analysis | 2026 | projects/smb-ai-booking-wtp
- AI booking WTP range (restaurant casual) | $100–$200/month | Derived from competitive pricing + ROI analysis | 2026 | projects/smb-ai-booking-wtp

<!-- from projects/what-regulatory-risks-tcpa-state-ai-laws-can-spam- on 2026-04-18 -->
- TCPA statutory damages per violation (negligent) | $500 | 47 U.S.C. § 227(b)(3) | 2026-04 | projects/regulatory-risks-agentnexlify
- TCPA statutory damages per violation (willful) | $1,500 | 47 U.S.C. § 227(b)(3) | 2026-04 | projects/regulatory-risks-agentnexlify
- TCPA class action settlement range (typical) | $2M–$75M | TCPA World litigation database 2022–2024 | 2024 | projects/regulatory-risks-agentnexlify
- TCPA defense costs before settlement | $500K–$2M | TCPA practitioner estimates | 2024 | projects/regulatory-risks-agentnexlify
- Consent management platform cost (TrustedForm/Jornaya) | $500–$2,000/month | vendor published pricing | 2026 | projects/regulatory-risks-agentnexlify
- In-house consent logging engineering cost (basic) | $10K–$30K one-time build | engineering estimate | 2026 | projects/regulatory-risks-agentnexlify
- Compliance tech market size | $2B+ growing ~18% annually | Grand View Research 2024 | 2024 | projects/regulatory-risks-agentnexlify
- FCC one-to-one consent rule projected TCPA litigation reduction | 30–40% | FCC rule-making record 2024 | 2024 | projects/regulatory-risks-agentnexlify
- FCC one-to-one consent rule effective date | January 27, 2025 (vacated same month by 11th Circuit) | Insurance Marketing Coalition v. FCC, 11th Cir. 2025 | 2025 | projects/regulatory-risks-agentnexlify
- BIPA violation statutory damages | $1,000 (negligent) to $5,000 (intentional) per violation | 740 ILCS 14/20 | 2026-04 | projects/regulatory-risks-agentnexlify
- CAN-SPAM opt-out honor window | 10 business days | 15 U.S.C. § 7704(a)(3) | 2026-04 | projects/regulatory-risks-agentnexlify
- GDPR maximum fine | 4% of global annual revenue or €20M, whichever higher | GDPR Art. 83 | 2026-04 | projects/regulatory-risks-agentnexlify
- TCPA class action plaintiff bar concentration | ~200–300 serial plaintiffs filed >90% of individual suits (certain periods) | TCPA World database 2022–2024 | 2024 | projects/regulatory-risks-agentnexlify
- Typical TCPA specialized insurance annual cost (meaningful limits) | $15K–$50K/year | insurance market data | 2024 | projects/regulatory-risks-agentnexlify
- Colorado AI Act effective date | ~2026 (phased) | SB 21-169 and 2024 amendments | 2026-04 | projects/regulatory-risks-agentnexlify
- Texas TDPSA effective date | July 1, 2024 | Texas Data Privacy and Security Act | 2024 | projects/regulatory-risks-agentnexlify
- NYC Local Law 144 (AI bias audit, employment) effective date | January 1, 2023 | NYC Admin. Code § 20-871 | 2023 | projects/regulatory-risks-agentnexlify
- FCC AI voice declaratory ruling (synthetic = artificial) | 2024 | FCC Declaratory Ruling, Feb 2024 | 2024 | projects/regulatory-risks-agentnexlify
- Historical regulatory-to-enforcement lag (prior TCPA/CAN-SPAM waves) | 18–36 months | historical analysis of SMS/fax/email regulatory cycles | 2026-04 | projects/regulatory-risks-agentnexlify

<!-- from projects/is-white-label-reseller-distribution-gohighlevel-m on 2026-04-19 -->
- GHL Agency Pro plan price (white-label enabled) | $297/mo | GoHighLevel public pricing | 2025 | projects/white-label-reseller-viability
- GHL estimated reseller partner count | 60,000+ | Multiple industry sources / GHL public statements | 2024-2025 | projects/white-label-reseller-viability
- GHL estimated ARR | $200M+ | SaaS industry reporting | 2024 | projects/white-label-reseller-viability
- GHL founding to reseller model launch | ~18 months (founded 2018, reseller growth 2019-2020) | GHL company history | 2026 | projects/white-label-reseller-viability
- Vendasta reseller partner count | 60,000+ | Vendasta public statements | 2024 | projects/white-label-reseller-viability
- Vendasta Series B raise | $200M | Crunchbase / public reporting | 2021 | projects/white-label-reseller-viability
- Vendasta partner 12-month retention: partners with active clients | ~70% | Vendasta partner program documentation / industry reporting | 2024 | projects/white-label-reseller-viability
- Vendasta partner 12-month retention: partners without active clients in 90 days | ~20% | Vendasta partner program documentation / industry reporting | 2024 | projects/white-label-reseller-viability
- Vendasta Pareto partner revenue distribution | top 20% of partners generate ~80% of revenue | B2B2SMB platform benchmark research | 2023 | projects/white-label-reseller-viability
- US digital marketing agencies (total estimated) | 150,000+ | Agency Spotter 2024 estimate | 2024 | projects/white-label-reseller-viability
- US contractor/home-services focused marketing agencies (estimated) | 8,000–15,000 | Derived estimate from Agency Spotter vertical segmentation | 2024 | projects/white-label-reseller-viability
- Typical productive partner CAC (including failed partner acquisition cost) | $10,000–$15,000 per productive partner (5:1 conversion on raw partner CAC of $2,000–$3,000) | Derived from Pareto dynamics and B2B2SMB benchmarks | 2026 | projects/white-label-reseller-viability
- Minimum viable white-label infrastructure build time (small engineering team) | 3–6 months | Technical estimation based on feature requirements | 2026 | projects/white-label-reseller-viability
- White-label infrastructure components build estimate: partner admin panel | 8–12 weeks | Technical estimation | 2026 | projects/white-label-reseller-viability
- White-label infrastructure components build estimate: billing isolation (Stripe Connect) | 4–6 weeks | Technical estimation | 2026 | projects/white-label-reseller-viability
- White-label infrastructure components build estimate: branded dashboards / custom domains | 3–4 weeks | Technical estimation | 2026 | projects/white-label-reseller-viability
- GHL SaaS Mode percentage of revenue from reseller channel | ~70% | Industry analyst estimates | 2024 | projects/white-label-reseller-viability
- ServiceTitan agency partner program launch | 2023 | ServiceTitan public announcements | 2023 | projects/white-label-reseller-viability
