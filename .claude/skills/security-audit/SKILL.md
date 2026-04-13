---
name: security-audit
description: Scan the codebase for security vulnerabilities including missing tenant verification, unverified webhooks, unsigned OAuth state, XSS, and dangerous imports. Use when user says 'security-audit', 'security scan', 'vulnerability scan', 'audit security', 'check for XSS', 'check RLS', or asks about security audit.
version: 1.0.0
origin: claude
user-invocable: true
triggers:
- security-audit
- security scan
- vulnerability scan
- audit security
- check for XSS
- check RLS
- check CORS
effort: high
---

# Security Audit

Full-codebase security scan with severity classification and structured fixes.

## When to Use
- Periodic security review of the codebase
- Before major releases or deployments
- After a security incident or vulnerability disclosure

## When NOT to Use
- Fixing findings from a review (use security-patch-from-review instead)
- Code review for correctness (use review skill instead)
- Verifying a single security fix (check the specific change directly)

## Usage

- `/security-audit` — full scan
- `/security-audit backend/routers/` — scan specific directory

## Checks

### 1. Missing Tenant Verification
Scan all router endpoints for missing `_verify_tenant` or equivalent tenant ownership check. Every endpoint that takes `tenant_id` as a path param must verify it matches the authenticated user's tenant.

```bash
grep -rn "tenant_id.*Path\|{tenant_id}" backend/routers/ | grep -v "_verify_tenant\|verify_tenant"
```

### 2. Unverified Webhook Endpoints
Each webhook provider has its own signature pattern:
- **Twilio:** Must call `verify_twilio_request` or `_verify_twilio_signature`
- **Stripe:** Must call `stripe.Webhook.construct_event` with signature
- **Resend:** Must call `_verify_resend_signature`

Scan for webhook endpoints missing verification:
```bash
grep -rn "webhook\|/hook" backend/routers/ --include="*.py"
```

### 3. Unsigned OAuth State Parameters
OAuth callbacks must use signed JWT state tokens (pattern from `integrations.py`), not raw tenant_id.
```bash
grep -rn "state.*tenant_id\|tenant_id.*state" backend/routers/
```

### 4. XSS — Backend HTML Email Templates
Scan for user-controlled values in HTML without `html.escape()`:
```bash
grep -rn "f\".*<.*{.*}.*>.*\"" backend/ --include="*.py"
```

### 5. XSS — Frontend dangerouslySetInnerHTML
```bash
grep -rn "dangerouslySetInnerHTML" frontend/src/
```
Each usage must have sanitization (DOMPurify, escapeHtml, or sanitizeHtml).

### 6. XSS — Widget innerHTML
```bash
grep -n "innerHTML" widget/agentnexlify-widget.js
```
Every innerHTML assignment with dynamic content must use `_esc()`.

### 7. Dangerous Python Imports
```bash
grep -rn "from __future__ import annotations" backend/routers/
```
CRITICAL — breaks FastAPI. Zero tolerance.

### 8. CORS Config
Read `backend/main.py` and verify `allow_origins` is not `["*"]` in production.

### 9. SQL Injection
Scan for f-string SQL or string concatenation in queries:
```bash
grep -rn "f\".*SELECT\|f\".*INSERT\|f\".*UPDATE\|f\".*DELETE" backend/ --include="*.py"
```

### 10. Missing client_id on leads/conversations
The `leads` and `conversations` tables use `client_id`, not `tenant_id`. Scan for wrong column:
```bash
grep -rn "\.eq.*tenant_id.*lead\|leads.*tenant_id" backend/ --include="*.py"
```

## Output

Classify every finding:
- **CRITICAL** — Active exploit, data loss, or silent failure
- **HIGH** — Exploitable with moderate effort
- **MEDIUM** — Defense-in-depth failure or limited scope
- **LOW** — Informational or edge case

Report format:
```
## Security Audit Report — YYYY-MM-DD

### CRITICAL (N)
1. file.py:LINE — Description

### HIGH (N)
1. file.py:LINE — Description
...
```

## Fix Process

1. Fix CRITICAL first, then HIGH, MEDIUM, LOW
2. Each fix: minimal targeted change, verify no regression
3. Commit: `fix(security): patch N <SEVERITY> vulnerabilities — <list>`

## Gotchas

- **Widget CORS exception.** `backend/main.py` intentionally runs `allow_origins=["*"]` — the widget is embedded on unknown 3rd-party sites. Do NOT flag this as CRITICAL. Flag any OTHER endpoint running `["*"]` as CRITICAL.
- **Service role key leakage via logs.** Never log `settings.service_role_key`, Stripe webhook secret, or Anthropic API key. Scan for `logger.*{key}` and `print.*key`.
- **`verify_tenant` vs `_verify_tenant`.** Both exist, same purpose. Grep both. Also: bare `claims.get("tenant_id") == tenant_id` checks without importing the helper are equally valid — don't false-flag.
- **RLS enabled with zero policies = silent failure.** 120/146 MTOptions sessions disappeared this way. Always query `pg_policies` after enabling RLS to confirm at least one policy exists.
- **Stripe webhook signature must use raw body.** If a handler calls `await request.json()` before `stripe.Webhook.construct_event`, signature validation fails. Must use `await request.body()`.
- **OAuth `state` param must be signed JWT.** Unsigned state = CSRF vulnerability. `backend/routers/integrations.py` has the canonical pattern.
- **`innerHTML` in widget with interpolation.** Every `.innerHTML = \`... ${var} ...\`` must route through `_esc()` or the widget is XSS-able by the tenant's KB content.
- **`dangerouslySetInnerHTML` in React.** Mandatory sanitization (DOMPurify/escapeHtml). No exceptions.
- **`from __future__ import annotations` in router files.** Zero tolerance — every request 422s. Separate from security, but commonly found during audits.
- **False-positive XSS on pure-backend templates.** `render_template` with escaped Jinja vars is safe; only flag f-string HTML.
