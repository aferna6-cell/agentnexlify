---
type: map
name: "Product Map"
tags:
  - map
  - moc
last_updated: 2026-07-01
---

# Product Map

How [[AgentNexLiFy]] fits together.

## Surfaces
- [[Chat Widget]] (embed on tenant sites) → FastAPI → Claude → Supabase.
- [[Dashboard]] (`app.agentnexlify.com`) → FastAPI → Supabase.
- [[Agent OS]] (conversational layer) → runs in [[Agent Service]].

## Intelligence
- [[Claude Managed Agents]] (8 agents) · [[Advisor-Executor Pattern]] · [[Claude Model Routing]].
- [[Drafts-Only Approval Loop]] is the trust boundary.

## Strategy
- [[Vertical Packs]] on one engine · [[Vertical Knowledge-Base Moat]] — **13 verticals live in prod**
  (salon, plumber/HVAC, dental, med-spa, auto, real-estate, law, restaurant, fitness, roofing,
  cleaning, veterinary + generic); KB retrieval wired into the live widget (FTS + optional
  embeddings, `widget_chat.py:861`). · [[Compound Operating System]].
- Referral channel live end-to-end (2026-06-23): widget watermark `?ref=` → click tracking →
  signup attribution (migration 159) → referrer notification email → tenant + admin dashboards.
  Incentive/credit program = open owner decision.
- Per-vertical SEO landing pages: 12 `/ai-front-desk/*` URLs, public since domain connect.
- Field: [[Competitive Landscape]] (vs [[GoHighLevel]]).

## Infra
- [[Vendor Stack]] · Supabase org [[VoltOps]] · [[Multi-Tenant Architecture]].

## Money
- Plans per [[2026-06-15 Plan Repricing]]; launch status in [[Paid Launch Readiness]].

## Related
- [[Home]] · [[Decision Log]] · [[Open Loops]]
