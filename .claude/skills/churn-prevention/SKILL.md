---
name: churn-prevention
description: Retention patterns for SaaS cancel/downgrade/pause flows. Load when editing frontend/src/pages/BillingPage.jsx cancel UX, backend/services/stripe_service.py subscription ops, or designing win-back logic for free/growth/professional/autopilot/enterprise tiers.
origin: coreyhaines31/marketingskills (adapted)
version: 1.0.0
triggers:
  - churn prevention
  - cancel flow
  - retention offers
  - pause subscription
paths: frontend/src/pages/Billing*.jsx,backend/services/stripe_service.py,backend/routers/billing*.py
user-invocable: false
  - downgrade instead of cancel
  - win-back
---

# Churn Prevention — Retention Playbook

Retention playbook adapted for AgentNexLiFy plans: free, growth ($249), professional ($499), autopilot ($299), enterprise ($899).

## When to Use
- Editing `frontend/src/pages/BillingPage.jsx` cancel/downgrade UX
- Editing `backend/services/stripe_service.py` subscription state transitions
- Designing win-back email sequences or in-app offers
- Reviewing churn metrics before a pricing change

## When NOT to Use
- Fresh signup / onboarding flows (use `industry-content` or `email-sequence`)
- Pure billing bug-fixes with no retention logic change
- Tenant-facing marketing content (use `email-sequence` / `seo-audit-marketing`)

## Core offer patterns (use in order of reversibility)

1. **Pause-for-N-months** — preserve config + data, stop billing 1-3 months. Less churny than cancel, user returns without onboarding tax.
2. **Downgrade-instead-of-cancel** — step down one tier (professional → growth, growth → free). Keeps account active, preserves widget + tenant data.
3. **Discount-for-commit** — 30-50% off 3-6 months for commit to annual renewal. Margin hit now, LTV protection long term.
4. **Feature unlock** — surface addon (marketing addon, autopilot) they haven't used. Often cancel = "didn't see value" not "too expensive."
5. **Skip-a-month** — 30-day credit on next invoice. Cheapest retention offer.

## What to measure
- **Cancel reason** (required field): price, missing feature, low usage, tech issues, switched competitor, business closed
- **Days-since-last-login** at cancel — predictor of reversibility
- **Widget conversations in last 30d** — engagement proxy
- **MRR saved** via retention offer (pause/downgrade/discount breakdown)

## Our plan-specific playbook
| Plan | Primary offer | Fallback |
|------|---------------|----------|
| free → (nothing to retain) | email nurture sequence | – |
| growth ($249) | downgrade to free + re-engagement email | 30% off 3 months |
| professional ($499) | downgrade to growth + pause option | 20% off 3 months |
| autopilot ($299 addon) | pause-3-months | drop addon, keep base plan |
| enterprise ($899) | account manager call BEFORE offer | custom contract terms |

## Implementation hooks
- `frontend/src/pages/BillingPage.jsx` — cancel button opens retention modal (pause/downgrade/discount offers before confirming cancel)
- `backend/services/stripe_service.py` — `pause_subscription()`, `change_plan()`, `apply_promotion_code()` (Stripe Billing pause_collection + promotion_codes API)
- `migrations/NNN_churn_events.sql` — log `cancel_reason`, `retention_offer_shown`, `retention_offer_accepted`
- Webhook: `customer.subscription.paused` + `customer.subscription.updated` → update local state

## Anti-patterns
- Don't gate cancel behind contact form (illegal in some jurisdictions; bad UX)
- Don't use dark patterns (fake urgency, hidden close buttons)
- Don't offer discounts on first ask — save for 2nd touch (they're already committed to cancel)
- Don't pause enterprise without CSM-approved SLA

## Metrics dashboard
- Retention rate by offer type (pause / downgrade / discount / none)
- Reactivation rate at 30/60/90 days for paused accounts
- Win-back cost per saved account ($ discount / MRR recovered)

## Full upstream reference
coreyhaines31/marketingskills — churn-prevention SKILL. Install full version:
```
npx skillsadd coreyhaines31/marketingskills
```
