---
paths:
  - "backend/routers/auth.py"
  - "backend/routers/stripe_webhooks.py"
  - "backend/routers/billing.py"
  - "backend/routers/client_portal.py"
  - "backend/services/email_sender.py"
  - "backend/dependencies.py"
---

# Security-Critical Code

Changes to these files require extra scrutiny. Run the security-audit skill before committing.

## Hard Rules
- NEVER skip security review on auth or payment endpoints
- ALL tenant-specific queries MUST use RLS or explicit tenant_id filtering
- ALL Stripe integration MUST use production keys in production (NEVER test keys)
- ALL API endpoints MUST have input validation and proper error responses
- NEVER commit .env files or log secret values
- NEVER add new features without running the test suite first

**Why:** Multi-tenant SaaS — a single missing tenant filter leaks data across ALL customers. A single logged secret compromises all tenants.
