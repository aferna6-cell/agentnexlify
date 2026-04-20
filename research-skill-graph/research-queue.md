# Research Queue

Pending research questions. The automation picks the first unchecked item, runs it, and marks it done. Open-questions from each completed project auto-append here.

## Format

```
- [ ] question text here
- [x] completed question
```

Optional metadata after the question: `(depth:standard)` or `(depth:quick)` or `(depth:deep)` maps to research-frameworks.md levels.

## Seed questions (AgentNexLiFy-relevant)

- [x] Is GoHighLevel beatable at the widget layer for the SMB contractor segment? (depth:standard)
- [x] What is the true 12-month CAC and churn profile of SMB AI widget products under $500/mo? (depth:standard)
- [x] Why do most AI chat widget companies plateau or fail in months 6-18? (depth:standard)
- [x] What happens to AgentNexLiFy unit economics if Anthropic raises prices 3x in 12 months? (depth:standard)
- [x] Should AgentNexLiFy vertical-specialize (contractors only) or stay horizontal across SMBs? (depth:deep)
- [x] How have historical document-automation waves (fax, email, workflow SaaS) priced and distributed to SMBs, and what applies now? (depth:standard)
- [x] What is the real defensibility of a widget-first AI product once foundation models become commodity? (depth:deep)
- [x] Which SMB verticals have the highest willingness to pay for AI appointment booking and why? (depth:standard)
- [x] What regulatory risks (TCPA, state AI laws, CAN-SPAM) most threaten AgentNexLiFy's outbound automation? (depth:standard)
- [x] Is white-label reseller distribution (GoHighLevel model) a viable growth lever for AgentNexLiFy? (depth:standard)

## Auto-iterated questions (appended by script)

<!-- open-questions from completed projects land below this line -->
- [x] What is AgentNexLiFy's current telemetry coverage? Are agent task completions, session data, and workflow activations already logged at the tenant level — or does a Health Score Dashboard require backend instrumentation work first?
- [ ] Is the SMB segment primarily self-serve (no sales/CS touch) or sales-assisted? This determines whether the intervention channel should be in-product, automated email, or CSM alert.
- [ ] What does the actual AgentNexLiFy churn data show — is the dominant churn signal engagement decay (supporting the dashboard recommendation) or stated product-fit complaints (supporting a different roadmap priority)?
- [ ] What is the median time-to-first-value for a new AgentNexLiFy SMB tenant today? If TTFV >7 days, onboarding activation gates may be higher leverage than ongoing health scores.
- [ ] Has AgentNexLiFy run any exit surveys or cancellation-flow data collection? The stated vs. behavioral churn reason gap (contrarian lens) can only be resolved with this data.
- [ ] What is the current monthly SMB churn rate for AgentNexLiFy specifically, and how does it compare to the 4.7% industry median? If churn is already below median, the return on this investment changes.
- [ ] Are there agent output quality issues (failed tasks, low completion rates) that would make surfacing a health score counterproductive without a quality improvement pass first?
- [ ] What is AgentNexLiFy's current MRR and customer count? (The 12-month path is entirely different from a $0 baseline vs. a $50K MRR baseline — this is the most critical unknown)
- [ ] What is the current monthly churn rate? (If above 4%, churn infrastructure must be the only priority before any channel investment)
- [ ] Does AgentNexLiFy have existing warm relationships with agency partners or vertical operators who could fast-track the partner channel?
- [ ] Which vertical has been validated (if any) as highest pain + lowest competitive noise in 2026? (Legal, real estate, home services, e-commerce ops, and healthcare admin are candidates — none confirmed)
- [ ] What is the product's current TTFV for a new customer completing self-serve setup? (If >48 hours, PLG is not viable and the path must be sales-assisted)
- [ ] Is pricing validated? Has $1,000/month been tested against SMB buyers, or is current pricing sub-$300 based on assumed price sensitivity?
- [ ] What is AgentNexLiFy's available runway? (A 12-month ARR target that requires burning through 18 months of runway to achieve is not a viable path regardless of growth rate)
- [ ] What is the gross margin on the product? (Agentic products with high compute costs may have 40–50% gross margins vs. 70–80% for traditional SaaS, which changes the LTV/CAC calculus significantly)
- [ ] Has the competitive displacement thesis been tested — are target SMBs actually evaluating AgentNexLiFy vs. Salesforce/HubSpot AI add-ons, or is AgentNexLiFy addressing a workflow those incumbents don't touch?
- [ ] What is AgentNexLiFy's current monthly SMS message volume (platform-wide and per tenant)? — this is the single most important variable; answer changes the recommendation materially above/below ~500K messages/month
- [ ] Are AgentNexLiFy's tenants the SMS senders (platform play: tenants use AgentNexLiFy to send their own messages) or does AgentNexLiFy send on behalf of tenants (managed service)? — this changes 10DLC registration structure, compliance ownership, and monitoring accountability entirely
- [ ] Is SMS deliverability monitoring being considered as an internal operational tool OR as a tenant-facing product feature? — if it's a product feature tenants pay for, in-house build immediately becomes the correct answer regardless of current scale
- [ ] Has AgentNexLiFy completed 10DLC brand and campaign registration for all active sending use cases? — if not, this is higher urgency than monitoring infrastructure and should be addressed first
- [ ] What specific deliverability failures or incidents have prompted this question? — understanding the actual failure mode (registration issue vs. carrier filtering vs. operational visibility gap) determines the right solution; "we want to monitor" vs. "we have active delivery failures" are very different situations
- [ ] What is AgentNexLiFy's international SMS exposure (% of messages going outside US)? — any meaningful international volume strongly argues against in-house build
- [ ] Does AgentNexLiFy's product roadmap include RCS, WhatsApp Business API, or other messaging channels in 12–18 months? — if yes, investing in SMS-specific monitoring infrastructure has a shorter useful life
- [ ] What is the current TCPA/CASL/GDPR compliance posture for SMS workflows? — if compliance gaps exist, they represent higher expected cost risk than deliverability gaps and should be prioritized
- [ ] What percentage of SMB contractors in the $300K–$2M revenue range make their own software purchasing decisions vs. deferring to their marketing agency? This is the most important unknown — it determines whether direct-to-contractor GTM is viable.
- [ ] What is the actual adoption rate of ServiceTitan Marketing Pro and Jobber Grow among their existing FSM customer bases? If >30%, the FSM platform window may already be closing.
- [ ] Does Google's GMB API access pose a near-term risk to review widget products? What is the current rate-limiting and access policy for third-party review display widgets in 2026?
- [ ] What is the size of the "field-heavy, tech-curious, 5+ jobs/week, self-managed" contractor ICP segment within the total US SMB contractor market (~10M businesses)? Is it 50,000? 500,000? This determines market size for the beachhead.
- [ ] Can a GHL widget competitor be built as a genuine white-label add-on that agencies install *within* their GHL sub-accounts (via GHL's custom widget/iframe functionality), enabling agency channel without agency conflict? What are the technical constraints on this embedding approach given GHL's API limitations?
- [ ] What is GHL's roadmap for contractor-vertical-specific features in 2026–2027? Has GHL announced or hired for trades/home services vertical specialization?
- [ ] What is Podium's current market share in the trades/home services review + messaging widget category, and what is their contractor NPS vs. GHL's?
- [ ] What would a Jobber or ServiceTitan formal partner integration require in terms of technical certification, revenue share, and exclusivity? What is the timeline from application to active partnership?
- [ ] What is the true churn rate for AI widget products specifically (not general SMB SaaS), segmented by activation cohort? No published primary dataset exists for this; requires operator survey or direct data access from ChartMogul/Baremetrics with AI-specific filtering.
- [ ] What is the CAC trend line for SMB AI widget products month-over-month from January 2024 to April 2026? The AI vendor fatigue hypothesis needs time-series data to validate; current evidence is cross-sectional.
- [ ] Do agency/reseller-acquired customers for AI widgets churn at 30–40% lower rates than self-serve customers, as inferred from general SaaS data? This extrapolation from general channel research has not been confirmed with AI-widget-specific cohort data.
- [ ] At what price point does "deliberate buyer" effect overcome "higher price barrier" effect to produce net churn reduction? The first-principles lens predicts a non-linear price/churn relationship, but the inflection point is unknown without A/B pricing test data.
- [ ] What share of AI widget churn in 2025–2026 is attributable to platform substitution (e.g., customer cancels because GHL added the feature) vs. product dissatisfaction vs. involuntary? This substitution churn is a new category not captured in legacy churn frameworks.
- [ ] How fast are LLM API costs actually declining at the volume levels relevant to sub-$500/month AI widget products? The gross margin improvement thesis depends on this trajectory.
- [ ] What is the 12-month CAC and churn profile segmented by product category within "AI widgets" (chat widget vs. review management vs. scheduling AI vs. content generation)? Aggregating across categories may be masking divergent economics.
- [ ] Is there a minimum viable activation completion rate threshold (e.g., 60% core workflow completion) below which no retention intervention recovers churn? The data suggests this exists but the specific threshold is unknown.
- [ ] How does the EU AI Act compliance overhead translate into specific CAC increases for EU-market SMB AI widget vendors in 2026?
- [ ] Is there a measurable LTV/CAC difference between "widget-only" companies and "widget-as-wedge" companies at the same ARR level, and at what ARR does the divergence become statistically significant?
- [ ] What is AgentNexLiFy's actual current Anthropic API cost as a percentage of monthly revenue? (This single number determines severity of impact; without it, all models have wide error bars)
<<<<<<< HEAD
- [ ] What is the actual number of US SMB contractors (NAICS 238xxx) who are currently paying for any SaaS tool above $100/month? This determines whether the contractor SAM supports venture-scale growth or a profitable-but-capped business.
=======
- [ ] Has ServiceTitan publicly disclosed a website chat widget or AI-powered lead capture product on their 2026 roadmap? (Resolves Contrarian Counter 1; highest priority intelligence gap)
>>>>>>> 6662e74 (research: should-agentnexlify-vertical-specialize-contractor)
- [ ] Has any pure-play widget-first AI company successfully navigated a foundation model commoditization cycle and retained >60% gross margin and >$10M ARR? (The cycle is new enough that no confirmed case study exists. This is the most important unknown.)
- [ ] What percentage of HVAC/plumbing operators are already receiving AI booking features from ServiceTitan or Jobber — if >30%, the standalone market is partially absorbed and urgency increases
- [ ] What is AgentNexLiFy's current Terms of Service language regarding TCPA compliance, and has it been reviewed by TCPA-specialized counsel? The platform's contractual liability exposure is unknown without this review.
- [ ] What is the actual size of the contractor-focused digital marketing agency market in the US, and what percentage are actively looking to add AI widget products to their service stack? (GHL's 150,000+ general agency market may not translate to AgentNexLiFy's narrower contractor vertical)
- [ ] Does AgentNexLiFy's application database contain tenant-tagged records for agent task completions (e.g., a table with tenant_id, completed_at, status columns)? This single question determines whether a v1 Health Score Dashboard can be built without new instrumentation.
