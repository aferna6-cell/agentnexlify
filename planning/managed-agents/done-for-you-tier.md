# Managed AI Workforce — Done-For-You Tier ($299.99/mo + $199 setup)

Shipped 2026-08-25 (owner-directed revenue session, idea 4). Plan key:
`agent_os_managed`. Sales-led: sold via a checkout link you send, never the
self-serve plan grid. 34 clients at this price = the $10k/mo profit target on
this tier alone.

## What the customer gets

Everything in AI Workforce (`agent_os`), plus the work they will never do
themselves:

- **White-glove setup ($199 one-time):** widget installed with them on a
  call, knowledge base built from their site + intake questions, greeting and
  booking flow tuned to their business.
- **Monthly tuning:** conversation review, KB updates, prompt adjustments,
  a monthly summary of what their AI handled.
- **Priority support:** direct line, 1-business-day response.
- **Voice included:** live AI phone answering (plan-included; no add-on).

## Why this tier is the profit engine

Small businesses buy outcomes: the pitch is a receptionist problem solved,
against GoHighLevel's $497 tier. Cost to serve stays software-shaped (AI
baseline 8M tokens/mo ≈ $40 ceiling) plus 1-2 hours of monthly human tuning.
Margin ≈ $230+/client/mo.

## Selling it (checkout link, no UI work)

The tier is live in the backend once the two Stripe prices exist. Flow:

1. Stripe dashboard → create prices: $299.99/mo recurring + $199.00 one-time.
2. Railway → set `STRIPE_PRICE_AGENT_OS_MANAGED_MONTHLY` +
   `STRIPE_PRICE_AGENT_OS_MANAGED_SETUP`.
3. On a closed sale, create the checkout from the API (or have the customer's
   account owner hit checkout with `plan=agent_os_managed`) — both checkout
   endpoints already build the setup + monthly line items and the webhook
   activates the plan (AMOUNT_TO_PLAN 29999 / 49899 map to it as fallback).

Plan-change upgrades from an existing subscription skip the setup fee
(change-plan prorates the recurring price only) — invoice the $199 manually
or run a fresh checkout for upgrades where setup is real work.

## What is wired (2026-08-25)

- `plan_catalog.CURRENT_PAID_PLANS` + `PREMIUM_PLANS` — all premium gates
  (Zapier, unlimited SMS, doc drafting, lead qualification, white-label).
- `agent_os_gate.AGENT_OS_PLANS` — Agent OS suite + marketing surfaces.
- `ai_usage_guard.PLAN_BASELINE_TOKENS` = 8,000,000 (+ reconciliation mirror).
- Voice: `_AI_VOICE_PLANS` includes it; voice add-on checkout refuses it
  (already included).
- Rate limits (480/min, same surface as agent_os), funnel/tenant-health/churn
  metrics count it as paid, churn call list frames it at $299.99/mo.
- Display name: "Managed AI Workforce" (`frontend/src/utils/planDisplay.js`).

## Delivery playbook (per client, ~2h/mo after setup)

- Week 0: setup call, KB build (use the vertical preset + their site), widget
  live, booking on, test conversation together.
- Weekly: skim conversation log (5 min) — fix any wrong answer in the KB.
- Monthly: send the value digest with a 3-line personal note; one tuning pass.
