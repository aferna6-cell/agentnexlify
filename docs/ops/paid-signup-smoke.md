# Paid-Signup Smoke Test (launch gate #1)

Proves the full money path end to end: a brand-new visitor cannot reach the
dashboard without paying, completing Stripe checkout flips them to active, and
the dashboard unlocks. Run once against prod before launch, and after any
change to the pay-gate, checkout, or Stripe webhook.

## Why this is partly manual

Stripe Checkout is a third-party hosted redirect — it cannot be driven
hermetically from CI. The backend half (webhook -> `plan_status=active` ->
gate opens) is covered automatically by `backend/tests/test_pay_gate_unlock.py`,
and the trial-end / dunning access contract by
`backend/tests/test_trial_expiry_paygate.py`. The card-entry half below needs a
human (or a Stripe test-mode card) in a real browser.

## Preconditions

- Stripe prices exist and Railway has the env vars set:
  `STRIPE_PRICE_CHATBOT_MONTHLY`, `STRIPE_PRICE_AGENT_OS_MONTHLY`,
  `STRIPE_PRICE_USAGE_PACK` (verify: `/health` -> `sentry_configured` etc., and
  a `POST /api/v1/auth/billing/checkout` returns a `checkout_url`, not a 503).
- Stripe webhook endpoint is configured and pointing at the prod backend
  (`checkout.session.completed` subscribed).

## Steps

1. **Signup is gated.** Open the app in a fresh/incognito session. Register a
   brand-new account. You must NOT reach a usable dashboard — you should be
   sent into checkout / the "Choose your plan to continue" gate.
2. **Checkout charges the real price.** Pick a plan. Confirm the Stripe
   Checkout page loads and shows **$19.99** (chatbot) or **$99.99** (agent_os).
   - Live mode: use a real card (refund after) or a card you control.
   - Test mode: card `4242 4242 4242 4242`, any future expiry, any CVC.
3. **No upfront charge.** Checkout enables a **7-day free trial**
   (`subscription_data.trial_period_days = 7`). The card is captured but NOT
   charged today — the first charge lands on day 7. Confirm Stripe shows the
   subscription as **Trialing** with the card on file and a $0.00 amount due now.
4. **Return unlocks.** Complete payment. You should land back on the app on
   `/setup` (the onboarding wizard), NOT the checkout gate. If you briefly see
   "Verifying payment..." that is expected — `RequirePaid` polls `/me` with
   backoff while the webhook lands (~up to 10s).
5. **Webhook fired.** In Stripe Dashboard -> Developers -> Events, confirm a
   `checkout.session.completed` event delivered 2xx to the prod webhook.
6. **DB reflects a paid/trialing tenant.** In Supabase, the new tenant row shows
   `plan_status` of **`trialing`** (normal during the 7-day window) **or**
   `active`, the correct `plan`, and a `stripe_customer_id`. Both statuses open
   the gate — `pay_gate.is_pay_gated` treats `{active, trialing}` as paid.
7. **Owner alert fired.** The platform owner inbox
   (`settings.platform_support_email`) receives a **"New paid signup"** email
   with the plan, amount, tenant ID, and customer email
   (`backend/services/owner_alerts.py::notify_new_paid_signup`).
8. **Gate stays open.** Reload the dashboard — it loads without the gate.

## Pass criteria

All eight steps hold. Any failure blocks launch:
- Step 2 shows a 503 / "not configured" -> Railway env vars missing or wrong.
- Step 4 strands on the gate past ~15s -> webhook not delivering, or
  `RequirePaid` poll not picking up the change (check `/me` returns
  `plan_status` in `{active, trialing}`).
- Step 6 shows `plan_status` of `paused` -> the fraud-guard path tripped
  (`backend/routers/billing.py::_handle_checkout_completed`); a `paused` tenant
  stays locked until manual review.
- Step 7 sends no email -> check Resend config + `platform_support_email`; the
  alert never raises, so a failure here is silent (look at backend logs for
  `owner_alerts.notify_new_paid_signup: send failed`).

## Cleanup

Delete the test tenant row (and cancel/refund the Stripe subscription) when done
so launch metrics start clean.
