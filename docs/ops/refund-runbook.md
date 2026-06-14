# Refund Runbook

Use this when a customer reports duplicate billing, an accidental renewal, or a service-activation billing error.

## Eligible Cases

- Duplicate charge
- Customer was billed but service never activated
- Manual goodwill refund approved to prevent a dispute

Partial-month "I changed my mind" requests are not automatically refundable. Use judgment, but document the reason every time.

## Before Refunding

1. Confirm the tenant ID, Stripe customer, and payment intent or charge ID.
2. Check whether the customer already opened a dispute.
3. Verify the latest account status and cancellation state in the dashboard.
4. If the case is unclear, pause and get written approval in the partner ops thread.

## Issue the Refund

Call the admin refund endpoint:

```bash
curl -X POST "https://agentnexlify-production.up.railway.app/api/v1/billing/admin/refund" \
  -H "X-Api-Secret: <ADMIN_API_SECRET_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "<tenant-uuid>",
    "payment_intent": "pi_...",
    "amount_cents": 24900,
    "stripe_reason": "requested_by_customer",
    "internal_reason": "Duplicate charge resolved before dispute.",
    "requested_by": "partner-name"
  }'
```

## After Refunding

1. Confirm a successful response with `status=refunded`.
2. Email the customer from `help@agentnexlify.com`.
3. Add the reason and Stripe refund ID to the customer notes.
4. If this was a duplicate-charge or activation bug, log the incident in the ops thread the same day.

## Escalate Instead of Refunding

- Stripe already shows an open dispute
- More than one customer reports the same billing bug
- The customer claims fraud or unauthorized use
- The refund amount or case history does not match the dashboard
