# Referral Incentive — Launch Runbook (2026-08-25)

The reward system is FULLY BUILT and live in prod code, gated OFF. This runbook
records the six program decisions (previously open in
`specs/referral-incentive_spec.md` §6) as launch defaults, and the single step
that turns the program on. Owner can change any default by editing
`backend/services/referral_reward.py` before flipping the switch.

## The six decisions — launch defaults

| # | Decision | Default | Where it lives |
|---|---|---|---|
| 1 | Reward amount | **$20 flat** | `REFERRAL_REWARD_CENTS = 2000` (`referral_reward.py:38`) |
| 2 | One- or two-sided | **One-sided (referrer only)** | grant path only credits the referrer |
| 3 | Trigger point | **Referee's FIRST paid invoice** | fires from `checkout.session.completed` after activation (`billing.py`) |
| 4 | Monthly cap | **None at current volume** — revisit before ~50 tenants; the `referral_rewards` table gives the per-referrer counts an audit needs | table query, no code cap |
| 5 | Mechanic | **Stripe customer balance credit** (auto-deducts from next invoice) | `stripe.Customer.create_balance_transaction(amount=-2000)` |
| 6 | Retroactive | **No** — only activations after enable; the UNIQUE(referred_tenant_id) row prevents double grants either way | webhook-driven, no backfill job |

Why these defaults: $20 ≈ one month of `chatbot` — meaningful, self-funding
after the referee's first `agent_os` month; one-sided keeps fraud surface
minimal; first-paid-invoice defeats signup-farming; balance credit needs no
coupon plumbing and shows up on the referrer's next invoice automatically.

## Safety properties already in code

- Idempotent: UNIQUE `referral_rewards.referred_tenant_id` (migration 160) —
  webhook redelivery and the twin webhook endpoints cannot double-grant.
- Self-referrals skipped (both promo-code and widget-watermark channels).
- Never raises into the webhook; failures land as `status='failed'` rows.
- Referrer notified by email on grant (`referral_reward_email.py`).
- Kill-switch works both ways: platform_settings `referral_reward_enabled`
  (migration 175) or env — flip off any time; tracking/attribution stays on.

## To launch (one step)

Railway → backend service → Variables → add `REFERRAL_REWARD_ENABLED=1`
(or set the `referral_reward_enabled` platform_settings row to on).

## To watch after launch

- `referral_rewards` rows with `status='failed'` — each carries the error.
- `/admin/referral` overview — clicks → signups → (now) rewards.
- Any month where one referrer earns >5 rewards → add the cap (decision 4).
