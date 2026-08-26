---
title: "Claude Managed Agents Pricing — The $0.08 Session-Hour on Top of Token Cost (2026)"
category: ai-llm
tags: [anthropic, managed-agents, pricing, session-hours, claude-opus-5, cost]
sources: ["raw/ai-llm/claude-managed-agents-pricing-2026.md"]
created: 2026-08-25
updated: 2026-08-25
summary: "Managed Agents bills standard token rates plus $0.08 per active session-hour; idle time is free, a one-hour Opus 5 coding session lands at $0.705, and several API discounts do not carry over."
---

Anthropic's Managed Agents bills on two components: the standard per-model token rates, plus **$0.08 per active session-hour**. TrueFoundry's August 2026 breakdown works the second component out in practice — it applies only while a session is in the `running` state, so idle time between turns costs nothing. That single detail is what separates the pricing from a rented-VM model and makes bursty agent workloads cheap relative to their wall-clock duration. The infrastructure Managed Agents wraps is described in [[anthropic-managed-agents-architecture]]; this article covers what it costs.

Per-model token rates are unchanged from the standard API. Opus 5 runs $5 per million input and $25 per million output, with 5-minute cache writes at $6.25 and cache reads at $0.50. Haiku 4.5 is $1/$5 with $1.25 writes and $0.10 reads. Sonnet 5 carries a dated change: $2/$10 through August 31 2026 with $2.50 writes and $0.20 reads, rising to $3/$15 with $3.75 writes and $0.30 reads from September 1 2026. Any cost model built before that date and still in use after it is understating Sonnet spend by 50%. The full standard-API rate card sits in [[claude-api-pricing-breakdown-2026]].

The worked example clarifies the ratio. A one-hour Opus 5 coding session consuming 50,000 input tokens and producing 15,000 output tokens costs $0.25 for input, $0.375 for output, and $0.08 for runtime — **$0.705 total**. Runtime is 11% of the bill. Token spend dominates at single-session scale, which means the session fee is not the thing to optimize first; the cache-hit rate and the output budget are. At multi-agent scale the arithmetic shifts: a fleet running hundreds of concurrent long-lived sessions accumulates $0.08 charges independently of how much thinking each one does.

What the session fee already covers matters as much as the fee itself. Idle time is free, and code execution is folded into session runtime rather than billed separately — an agent that spends most of its hour running tools rather than generating tokens is not charged extra for the sandbox. What does **not** carry over is the discount surface: the Batch API's 50% reduction, fast-mode multipliers, data-residency discounts, and web search at $10 per 1,000 searches all sit outside the Managed Agents billing model. A workload that leaned on Batch pricing on the raw API loses that lever entirely when it moves.

TrueFoundry's comparison against self-hosted orchestration is vendor-framed but the axes are real. Framework cost is included versus open-source with no license fee. Runtime is $0.08 per session-hour versus none. Model access is Claude-only versus 1,000+ LLMs through a gateway. Hosting is Anthropic-managed US cloud versus self-hosted, on-prem, or managed SaaS. Governance is per-tool permission policies versus centralized model-level RBAC and budgets. Observability is server-side event history versus OpenTelemetry export to Grafana or Datadog. The conclusion follows from the axes rather than the pricing: large multi-model deployments avoid per-session fees by self-hosting, and single-model Claude deployments generally do not clear the operational bar to justify it.

The practical takeaways are three. Token spend dominates any individual session, so optimize prompt caching before worrying about runtime — the mechanics of that are in [[prompt-caching-production-savings-2026]]. Session runtime becomes material only at multi-agent scale, where concurrency multiplies the $0.08. And several API discounts simply do not exist here, so a migration cost model must be rebuilt rather than adjusted. An independent read of the same pricing structure is in [[anthropic-managed-agents-pricing-finout-2026]].

## Key Concepts

- **Session-hour** — the billing unit for Managed Agents runtime, $0.08 per hour, accrued only while the session is in the `running` state.
- **Idle time** — the period between turns when a session exists but is not executing. Charged at zero, which is what makes long-lived low-activity agents viable.
- **Two-component billing** — the total is per-model token charges plus session-hour runtime. Neither substitutes for the other.
- **Included code execution** — sandboxed tool and code execution is folded into session runtime rather than metered separately.
- **Non-transferring discounts** — Batch API 50%, fast-mode multipliers, and data-residency discounts apply to the raw Messages API and not to Managed Agents.
- **Sonnet 5 price step** — $2/$10 through 2026-08-31, $3/$15 from 2026-09-01. A dated change, not a tier change.

## Related Articles

- [[anthropic-managed-agents-architecture]] — what the runtime actually provides for the session fee
- [[anthropic-managed-agents-pricing-finout-2026]] — a second independent pricing analysis
- [[anthropic-managed-agents-cowork-ga-april-2026]] — GA timeline and product surface
- [[claude-api-pricing-breakdown-2026]] — standard per-model API rates
- [[prompt-caching-production-savings-2026]] — the lever that moves the dominant cost component
- [[claude-opus-4-7-tokenizer-cost-reality-2026]] — why token counts drifted upward across model generations

## Relevance to AgentNexLiFy

We already run Managed Agents in production — the Lead Qualifier is live on the platform — so this rate card is a direct input, not competitive research. Three concrete uses.

Budget sizing: `.claude/rules/task-budgets.md` documents `DEFAULT_SESSION_BUDGET_CENTS = 500` ($5) on every script-launched session. At $0.705 for a one-hour Opus 5 session, that ceiling permits roughly seven such sessions before the budget goes idle — worth checking against actual nightly-loop duration rather than assuming headroom.

Model selection: the Sonnet 5 step to $3/$15 on 2026-09-01 lands within days of this writing. Any per-tenant cost model or `PLAN_BASELINE_TOKENS` calibration built on the $2/$10 rate needs recomputing before September.

Architecture: because idle time is free and code execution is included, keeping a session alive across a multi-step tenant workflow costs nothing extra versus tearing it down and re-establishing context. That argues for longer-lived sessions with better cache retention rather than short ones, and it inverts the instinct carried over from VM-billed infrastructure.
