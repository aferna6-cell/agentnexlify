# Service Continuity Plan

Use this if Aidan is unavailable and customers still need the service to keep running.

## Goal

Keep production stable for 30 days without heroics. Prefer containment and rollback over risky fixes.

## Minimum Access Inventory

At least one partner besides Aidan should be able to reach:

- Railway production backend
- Vercel production frontend
- Stripe dashboard and webhooks
- Supabase dashboard
- `help@agentnexlify.com`

## Default Rule

If the issue is customer-facing and the rollback path is obvious, roll back first and investigate second.

## Safe Actions Partners Can Take

- Rotate `STRIPE_WEBHOOK_SECRET`
- Roll back a Railway deployment
- Roll back a Vercel deployment
- Pause new paid signups
- Issue an approved refund through the admin refund endpoint
- Leave AI usage caps in place during suspicious traffic spikes

## Actions Partners Should Not Take Alone

- Running destructive SQL
- Editing migrations in production
- Manually patching tenant records without a written reason
- Rotating more than one production secret at once

## Communication Cadence

- Post a status update in the partner ops thread within 15 minutes
- If customers are affected, reply from `help@agentnexlify.com` the same day
- Keep one running incident timeline until the issue is resolved

## Reference Docs

- `docs/ops/partner-runbook.md`
- `docs/ops/refund-runbook.md`
- `docs/incident-response-playbook.md`
- `docs/production-runbook.md`
