# Positioning Intake — AgentNexLiFy (2026-04-23)

Input conditions for startup-positioning skill run. Uses April Dunford's 5+1 framework. Intake compressed from existing KB + CLAUDE.md + competitive audit.

## Company
**AgentNexLiFy** — multi-tenant AI business automation SaaS. Embeddable widget captures leads, books appointments, automates follow-ups.

## Stage
Operating with pricing published: free / growth $249 / autopilot $299 / professional $499 / enterprise $899. Feature-complete for core small-business operations per 2026-03 analysis.

## Product surface
- Chat widget (JS embed, byte-identical in `widget/` + `frontend/public/widget/`)
- Dashboard (React/Vite)
- Backend (FastAPI + Supabase, multi-tenant by `client_id`)
- AI layer (Anthropic Claude — Opus 4.7 / Sonnet 4.6 / Haiku 4.5)
- Per-tenant knowledge base in `widget/knowledge-bases/<tenant>_kb.md`

## Target buyer (ICP hypothesis)
Small-business owner / operator in a specific vertical (dental, legal, salon, med-spa, real estate, restaurant, auto shop, medical office), 1-3 locations, no in-house marketing team, no agency retainer, budget <$400/mo, wants a chat widget on existing site without CRM migration, values pricing transparency.

## What we believe uniquely about us (attribute list, pre-filter)
Candidates for "Unique Attributes" in Dunford frame:
1. Per-tenant vertical knowledge base
2. Widget-first product identity (vs widget-as-feature)
3. Transparent public pricing (4 tiers published)
4. Flat pricing (not per-location)
5. 30-second embed narrative (short install)
6. No CRM migration required
7. Direct-to-business (no agency middleman)
8. Free tier for trial / top-of-funnel
9. Byte-identical widget discipline (reliability moat)
10. Multi-tenant from day one
11. Self-serve onboarding (no CSM required)
12. KB compiled from raw sources per-customer (vertical depth)
13. Plan-named alignment (growth, autopilot, professional) maps to buyer progression
14. Works with Anthropic Claude — latest model alignment

We'll filter these through "true AND different AND valuable" gate in `positioning-doc.md`.

## Gut feel positioning (pre-framework)
> "The chat widget that actually knows your business — from the moment you install it — without the CRM migration."

This is a pre-synthesis candidate, not final. Framework pass refines.

## Market category — open question
Currently ambiguous. Candidates:
- "AI lead-capture widget"
- "Vertical AI chat for SMBs"
- "SMB AI business automation" (GHL adjacent — likely loses)
- "Widget-first CRM alternative"
- "Per-tenant AI assistant"

See `audits/positioning/market-category-analysis.md` for the decision.

## Competitive alternatives (what buyer compares us against)
From `audits/competitive/competitors-report.md`:
- **GoHighLevel** — horizontal agency stack
- **Podium** — widget-strong peer
- **Birdeye** — reviews-first with hidden pricing
- **Drillbit** — voice-first for trades
- **Intercom / Drift** — enterprise chat
- **Tidio / Crisp / LiveChat** — SMB chat at lower price
- **HubSpot** — full CRM
- **Status quo** — contact forms + manual email / phone follow-up (often the real alternative)

## Strategic finding carried in
From `knowledge-base/wiki/competitors/competitive-landscape-march-2026.md`:
> Gap is NOT breadth. Gap is engagement and stickiness.

Implication: positioning that makes the widget *feel* irreplaceable beats adding feature #47. "Per-tenant KB" is the engagement hook, not a feature column.

## Trend overlay (pre-framework)
- AI mainstreaming across SMB (2026 = "everyone has AI" year)
- FTC + state-level AI disclosure laws emerging
- Agency fatigue: SMBs tired of paying 3x markup on tools they don't control
- Google organic search decline → direct-traffic value rising → widget on existing site is higher-leverage
- Self-serve SaaS reemergence (post-PLG wave): buyers want to try, not demo

## Deliverables planned
1. `positioning-doc.md` — Dunford 5+1 with strength ratings
2. `positioning-statement.md` — Moore template, Neumeier Onliness, elevator pitch, taglines
3. `competitive-alternatives.md` — all alternatives including status quo
4. `market-category-analysis.md` — 3-5 candidate categories, decision
5. `messaging-implications.md` — words to use, words to avoid, home page / pricing page / ad map

## Source files consumed
- `audits/competitive/competitors-report.md`
- `audits/competitive/competitive-matrix.md`
- `audits/competitive/pricing-landscape.md`
- `audits/competitive/battle-cards/*.md`
- `knowledge-base/wiki/competitors/*.md`
- `CLAUDE.md`
