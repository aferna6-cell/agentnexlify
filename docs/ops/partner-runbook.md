# Partner Emergency Runbook

**Owner:** Aidan + partner lead  
**Use when:** something breaks, a customer is angry, billing is at risk, or Aidan is unavailable.

Related docs:
- `docs/ops/refund-runbook.md`
- `docs/ops/service-continuity-plan.md`
- `docs/ops/dispute-threshold.md`

## First Move

1. Post in the partner ops chat: what happened, customer name, time noticed, and whether money/data/customer replies are affected.
2. Check the public app: `https://app.agentnexlify.com`.
3. Check the API health URL: `https://agentnexlify-production.up.railway.app/api/health`.
4. If customers can lose money, get billed twice, or see bad AI replies, pause the risky path first and diagnose second.

## Stripe Webhook Secret Rotation

**Symptom:** payments succeed in Stripe but accounts do not upgrade, invoices stay unpaid, or Stripe shows webhook failures.

1. Open Stripe Dashboard -> Developers -> Webhooks.
2. Open the AgentNexLiFy production endpoint.
3. Reveal or rotate the signing secret.
4. Open Railway -> AgentNexLiFy backend -> Variables.
5. Set `STRIPE_WEBHOOK_SECRET` to the new value.
6. Redeploy/restart the backend service.
7. In Stripe, replay one failed webhook event.
8. Confirm the tenant plan or invoice status updated in the dashboard.

## Pause New Paid Signups

**Use when:** any cold-start dispute appears, dispute rate hits the pause threshold, Stripe is unstable, or checkout creates bad subscriptions.

1. Open Railway -> backend Variables.
2. Set `STRIPE_NEW_SIGNUPS_PAUSED=true` if the flag exists.
3. If the flag is not shipped yet, remove public upgrade CTAs from the frontend or ask Aidan to patch checkout immediately.
4. Keep existing customers running unless the incident affects service delivery.
5. Link the incident to `docs/ops/dispute-threshold.md`.

## Refund Before Chargeback

**Use when:** a customer asks to cancel/refund, claims duplicate billing, or sounds close to filing a dispute.

1. Find the Stripe payment intent or charge ID in the Stripe Dashboard.
2. Call the admin refund endpoint:

```bash
curl -X POST "https://agentnexlify-production.up.railway.app/api/v1/billing/admin/refund" \
  -H "X-Api-Secret: <ADMIN_API_SECRET_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "<tenant-uuid>",
    "payment_intent": "pi_...",
    "amount_cents": 24900,
    "stripe_reason": "requested_by_customer",
    "internal_reason": "Refunded before chargeback risk.",
    "requested_by": "partner-name"
  }'
```

3. Email the customer that the refund was issued.
4. Add the reason to the customer notes.

## Failed Payment / Dunning

**Symptom:** dashboard shows `Payment Issue`, Stripe invoice is open, or customer says their card failed.

1. Open the Stripe customer.
2. Send them the hosted invoice URL if Stripe generated one.
3. Ask them to update their payment method in the billing portal.
4. Check `billing_dunning_events` for the latest `invoice.payment_failed` record.
5. Do not manually reactivate service until Stripe shows a paid invoice or Aidan confirms.

## Runaway AI Usage

**Symptom:** a tenant gets unusual traffic, AI bill spikes, or widget replies say the assistant is temporarily paused.

1. Do not delete the widget.
2. Check `tenant_ai_usage_monthly` for the tenant and current month.
3. If the tenant is legitimate and paid, raise `tenants.ai_monthly_token_hard_limit`.
4. If traffic looks abusive, leave the cap in place and contact the customer.
5. Tell the customer: "We paused the assistant because traffic spiked unusually. We are checking whether it is real visitor traffic or abuse."

## Railway Backend Broken

1. Open Railway -> backend service -> Deployments.
2. Roll back to the last green deployment.
3. Confirm `/api/health` returns 200.
4. Run the public smoke test when Aidan is available:

```powershell
.\.venv312\Scripts\python.exe scripts\public_smoke.py
```

## Vercel Frontend Broken

1. Open Vercel -> AgentNexLiFy project -> Deployments.
2. Promote or roll back to the previous working deployment.
3. Visit `https://app.agentnexlify.com/login`.
4. Confirm the dashboard loads for a test tenant.

## Supabase Trouble

**Symptom:** login fails, widget cannot save chats, or API logs show database errors.

1. Open Supabase project dashboard.
2. Check status, connection usage, and recent errors.
3. Do not run destructive SQL.
4. If a migration failed, capture the exact SQL error and stop.
5. If connection usage is high, disable nonessential automation jobs first.

## Customer Message Templates

**Refund issued:**  
"We issued the refund today. It can take a few business days to appear on your statement, depending on your bank. We are also reviewing what caused the issue so it does not happen again."

**Payment failed:**  
"Your payment did not go through, so your account is temporarily paused. Update your payment method from Billing and reply here if you want us to check it with you."

**AI usage paused:**  
"Your assistant saw an unusual traffic spike, so we paused AI replies while we verify it. Your leads and account data are safe."

## Escalate Immediately

- Customer threatens chargeback or legal action
- Stripe account warning or reserve
- Data loss or cross-tenant data exposure
- AI says something harmful or materially false
- More than one customer reports the same billing bug
