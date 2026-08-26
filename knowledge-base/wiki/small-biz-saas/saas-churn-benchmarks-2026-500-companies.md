---
title: "SaaS Churn Benchmarks 2026 — Artisan Growth's 500-Company Study: Segment Rates, NRR, Leading Indicators, and Dunning Recovery"
category: small-biz-saas
tags: ["churn", "benchmarks", "nrr", "smb-saas", "involuntary-churn", "dunning", "onboarding", "ltv", "leading-indicators", "cohort-reporting"]
sources: ["raw/small-biz-saas/saas-churn-benchmarks-2026-500-companies.md"]
created: 2026-08-26
updated: 2026-08-26
summary: "Artisan Growth's April 2026 study of 500+ B2B SaaS companies ($500k–$20M ARR) puts SMB self-serve churn at 3.5–5.0% monthly with sub-3% as top quartile, shows ~40% of churn landing in the first 90 days, names involuntary churn as 20–40% of SMB loss recoverable at 50–70% with combined dunning, and quantifies the single-feature (~3x) and single-user (~2x) risk multipliers that decide which accounts to intervene on."
relevance_score: 8
---

> ⚠️ Some sources are over 60 days old. Run /kb-health to check for updates.

# SaaS Churn Benchmarks 2026 — Artisan Growth's 500-Company Study: Segment Rates, NRR, Leading Indicators, and Dunning Recovery

Artisan Growth Strategies published its 2026 churn benchmark on 8 April 2026, drawing on self-reported medians from more than 500 B2B SaaS companies between $500k and $20M ARR, covering 2025 through the first quarter of 2026. Where the wiki's other churn sources — [[churnfree-b2b-saas-churn-benchmarks-2026]], [[saas-churn-benchmarks-2026]], and the segment-spike analysis in [[saas-churn-benchmarks-by-segment-2026-spike]] — establish the headline rates, this study is the most operational of the set: it attaches specific intervention lift percentages, dunning recovery rates, and risk multipliers to each benchmark, which makes it usable as a retention playbook rather than a scoreboard.

## Churn by segment

The study segments by contract value, and the segments map cleanly onto price points. SMB self-serve accounts under $1,200 per year churn at 3.5–5.0% monthly, or 35–50% annually. SMB sales-assisted accounts between $1,200 and $10,000 per year run 2.0–3.0% monthly, 22–30% annually. Mid-market lands at 0.8–1.5% monthly and enterprise at 0.4–0.8%. The study singles out the under-$100-per-month self-serve tier explicitly: 3.5–5% monthly is normal, and under 3% is top quartile. That framing matters because the common instinct is to treat 4% monthly as a crisis when it is the segment median.

Net revenue retention follows the same gradient. SMB self-serve medians sit at 88% NRR with top performers reaching 100% or better; sales-assisted SMB medians reach 95% with top quartile at 110%; mid-market 105% and 120%; enterprise 112% and 130%-plus. The gap between median and top quartile in the self-serve band — twelve points — is the whole difference between a shrinking installed base and a flat one, and the study's argument is that the gap is closed by expansion and involuntary-churn recovery, not by lowering voluntary churn alone.

## When churn happens

Roughly 40% of total churn occurs in the first 90 days after signup, and a further 22% in days 91–180, meaning nearly two-thirds of all churn is decided in the first six months. The strongest single predictor the study reports is time-to-first-value: accounts that reach a first meaningful outcome within seven days churn at about one-third the rate of accounts that take more than thirty days. This is the same finding [[userpilot-churn-strategies-2026]] reaches from the product-analytics side, and the two sources agree that onboarding is a retention lever with a larger effect size than any pricing or packaging change.

## Leading indicators and risk multipliers

The study names five behavioral signals that precede churn with enough lead time to act on. Two consecutive weeks with usage down more than 50% from the account's baseline. Zero logins for fourteen days. A negative support ticket left unresolved for more than 72 hours. A failed payment. And, as structural rather than behavioral indicators, two account shapes that carry multipliers: single-user accounts churn at roughly twice the rate of multi-user accounts, and single-feature accounts — those that use one capability and nothing else — churn at roughly three times the rate of accounts using two or more.

Involuntary churn, the failed-payment category, accounts for 20–40% of all SMB churn in the study. It is also the most recoverable. The reported recovery rates by tactic: automatic card updater 25–35% of failed payments recovered, smart dunning sequences 15–25%, pre-dunning notices sent before card expiry 10–15%, in-app payment banners 8–12%, and all tactics combined 50–70%. Since these overlap, the combined figure is the one to plan against; a product losing 4% monthly with 30% of that involuntary can recover roughly 0.6–0.8 points of monthly churn from billing hygiene alone.

## Intervention lift

The study attaches churn-reduction percentages to six interventions. Structured onboarding reduces churn 25–35%. Annual prepay reduces it 20–30%, partly by selection and partly by removing the monthly cancel decision. Proactive outreach triggered by the leading indicators above yields 15–20%. A second-user invite flow yields 12–18%, directly attacking the single-user multiplier. A monthly value recap email yields 8–15%. A cancel-flow save offer yields 10–20% of would-be cancellations. These are not additive — onboarding and outreach overlap heavily — but the ordering is informative: the two largest levers are both about the first 90 days.

## LTV arithmetic and reporting

The study's lifetime math is simple and worth memorizing. At 4% monthly churn, expected customer lifetime is 25 months; at 3%, it is 33 months, a 32% increase. Each percentage point of monthly churn removed is worth roughly 30% more lifetime value at these rates. The study also recommends reporting churn by signup cohort rather than as a blended monthly figure, because a blended number hides whether recent onboarding changes are working — a cohort table shows month-3 retention for the June signups next to the March signups and makes the effect of any intervention visible within one quarter.

## Key Concepts

- **Segment-normal churn** — SMB self-serve under $1,200/yr runs 3.5–5.0% monthly; under 3% is top quartile, so 4% is median, not failure.
- **First-90-day concentration** — ~40% of churn in days 0–90 and ~22% in days 91–180; two-thirds of churn is decided in the first six months.
- **Time-to-first-value** — first value within 7 days cuts churn to about one-third of the >30-day cohort.
- **Single-feature multiplier** — accounts using one capability churn ~3x; single-user accounts ~2x.
- **Involuntary churn** — failed payments are 20–40% of SMB churn and 50–70% recoverable with combined dunning tactics.
- **Cohort reporting** — churn by signup month, not blended, so onboarding changes show up within a quarter.
- **LTV per churn point** — 4% → 25 months, 3% → 33 months; each point is ~30% lifetime value.

## Related Articles

- [[saas-churn-benchmarks-by-segment-2026-spike]] — segment-level rates and the 2026 spike context.
- [[churnfree-b2b-saas-churn-benchmarks-2026]] — ChurnFree's parallel benchmark set for B2B SaaS.
- [[saas-churn-benchmarks-2026]] — the wiki's baseline churn benchmark article.
- [[userpilot-churn-strategies-2026]] — product-analytics view of onboarding and activation as retention levers.
- [[chartmogul-saas-retention-ai-churn-wave]] — retention data through the AI-driven churn wave.
- [[vantainsights-saas-churn-federal-baseline-2026]] — a contrasting baseline from a different sample.

## Relevance to AgentNexLiFy

Both paid plans sit on the study's segment boundaries. `chatbot` at $19.99/mo ($240/yr) is squarely in the under-$100-per-month self-serve band, where 3.5–5% monthly churn is the median and under 3% is the target. `agent_os` at $99.99/mo ($1,200/yr) sits exactly at the study's line between self-serve and sales-assisted; whether it behaves like a 4% or a 2.5% product depends on whether onboarding is guided, which argues for treating agent_os signups as sales-assisted with a scheduled setup call even though the checkout is self-serve.

The single-feature multiplier is the most pointed finding for the product. A `chatbot` tenant by definition uses one capability — the widget — and the study says that shape churns at roughly three times the rate of multi-feature accounts. That reframes the chatbot → agent_os upgrade path as a retention mechanism rather than only an upsell: the second feature adopted (missed-call text-back, appointment booking, automated follow-up per the ops-automation PRD) is what moves the tenant out of the 3x band. The dashboard should surface that second-feature activation as a first-class onboarding step, not a plan-gate.

Time-to-first-value maps to a concrete metric already in the schema: the interval between tenant creation and the first row in `leads` with that `client_id`. If the widget is installed and captures a lead within seven days, the study predicts one-third the churn; if the embed sits uninstalled for a month, it predicts the opposite. That interval should be the lead metric on the internal health view, and the "zero logins for fourteen days" and "usage down 50% for two weeks" signals translate directly to `conversations` volume per `client_id` week over week.

Involuntary churn is the cheapest fix on the list. Stripe's automatic card updater and Smart Retries cover the top two tactics (25–35% and 15–25% recovery) and are configuration, not code; the pre-dunning notice and in-app banner are a small automation on the existing `stripe_service.py` webhook path. At the study's 20–40% involuntary share, that alone is worth more than any cancel-flow save offer.
