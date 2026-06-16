# Paid-Signup Smoke Test (launch gate #1)

Proves the full money path end to end: a brand-new visitor cannot reach the
dashboard without paying, completing Stripe checkout flips them to active, and
the dashboard unlocks. Run once against prod before launch, and after any
change to the pay-gate, checkout, or Stripe webhook.

## Why this is partly manual

Stripe Checkout is a third-party hosted redirect — it cannot be driven
hermetically from CI. The backend half (webhook -> `plan_status=active` ->
gate opens) is covered automatically by `backend/tests/test_pay_gate_unlock.py`.
The card-entry half below needs a human (or a Stripe test-mode card) in a real
browser.

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
3. **Return unlocks.** Complete payment. You should land back on the app on
   `/setup` (the onboarding wizard), NOT the checkout gate. If you briefly see
   "Verifying payment..." that is expected — `RequirePaid` polls `/me` with
   backoff while the webhook lands (~up to 10s).
4. **Webhook fired.** In Stripe Dashboard -> Developers -> Events, confirm a
   `checkout.session.completed` event delivered 2xx to the prod webhook.
5. **DB reflects paid.** In Supabase, the new tenant row shows
   `plan_status = 'active'`, the correct `plan`, and a `stripe_customer_id`.
6. **Gate stays open.** Reload the dashboard — it loads without the gate.

## Pass criteria

All six steps hold. Any failure blocks launch:
- Step 2 shows a 503 / "not configured" -> Railway env vars missing or wrong.
- Step 3 strands on the gate past ~15s -> webhook not delivering, or
  `RequirePaid` poll not picking up the change (check `/me` returns
  `plan_status: "active"`).
- Step 5 shows `plan_status` other than `active` -> see the fraud-guard path
  (`paused`) in `backend/routers/billing.py::_handle_checkout_completed`.

## Cleanup

Delete the test tenant row (and cancel/refund the Stripe subscription) when done
so launch metrics start clean.
