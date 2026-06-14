# Competitive Intake — AgentNexLiFy (2026-04-23)

Input conditions for startup-competitors skill run. Intake compressed from existing KB + CLAUDE.md instead of fresh interview.

## Product
**AgentNexLiFy** — AI-powered business automation. Embeddable chat widget captures leads, books appointments, automates follow-ups. Multi-tenant SaaS from day one.

## Target customer (ICP)
Small-business owners in: salon, dental, contractor, legal, real estate, restaurant, auto shop, medical office. 1-3 locations. No in-house marketing team. No agency retainer. Wants widget on existing site without CRM migration.

## Core value proposition (hypothesized)
Widget-first AI capture + vertical knowledge base per tenant. 30-second embed. No agency call required.

## Plan ladder (pricing)
| Plan | Price | Target |
|---|---|---|
| free | $0 | trial / single-user |
| growth | $249/mo | single-location SMB |
| autopilot | $299/mo | automation-heavy SMB |
| professional | $499/mo | multi-location SMB |
| enterprise | $899/mo | multi-location / custom |

## Competitive set (confirmed from KB)
Direct widget-first or widget-adjacent:
- **GoHighLevel** ($97-497/mo) — horizontal agency platform; widget buried in CRM
- **Drillbit** ($500/mo/location) — YC vertical play; voice-first for trades contractors; no widget
- **Birdeye** (~$300-600/mo est) — reviews-first; chatbot gated to top tier; hidden pricing
- **Podium** ($399-599/mo) — closest widget peer; transparent pricing; CSM-onboarded

Adjacent / contextual:
- **Intercom / Drift** — enterprise chat ($300+/mo)
- **Tidio / Crisp / LiveChat** — SMB chat ($20-80/mo); light automation
- **HubSpot** — full CRM ($45-800/mo); custom fields strong
- **Phonely / Toma** — voice-first AI receptionist

## Gut feelings (pre-analysis)
- GHL's reseller moat locks agencies, not end-businesses → clean lane for direct SMB
- Podium is the hardest direct fight because widget is real + priced on page
- Birdeye's hidden pricing + top-tier gating is an open wedge
- Drillbit doesn't compete in dental/legal/salon — safe flank

## Known strategic finding (KB: competitive-landscape-march-2026)
> AgentNexLiFy is feature-complete for small-business operations. Gap is NOT breadth. Gap is engagement + stickiness.

Implication: positioning > feature-add as the next moat. Hence this audit.

## Scope decisions for this audit
- **In scope:** GHL, Drillbit, Birdeye, Podium (battle cards for these 4)
- **Out of scope:** Tidio/Crisp/LiveChat (wrong price band), Intercom/Drift (wrong segment), Phonely/Toma (voice-first, different product shape)
- **Research mode:** Skip fresh web research waves — KB data from 2026-04-18 is current enough for synthesis

## Source files consumed
- `knowledge-base/wiki/competitors/gohighlevel.md`
- `knowledge-base/wiki/competitors/drillbit.md`
- `knowledge-base/wiki/competitors/birdeye.md`
- `knowledge-base/wiki/competitors/podium.md`
- `knowledge-base/wiki/competitors/competitive-landscape-march-2026.md`
- `CLAUDE.md` (plan pricing, architecture)

## Deliverables planned
1. `competitors-report.md` — executive summary
2. `competitive-matrix.md` — feature table
3. `pricing-landscape.md` — tier + psychology analysis
4. `battle-cards/{gohighlevel,drillbit,birdeye,podium}.md`
