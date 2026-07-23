# Decision: Stripe Connect vs per-tenant key vault (self-serve own-payments)

**Date:** 2026-07-23
**Status:** Decided — deferred build, architecture locked
**Resolves:** GH #217 (blocked on this decision since 2026-06-08)
**Context:** `plans/non-technical-readiness-roadmap_plan.md` Item 5; open question #2 in `plans/onboarding-v2_spec.md` §6

## Decision

1. **Architecture: Stripe Connect (Standard accounts, OAuth onboarding).** When we build self-serve own-payments, tenants connect their own Stripe account via Connect OAuth. We will NOT collect or store tenants' raw Stripe secret keys.
2. **Timing: deferred until a demand signal.** Do not build now. Re-open GH #217 when ANY of:
   - a paying tenant asks to collect payments from their customers through the widget/booking flow,
   - deposits-at-booking becomes a committed roadmap item,
   - tenant count crosses 10 paid.

## Why Connect over key vault

- **Liability.** A per-tenant key vault means holding other businesses' Stripe *secret* keys. A leak of one platform key becomes a leak of every tenant's payment processor. Stripe's own guidance steers platforms to Connect precisely to avoid third parties handling secret keys.
- **Webhook routing is solved by Connect.** With Connect, one platform webhook endpoint receives events for all connected accounts with per-account signatures. With BYO keys, we'd need per-tenant webhook endpoints/secrets configured inside each tenant's Stripe dashboard — support burden lands on non-technical owners (the exact people this feature targets).
- **Revenue option.** Connect allows an application fee per transaction later; a key vault never does.
- **Existing vault is not a head start for this.** `integration_key_vault.py` encrypts OAuth *tokens* for integrations (Drive/GBP). Stripe Connect also issues per-account IDs, not secrets we must guard — it fits the existing pattern; raw API keys do not.

## Why deferred

- 3 paid tenants today; zero recorded requests for own-payment collection (checked issues, brain Open Loops, tenant notes 2026-07-23).
- Platform billing (our subscriptions) works and is unrelated — this feature is only about tenants charging *their* customers.
- Connect onboarding is M–L effort with real webhook/test-mode surface; building ahead of demand contradicts the launch-focus mandate.

## Consequences

- GH #217 closes as "deferred, architecture decided" with the re-open criteria above.
- When re-opened: write-prd → grill-me → tdd-workflow per `.claude/rules/daily-skills.md`; scope is Connect OAuth flow, account linking table (new migration), per-account webhook verification, and a Settings UI card.
