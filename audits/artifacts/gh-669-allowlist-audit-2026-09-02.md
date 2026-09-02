# Allowlist audit — DemoRoleBlockMiddleware (#749 / GH #669)

**Date:** 2026-09-02  
**Scope:** read-only post-merge security audit of `DEMO_MUTATION_ALLOWLIST_PREFIXES`  
**Verdict:** **PASS** (with documented residual sandbox mutations)

## Evidence

| Check | Result |
|-------|--------|
| Implemented by | #749 (`17bab2dd` merge) |
| PR Validation on head `4ceaaa5a` | SUCCESS |
| Central mutation middleware present | PASS |
| Money/destructive secondary `block_demo_role` | PASS |
| Allowlist audit | PASS |

Money/destructive routers (all still carry `Depends(block_demo_role)`):

- `backend/routers/billing.py`
- `backend/routers/auth_billing.py`
- `backend/routers/billing_addons.py`
- `backend/routers/billing_usage.py`
- `backend/routers/phone.py`
- `backend/routers/account_deletion.py`

Under the broad `/api/v1/auth` allowlist, money routes (`auth_billing`, `billing_addons`) keep **router-level** `dependencies=[Depends(block_demo_role)]`. That is the critical secondary guard the design relies on.

## Allowlist prefixes audited

```text
/api/v1/auth
/api/v1/webhooks
/api/v1/twilio
/api/v1/widget
/api/widget
/api/v1/widget-health
/api/v1/forms/public
/api/v1/book
```

### Ingress / public (expected allow)

- Auth login/register/demo-login/password-reset/google-register
- Stripe / Resend / Twilio inbound webhooks (provider-signed; no demo JWT required)
- Widget chat/lead/book/photo-quote/public book page

### Owner-gated under allowlist (demo blocked by `require_role`)

These sit under allowlisted prefixes but still reject `role=demo` via owner/admin role checks:

- `POST/DELETE /api/v1/auth/mcp-key/{tenant_id}` — `require_role("owner")`
- `PUT /api/v1/auth/settings/{tenant_id}` — `require_role("owner","admin")`
- Webhook CRUD under `/api/v1/webhooks/{tenant_id}` — `require_role("owner","admin")`
- FAQ update — `require_role("owner","admin")`

### Residual sandbox mutations (accepted for #669 close; follow-up hardening)

Demo JWT can still mutate **demo-tenant-scoped** surfaces that only require `_get_current_tenant` (not owner) under allowlisted prefixes:

- FAQ create/delete
- Conversation tag updates
- Widget config online-status / allowed-domains / auth widget-config update

These are confined to the demo sandbox tenant (outbound still no-ops via `demo_guard`). They are **not** money/destructive. Follow-up options (not blocking close):

1. Narrow `/api/v1/auth` allowlist to explicit auth ingress paths, **or**
2. Add `block_demo_role` / owner checks on the residual routes, **or**
3. Extend the CI invariant to enumerate every mutating route under allowlisted prefixes and assert either public-by-design, owner-gated, or demo-blocked.

## Closure checklist (for GH #669)

```text
Implemented by #749
PR Validation: SUCCESS
central mutation middleware: PASS
money/destructive secondary guards: PASS
allowlist audit: PASS
```

**Note:** This agent cannot close GH #669 via API (integration 403 on issues). Owner should paste the checklist above and close the issue.
