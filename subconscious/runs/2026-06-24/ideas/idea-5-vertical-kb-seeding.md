# Idea 5: Seed KB for 3 New Verticals (Roofing, Home Cleaning, Veterinary)

## Summary
#367 added 3 new verticals. Their widget knowledge bases likely contain only the generic template. Seed each with vertical-specific FAQs, common objections, and automation triggers to differentiate responses from generic LLM output.

## Evidence
- 852e8b0 (#367): vertical expansion 10→13 (roofing, home cleaning, veterinary)
- Our moat per CLAUDE.md: "vertical knowledge-base pattern per tenant, not generic LLM replies"
- KB auto-populate runs twice daily but can't generate vertical-specific content without a seed template
- Without seeding: widget gives generic AI answers indistinguishable from competitors (GoHighLevel, Drillbit)

## What "done" looks like
Three files in `widget/knowledge-bases/`:
- `roofing-vertical-template_kb.md`: storm damage FAQs, insurance claim process, free estimate flow, seasonal triggers
- `home-cleaning-vertical-template_kb.md`: service frequency, pricing structure, booking flow, recurring vs one-time
- `veterinary-vertical-template_kb.md`: appointment types (wellness vs sick), emergency vs routine, species-specific routing

Each KB: ~20 targeted Q&A pairs + 5 automation triggers (keywords → lead actions).

## Impact
Improves widget answer quality for all new tenants in these 3 verticals. Vertical differentiation = retention. Generic answers = churn.

## Effort
MEDIUM — content research + writing, no code changes. 3 KB files at ~150 lines each.

## Category
Customer experience / competitive differentiation
