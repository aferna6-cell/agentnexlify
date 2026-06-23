---
title: "GoHighLevel AI Employee — Reselling Mechanics and $97/Sub Unlimited Tier"
category: competitors
tags: ["gohighlevel", "ai-employee", "reselling", "rebilling", "agency", "ai-pricing"]
sources: ["raw/competitors/help-gohighlevel-com-support-solutions-articles-155000003906-ai-employ.md"]
created: 2026-04-21
updated: 2026-04-21
summary: "GHL bundles Voice/Conversation/Reviews/Content/Funnel AI into an 'AI Employee' add-on at $97/mo per sub-account, with agency-set rebilling markups commonly 2-2.5x that anchor the category's reseller margins."
---

# GoHighLevel AI Employee — Reselling Mechanics and $97/Sub Unlimited Tier

GoHighLevel's AI Employee is not a product — it is a billing construct that bundles Voice AI, Conversation AI, Reviews AI, Funnel/Website AI, and Content AI under one subscription line. Agencies can choose usage-based pricing per AI action or flip each sub-account to a flat $97/mo unlimited plan. The agency then sets its own markup (commonly 2-2.5x) and rebills the client — turning AI into a white-label SaaS line item. This is the mechanism that lets GHL agencies price AI packages at $200-$600/mo per client while paying $97 wholesale, and it is the single largest distinction between GHL's distribution model and the direct-sales model used by Phonely, Birdeye, and AgentNexLiFy.

The toggle lives at Agency View → Company → AI Employee, and access is granted per sub-account. Once enabled at the agency level, each sub-account has a toggle in the reselling tab controlling whether the client sees the "Upgrade to AI Employee" button inside Voice AI, Conversation AI, Reviews AI, and Content AI modules. The rebilling slider moves from 1x to roughly 5x — the support doc shows a 2.5x example where a $1 wholesale cost becomes $2.50 to the client. The agency keeps the difference. No invoice is issued to the client by GHL; billing flows through the agency's Stripe account under SaaS Mode, which requires the $497/mo Agency Pro tier documented in [[ghl-pricing-teardown-2026]].

The product boundary of "AI Employee" is moving. The 2026 documentation explicitly warns that some AI features have been moved to free-use and removed from the AI Employee billing construct, and that agencies must verify product scope before directing a client to upgrade. This is quiet unbundling — free-use features no longer carry rebill margin, so an agency that packaged "all AI for $297/mo" based on the 2025 bundle now finds the scope shrinking under them. Voice AI remains outside the unlimited $97/mo plan and is always billed usage-based on top (approximately $0.163/min including LLM tokens), so a plumber handling 6,000 voice minutes/mo still generates ~$978 in additional charges the $97 flat plan does not cover.

Phone and SMS are explicitly excluded from AI Employee — they are billed via LC Phone or Twilio under separate line items. This matters because [[ghl-carrier-pricing-april-2026]] describes carrier rate increases from April 1 (AT&T) and May 1 (Verizon) 2026, meaning the rebillable telecom margin inside an agency's AI package is compressing simultaneously with the AI product scope shrinking. The all-in-one positioning holds, but the underlying unit economics are drifting in the agency's disfavor, and many agencies will absorb the increases rather than reprice clients mid-contract.

Rebilling markup patterns observed in the GHL agency ecosystem cluster at 2x for competitive markets and 2.5-3x where the agency owns vertical expertise. The $97 → $240-$291/sub math lands well below the standalone price of Voice AI tools like [[phonely]] ($99/mo Pro) and far below [[birdeye]]'s hidden-pricing multi-location packages, giving GHL agencies meaningful price-leader room. This is the distribution moat: GHL is not winning on AI quality vs. Anthropic or OpenAI; it is winning on a wholesale→retail billing infrastructure that lets 10,000+ agencies layer the same AI on top of local relationships at prices the end-client cannot negotiate down to wholesale.

## Key Concepts

- **AI Employee** — GHL's billing bundle name for Voice AI, Conversation AI, Reviews AI, Funnel/Website AI, and Content AI. Not a single product; a rebilling construct.
- **Rebilling multiplier** — Agency-set markup on AI Employee wholesale cost, adjustable per sub-account from 1x to ~5x. Default example is 2.5x.
- **Unlimited plan per sub-account** — Flat $97/mo per sub-account covering the AI Employee bundle with no per-action caps (except Voice AI, which remains usage-based).
- **SaaS Mode** — Agency Pro ($497/mo) feature enabling automated client billing via the agency's Stripe account, required for true AI Employee reselling.
- **Scope drift** — GHL quietly moving features in/out of the AI Employee bundle. Some AI features are now free-use; agencies must verify what still belongs to AI Employee before marketing it to clients.

## Related Articles

- [[gohighlevel]] — Parent platform profile with plan tiers, feature surface, and widget positioning.
- [[ghl-pricing-teardown-2026]] — Full cost breakdown including AI Employee in the context of all usage fees; explains where AI Employee sits against the $97/$297/$497 base plans.
- [[ghl-april-2026-product-updates]] — April 2026 release notes, including Workflow AI Builder and Ask AI, that sit adjacent to the AI Employee bundle but aren't always inside it.
- [[ghl-carrier-pricing-april-2026]] — Telecom rate increases compressing the rebillable margin alongside AI Employee scope drift.
- [[ghl-lead-recovery-system]] — How AI Employee is positioned as the engine behind GHL's "system is the strategy" frame.
- [[phonely]] — Direct Voice AI competitor at $99/mo Pro; serves as the price ceiling GHL agencies underprice against.
- [[birdeye-agentic-marketing-platform]] — Multi-location agentic competitor with hidden pricing, illustrating the alternative distribution model.

## Relevance to AgentNexLiFy

AI Employee is the single strongest reason AgentNexLiFy should treat distribution — not AI quality — as the primary competitive axis against GoHighLevel. GHL agencies aren't buying on model performance; they are buying on a reseller billing rail that turns $97 wholesale into $200-$600 retail per sub-account. AgentNexLiFy cannot match this through the widget-first direct-to-SMB channel alone, which means the realistic plays are (1) build explicit agency/reseller tooling including per-client white-label, markup sliders, and Stripe Connect billing; (2) position vertical depth (salon KB, plumber KB, dental KB) as the moat agencies can't quickly replicate in GHL; or (3) stay direct-to-SMB and compete on lower total monthly cost (`agent_os` $99.99/mo vs. $297 GHL Unlimited + $97 AI Employee + usage fees = ~$412+/mo in Scenario 2 of the pricing teardown). The scope-drift pattern is also a warning: customers pay for bundles today that the vendor can quietly narrow tomorrow. AgentNexLiFy's plan feature list should be versioned and its scope guarantees written explicitly into the terms so AgentNexLiFy does not train customers to expect the same silent narrowing.
