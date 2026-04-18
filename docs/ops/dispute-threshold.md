# Stripe Dispute-Rate Pause Threshold

**Set:** 2026-04-17
**Owner:** Aidan + partners (joint)
**Review cadence:** monthly until 100 paid customers, then quarterly

## The number

**Pause new paid signups if rolling-30-day dispute rate reaches 0.50%.**

- **0.50%** → pause all new paid signups (keep existing customers on)
- **0.65%** → pause + personally call every open dispute to try to resolve before Stripe decides
- **0.75%** → Stripe's own threshold for review / account flag — at this point assume account is in danger

## Why 0.50% (half of Stripe's threshold)

Stripe's hard threshold is 0.75%. If we hit 0.75%, Stripe reviews us. The pause must fire **before** Stripe notices, not when they're already looking. Half of their threshold gives us margin to investigate + fix before reputation damage.

Industry context (per Stripe docs + public SaaS ops writing):
- Healthy SMB-SaaS dispute rate: **0.1% – 0.3%**
- Warning zone: **0.3% – 0.5%**
- Danger zone: **0.5% – 0.75%**
- Stripe review: **≥ 0.75%**

## How the dispute rate is calculated

`(disputes opened in last 30 days) / (successful charges in last 30 days) × 100`

**Source of truth:** Stripe Dashboard → Disputes → "Dispute rate" metric. Check weekly until we have ≥ 100 monthly charges; daily after that.

## Cold-start rule (small numbers)

At low volume, one dispute can blow past the threshold mathematically:
- 1 dispute / 10 charges = 10%
- 1 dispute / 50 charges = 2%

**Until we have 100+ successful charges in a rolling 30-day window:**
- **ANY dispute** → pause new signups for 72h + root-cause it
- Treat cold-start disputes as acceptance tests on the refund/cancel flow, not statistics

## Who does what on trigger

| Threshold | Action | Owner |
|---|---|---|
| 0.30% (warn) | Slack alert to #ops channel; review all last-30d disputes in a 30-min call | Aidan |
| 0.50% (pause) | Disable Stripe checkout via `settings.stripe_enabled=false` env flag; landing page shows "waitlist only"; existing customers unaffected | Aidan or partner with Railway access |
| 0.65% (escalate) | Call every open dispute personally; offer full refund + email apology; document every outcome | Partner lead |
| 0.75% (danger) | Assume Stripe is reviewing the account. Do NOT take any new revenue. Contact Stripe support proactively + prepare documentation | Aidan + partner |

## Implementation checklist (to do)

- [ ] **Monitoring:** nightly cron hits Stripe API, calculates 30d dispute rate, writes to `ops_metrics` table + Slack `#ops` if >0.30%
- [ ] **Kill switch:** env var `STRIPE_NEW_SIGNUPS_PAUSED=true` that makes `/api/v1/auth/billing/checkout` return 503 with user-facing waitlist CTA
- [ ] **Partner access:** partner lead has Railway login + permission to set env vars
- [x] **Runbook:** linked from `docs/ops/partner-runbook.md` (created 2026-04-18)

## When to re-negotiate the threshold

Raise the pause threshold toward 0.60% **only after** all 4 are true:
1. 500+ successful charges in a rolling 30-day window
2. Refund endpoint shipped + tested (rubric 3.6 closes)
3. Dunning flow shipped + tested (rubric 3.2 closes)
4. Cancel-reason captured (rubric 10.3 closes)

Until all 4 are true, 0.50% holds. Non-negotiable.

## What counts as a "dispute" here

Include:
- Chargeback (customer disputes with their bank)
- Stripe-initiated inquiry that becomes a dispute
- Unauthorized / fraudulent charge filed via Stripe

Exclude:
- Duplicate-charge refunds we process ourselves (those are refunds, not disputes)
- Pre-auth failures (not charges)
- Customer-initiated refunds before dispute window opens (pay them, move on)

## History

- **2026-04-17** — Threshold set at 0.50% (initial). Cold-start rule active until 100+ monthly charges.
