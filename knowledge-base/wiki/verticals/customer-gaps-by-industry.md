---
title: "Customer Gaps by Industry — Consolidated"
category: verticals
tags: ["salon", "plumber", "dental", "restaurant", "fitness", "lawyer", "real-estate", "product-market-fit", "gaps"]
sources: ["raw/verticals/customer-gaps-consolidated.md"]
created: 2026-04-04
updated: 2026-04-04
summary: "Product-market fit scores across 7 verticals (Salon 9/10 to Real Estate 6/10) with 15 resolved gaps and prioritized cross-industry open gaps."
---

> ⚠️ Some sources are over 60 days old. Run /kb-health to check for updates.

# Customer Gaps by Industry — Consolidated

Findings from customer simulations across 7 industries. 15 gaps have been resolved through the build loop; remaining gaps are prioritized by cross-industry impact.

## Product-Market Fit Scores

| Industry | Fit Score | Key Strength | Missing Piece |
|----------|-----------|--------------|---------------|
| Salon/Spa | 9/10 | Service types + rebook + reminders | Waitlist |
| Plumber/HVAC | 8/10 | Emergency detection + bids + invoices | Before/after photos |
| Dental | 8/10 | Intake forms + insurance + HIPAA AI | Provider scheduling |
| Restaurant | 8/10 | Menu + orders + chat ordering | POS integration |
| Fitness | 7/10 | Waiver form + rebook + pipeline | Class scheduling |
| Lawyer | 7/10 | Intake forms + documents + pipeline | Billable hours |
| Real Estate | 6/10 | Pipeline + documents | Property tracking |

## Cross-Industry Open Gaps (High Priority)

These affect ALL verticals and should be prioritized:

1. **AI-to-human handoff** — Critical for complex queries that the AI can't resolve. Medium effort.
2. **Lead source analytics** — The `source` column exists on leads but there's no dashboard visualization. Low effort.
3. **Custom automation templates** — Custom birthday messages, post-service follow-ups per industry. Medium effort.

## Industry-Specific Open Gaps

### Real Estate (Fit: 6/10 — most gaps)
- Buyer qualification AI (budget, pre-approval) — High impact, Medium effort
- Property-level tracking in appointments — High impact, High effort
- Post-showing follow-up template — Medium impact, Low effort
- MLS integration — Low impact, Very High effort (external API)

### Dental / Medical
- Provider-specific availability — Medium impact, High effort
- Post-appointment care instructions — Medium impact, Low effort
- Treatment plan tracking — Medium impact, High effort

### Salon
- Waitlist for fully booked days — Medium impact, Medium effort
- Before/after photo gallery — Low impact, Medium effort
- Tipping integration — Low impact, Medium effort

### Lawyer
- Conflict check (opposing party lookup) — High impact, Medium effort
- Billable hours tracking — Medium impact, High effort
- Retainer balance tracking — Medium impact, Medium effort
- Matter/case number generation — Low impact, Low effort

### Fitness
- Class schedule integration — Medium impact, High effort
- Member retention tracking (30-day inactive alert) — Medium impact, Medium effort
- Trial-to-member conversion tracking — Medium impact, Low effort

### Restaurant
- Table/reservation management — Medium impact, High effort
- Post-dining aftercare ("Thank you, leave a review") — Low impact, Low effort
- POS integration — Low impact, Very High effort (external API)

## Resolved Gaps (15 total)

All resolved via the autonomous build loop (Cycles 107-132):
Emergency/urgency detection, business hours in onboarding, service type booking, dental-aware reminders, rebook automation (42-180 day), patient intake form preset, HIPAA-aware AI, insurance fields on leads, industry pipeline presets, webhook schema, lead source tracking, AI conversation summary, birthday automation, legal intake form preset, FAQ consistency (≥5 per type).

## Key Concepts

- **Product-market fit score** — 10-point heuristic weighing feature coverage vs vertical's core workflow; 8+ = ready to sell, <7 = needs work.
- **Cross-industry gap** — missing capability that affects ≥3 verticals; prioritized over industry-specific gaps.
- **Resolved gap** — previously-open capability closed through the autonomous build loop (Cycles 107-132).
- **Strongest vertical** — Salon/Spa (9/10) and Plumber/HVAC (8/10) are primary GTM targets.

## Related Articles

- [[competitive-landscape-march-2026]] — competitor-driven feature priorities.
- [[post-launch-growth-strategy]] — 10 growth features that sit atop these gaps.
- [[gohighlevel]] — horizontal competitor reviewed missing QuickBooks sync + vertical depth.

## Relevance to AgentNexLiFy

**Salon/Spa and Plumber/HVAC are the strongest verticals** (8-9/10 fit) and should be the primary go-to-market targets. Real estate (6/10) needs the most work — property tracking and buyer qualification are significant gaps. The 3 cross-industry gaps (AI-to-human handoff, lead source analytics, custom automation templates) should be prioritized over industry-specific gaps since they benefit all customers. See also [[competitive-landscape-march-2026]] for feature priorities from the competitor angle.
