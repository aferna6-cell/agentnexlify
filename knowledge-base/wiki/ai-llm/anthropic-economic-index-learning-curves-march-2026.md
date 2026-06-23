---
title: "Anthropic Economic Index March 2026: tenure drives 10% higher Claude success rate"
category: ai-llm
tags: [anthropic, economic-index, learning-curves, opus-4-6, model-selection, onet, primitives, augmentation]
sources:
  - url: https://www.anthropic.com/research/economic-index-march-2026-report
    title: "Anthropic Economic Index report: Learning curves"
    fetched: 2026-05-05
created: 2026-05-05
updated: 2026-05-05
summary: "Feb 5-12 2026 sample shows 6+ month tenure users have a 10% higher conversation success rate after task fixed effects, Opus skews to higher-wage tasks, and Claude.ai task concentration fell from 24% to 19%."
---

The third Anthropic Economic Index report covers Claude usage February 5-12 2026, three months after Opus 4.5 and coincident with Opus 4.6. Two findings drive the report. First, learning-by-doing: users with 6+ months tenure on Claude have a 10% higher success rate in their conversations, dropping to 3-4 percentage points after fixed effects for O*NET task and request cluster — meaning the gap is not just task selection. Second, model selection follows wages: paying Claude.ai users pick Opus for 55% of Computer and Mathematical tasks vs 45% for Educational tasks, and the slope on the API is roughly 2x stronger than on Claude.ai. See [[anthropic-economic-index-feb-2026]] for the prior report and [[anthropic-economic-primitives-2026]] for the primitives framework.

Claude.ai usage diversified between November 2025 and February 2026. Top 10 O*NET tasks fell from 24% to 19% of conversations. Coursework dropped from 19% to 12%, partially explained by winter academic calendars. Personal use rose from 35% to 42%. Coding migrated out of Claude.ai into the API as Claude Code adoption grew — coding's share of Computer/Mathematical tasks rose 14% on the API and fell 18% on Claude.ai since August 2025. Average task value on Claude.ai dropped from $49.30 to $47.90/hr (BLS OEWS wage anchor) due to simple-factual queries (sports, weather) becoming a larger share.

Two emerging API automation patterns at least doubled in three months: business sales and outreach automation (sales enablement, B2B lead qualification, customer data enrichment, cold-email drafting) and automated trading and market ops (market monitoring, position tracking, broker condition alerts). Both are directive workflows with less human in the loop. Customer Service Representatives previously flagged as the highest exposure occupation continues to track because automated billing and payment workflows are frequent in API traffic. Augmentation rose slightly on Claude.ai (driven by validation and learning patterns) and automation fell sharply on the API in the same period.

Tenure analysis is the most actionable finding. High-tenure users (6+ months since signup) are 7 percentage points more likely to use Claude for work, run higher-education tasks, iterate more, and delegate less through directive patterns. The 10% raw success-rate gap survives task-level controls at 3-4 points, then rises to 4 points with full controls (model, language, country, use case). The interpretation Anthropic favors: learning-by-doing rather than cohort effects or survivorship bias. Caveats: early adopters skew technical, and we don't observe people who churned. Years of schooling required for the prompt rises about 1 year for each additional year of Claude tenure, while personal use share falls from 44% (newest users) to 38% (1-year users).

Geographic convergence within the US continued but slowed: top-five-state share fell from 30% to 24% since August 2025, but extrapolated convergence horizon stretched from 2-5 years to 5-9 years. Cross-country usage diverged — top 20 countries went from 45% to 48% of per-capita usage. Skill-biased technological change is the policy framing: early adopters with high-skill tasks have more successful Claude conversations, the same group most exposed to AI-driven disruption is also the most aided by it.

## Key Concepts

- **Learning-by-doing on Claude** — 6+ month tenure users have a 3-4 percentage point higher success rate within the same O*NET task cluster, suggesting skill at AI use accumulates with experience
- **Wage-calibrated model selection** — Opus share rises 1.5pp per $10/hr task wage on Claude.ai and 2.8pp on the API; users match model class to task complexity
- **Augmentation vs automation** — five interaction types (directive, feedback loop, task iteration, validation, learning) grouped into automation (directive) and augmentation (collaborative); augmentation rose on Claude.ai
- **Task value** — average hourly wage paid to US workers performing an O*NET task, sourced from May 2024 BLS OEWS, used as a proxy for the economic value of work being done on Claude
- **Task concentration** — share of conversations covered by the top 10 O*NET tasks, a proxy for usage diversification; fell from 24% to 19% on Claude.ai
- **Skill-biased technological change** — innovations that raise wages for high-skill workers while compressing them for others; the report identifies AI usage success as one such channel

## Related Articles

- [[anthropic-economic-index-feb-2026]] — November 2025 sample (the prior report)
- [[anthropic-economic-primitives-2026]] — primitives framework introduced earlier
- [[claude-opus-4-6]] — model release coincident with this sample
- [[anthropic-managed-agents]] — automation pattern context
- [[claude-code-ecosystem-snapshot-2026]] — Claude Code adoption context for the API migration finding

## Relevance to AgentNexLiFy

The "tenure drives success" finding maps directly to AgentNexLiFy's onboarding strategy. Tenants who run the widget for 6 months get measurably better outcomes — not because the model improves, but because the operator learns to feed it better context. That is an argument for stronger tenant-side coaching during the first 90 days and against assuming usage value is constant. The two emerging API automation patterns (B2B lead qualification and customer data enrichment) overlap directly with AgentNexLiFy's lead-qualifier agent and the planned ops automations — Anthropic's data confirms this is where API spend is doubling. Wage-calibrated model selection validates the model-routing rule: Opus for plan, Sonnet for execute, Haiku for mechanical work. Cost per $10 task value increase scales, so the right model for a $40/hr ops task is Sonnet, not Opus. Use the report's task-value framing in tenant pricing conversations: the `agent_os` plan ($99.99/mo; pricing updated 2026-06-15) paying for hundreds of $40-$60/hr tasks is the value anchor.
