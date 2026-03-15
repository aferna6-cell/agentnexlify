# Customer Simulation Summary — 2026-03-15

Three business types simulated: Plumber, Restaurant, Real Estate Agent.

## Cross-Industry Gaps (Affect ALL Business Types)

| # | Gap | Severity | Fix Effort |
|---|-----|----------|------------|
| 1 | **No holiday/special hours override** | High | Low — add exception_dates JSONB to business_hours |
| 2 | **Lead scoring is a black box** | Medium | Low — show scoring factors in LeadDetailDrawer |
| 3 | **lead_temperature never populated** | Medium | Low — calculate from lead_score (hot/warm/cold) |
| 4 | **No default automations on signup** | Medium | Medium — auto-create welcome + follow-up sequences |
| 5 | **Feature discovery missing in onboarding** | Medium | Low — highlight key features in onboarding checklist |

## Plumber-Specific Gaps

| Gap | Impact | Notes |
|-----|--------|-------|
| Team can view but not respond to chats | High | Shared inbox exists but needs better team notification |
| Bid/quote flow missing email collection | Medium | AI should ask for email when collecting quote details |

## Restaurant-Specific Gaps

| Gap | Impact | Notes |
|-----|--------|-------|
| No table/reservation management | High | Appointment system not suitable for restaurants — party size, covers needed |
| No customer order confirmation SMS | High | Customer gets nothing after ordering — trust issue |
| No menu modifiers (customization) | Medium | modifiers_json exists but unused in chat flow |
| No holiday hours | High | Can't close for Thanksgiving |

## Real Estate-Specific Gaps

| Gap | Impact | Notes |
|-----|--------|-------|
| No property tracking | Critical | Can't record which properties leads saw |
| No showing workflow | Critical | Appointments are generic, not property-specific |
| Lead qualification wrong for RE | High | Missing budget/timeline/pre-approval questions |
| No MLS integration | Critical | Would need external API — out of scope for now |

## Strengths (Confirmed Across All Simulations)

- Lead capture from chat is natural and effective
- AI auto-tagging from conversations is valuable
- Team member assignment works well
- Email/SMS automation sequences are powerful
- Widget customization is straightforward
- Business hours awareness in AI is helpful
- Multi-language support works automatically

## Verdict by Business Type

| Business Type | Score | Would They Stay? |
|---------------|-------|-----------------|
| **Service businesses** (plumber, HVAC, cleaning) | 7/10 | Yes — strong fit |
| **Restaurants** (takeout/delivery) | 6/10 | Probably — good for orders |
| **Restaurants** (dine-in) | 4/10 | No — needs table management |
| **Real estate** | 4/10 | Lead capture only — missing core RE features |
| **Dental/medical** | 7/10 | Yes — booking + reminders is perfect |
| **Legal** | 6/10 | Yes — lead qualification + follow-up |

## Priority Fixes (Build Next)

1. Holiday hours override (affects all)
2. Customer order confirmation SMS (restaurants)
3. Lead score explanation in UI (all)
4. lead_temperature auto-calculation (all)
5. Default automation sequences on signup (all)
