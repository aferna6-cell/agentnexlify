# Security Audit Report — AgentNexLiFy
**Date:** 2026-04-05
**Auditor:** Security Reviewer Agent (claude-sonnet-4-6)
**Scope:** backend/, frontend/src/, widget/

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 4 |
| MEDIUM | 3 |
| LOW | 2 |
| PASS | 12 |

---

## CRITICAL Findings

### CRIT-01 — Live Supabase credentials present in committed .env file
**File:** `.env` (lines 1–3)
**Status:** File is in `.gitignore` and does NOT appear in git history. However the file exists on disk with real production credentials.

```
SUPABASE_URL=https://pxserpybmajixqrmzaly.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...   (anon key)
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  (service_role key)
```

The SUPABASE_SERVICE_KEY is a `service_role` JWT that **bypasses all Row-Level Security**. If this file is ever accidentally committed (e.g., `git add .` before .gitignore is loaded), these credentials would be exposed in git history permanently.

**Risk:** Complete database compromise. Any actor with the service key can read/write/delete all tenant data, bypassing RLS.

**Fix:**
1. Rotate the Supabase service key immediately via the Supabase dashboard.
2. Add a pre-commit hook that explicitly blocks any `.env` file containing real JWT patterns. The current hook may not catch this.
3. Consider using a secrets manager (Railway environment variables) exclusively and deleting the local `.env` file.

---

## HIGH Findings

### HIGH-01 — XSS via unsanitized user content in SequenceBuilder email preview
**File:** `frontend/src/pages/Automations/SequenceBuilder.jsx` (lines 234–236, 258–261)

The `sanitizeHtml()` function used in `resolveTemplateVars()` performs only basic regex stripping of `<script>` tags and `on*=` attributes. It does NOT strip:
- `<img src=x onerror=...>` style payloads
- `<svg onload=...>`
- `javascript:` protocol in `href`
- `<iframe>` elements
- `<link>` tags with external resources

The `resolvedSubject` and `resolvedBody` values are then injected directly via `dangerouslySetInnerHTML`. Since these values come from tenant-created email templates stored in the database, a malicious team member or compromised admin account could inject arbitrary HTML/JS that executes in other team members' browsers.

```js
// SequenceBuilder.jsx line 234
dangerouslySetInnerHTML={{
  __html: `<strong>Subject:</strong> ${resolvedSubject || "(no subject)"}`,
}}
// SequenceBuilder.jsx line 258
dangerouslySetInnerHTML={{
  __html: resolvedBody || '...',
}}
```

**Fix:** Replace the custom regex sanitizer with DOMPurify:
```js
import DOMPurify from "dompurify";

function sanitizeHtml(html) {
  if (!html) return "";
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
}
```
Install: `npm install dompurify`

---

### HIGH-02 — Incomplete HTML sanitization in DocumentsPage
**File:** `frontend/src/pages/DocumentsPage.jsx` (lines 14–19)

```js
function sanitizeDocHtml(html) {
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
    .replace(/on\w+\s*=\s*["'][^"']*["']/gi, "");
}
```

Documents can contain `<iframe>`, `<object>`, `<embed>`, `<form>`, `<link>`, SVG with `onload`, `href="javascript:..."` and many other XSS vectors. The document HTML (`template_html` / `rendered_html`) is tenant-authored and stored in the database, then rendered via `dangerouslySetInnerHTML`.

**Fix:** Use DOMPurify with `FORCE_BODY: true` and `FORBID_TAGS` for `iframe`, `object`, `embed`:
```js
import DOMPurify from "dompurify";
DOMPurify.sanitize(html, {
  FORCE_BODY: true,
  FORBID_TAGS: ["script", "iframe", "object", "embed", "form", "link", "meta"],
  FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover"],
});
```

---

### HIGH-03 — Wildcard CORS on all API routes
**File:** `backend/main.py` (lines 318–324)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

All API routes — including authenticated dashboard endpoints, billing operations, and admin functions — accept requests from any origin. The comment in the code correctly notes this is needed for the embeddable widget. However, origin-based restrictions (even weak ones) provide defense-in-depth for dashboard routes. An attacker who tricks a logged-in user into visiting a malicious site can make authenticated API calls using the victim's JWT (from localStorage or memory).

**Partial mitigations present:** `allow_credentials=False` prevents cookie-based CSRF. JWT auth from `Authorization` header cannot be automatically included by cross-origin requests, so actual exploit requires either a stored XSS vector or a misconfigured frontend.

**Recommended fix:** Split the CORS configuration — apply `allow_origins=["*"]` only to `/api/v1/widget/*` routes, and restrict dashboard routes to `settings.frontend_url`:
```python
# Widget routes: origins=["*"]
# Dashboard routes: origins=[settings.frontend_url, "https://agentnexlify.vercel.app"]
```

---

### HIGH-04 — No security headers on HTTP responses
**File:** `backend/main.py` (entire file — absence of middleware)

The API sets no HTTP security headers. Missing:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security`
- `Content-Security-Policy` (even a minimal one)
- `Referrer-Policy`
- `Permissions-Policy`

**Fix:** Add a security headers middleware:
```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```
Or use the `secure` package: `pip install secure`.

---

## MEDIUM Findings

### MED-01 — Supabase ilike queries pass partially-sanitized user input
**Files:**
- `backend/routers/leads.py` lines 62–67 and 583–588
- `backend/routers/clients.py` lines 61–65
- `backend/routers/smart_lists.py` lines 116–120
- `backend/routers/snippets.py` line 58

The search parameter is interpolated into the PostgREST filter string using an f-string:
```python
f"name.ilike.%{safe_search}%,email.ilike.%{safe_search}%,phone.ilike.%{safe_search}%"
```

`leads.py` and `clients.py` strip commas and dots before interpolation (`safe_search = search.replace(",", "").replace(".", "").strip()`), but `snippets.py` and `smart_lists.py` do not sanitize at all. PostgREST parses this string server-side. While the Supabase Python client transmits this as a query parameter (not raw SQL), the PostgREST filter syntax has its own injection surface — special characters like `(`, `)`, `.`, `not`, `or` could manipulate the filter logic.

**Specific gap in snippets.py (line 58):** No sanitization at all before interpolation.

**Fix:** Apply the same comma/dot stripping used in `leads.py` to all ilike search parameters. Additionally, escape or reject `%` and `_` wildcards in user input (they are valid PostgreSQL LIKE wildcards):
```python
safe_search = search.replace(",", "").replace(".", "").replace("%", "").replace("_", "").strip()
```

---

### MED-02 — billing.py /create-checkout uses api_secret_key as an auth mechanism
**File:** `backend/routers/billing.py` (lines 27–29)

```python
def _verify_secret(x_api_secret: str = Header(...)):
    if x_api_secret != settings.api_secret_key:
        raise HTTPException(status_code=403, detail="Invalid API secret")
```

The billing create-checkout endpoint is protected by comparing a request header to `settings.api_secret_key` — the same key used to sign all JWTs. If this key is ever leaked (e.g., via a misconfiguration, log line, or env var exposure), an attacker could both forge JWT tokens AND create Stripe checkout sessions for any tenant_id they supply. This is a key reuse problem — one key should not serve two authentication purposes.

Also: the `tenant_id` in the request body is not verified against any authenticated session. Any caller who knows the api_secret_key can create a checkout for any tenant.

**Fix:** Use a separate `BILLING_SECRET` env var for the billing endpoint. Better: convert this endpoint to use standard JWT auth (`_get_current_tenant`) so only the tenant themselves can create their own checkout.

---

### MED-03 — Hardcoded production API base URL in client_portal.py
**File:** `backend/routers/client_portal.py` (line 439)

```python
"api_base": "https://agentnexlify-production.up.railway.app",
```

This hardcoded URL is returned to public portal users and used by the client-facing portal page. If the production API URL changes, this creates a broken dependency. More importantly, it prevents proper staging/dev environments from functioning and is a form of configuration leakage.

**Fix:** Use `settings.api_url` instead:
```python
"api_base": settings.api_url,
```

---

## LOW Findings

### LOW-01 — Default fallback JWT secret is a predictable string
**File:** `backend/config.py` (lines 12, 51–52)

```python
_DEV_FALLBACK_SECRET = "INSECURE-DEV-ONLY-CHANGE-ME-IN-PRODUCTION"
api_secret_key: str = _DEV_FALLBACK_SECRET
```

If `API_SECRET_KEY` is not set in production (e.g., env var misconfiguration on Railway), the app silently uses this predictable fallback. An attacker knowing this default could forge JWTs and impersonate any tenant. The startup warning (line 286–289) is good, but the system continues running.

**Fix:** In production, fail hard at startup if the key is not set:
```python
if settings.api_secret_key == _DEV_FALLBACK_SECRET and os.getenv("ENVIRONMENT") == "production":
    raise RuntimeError("API_SECRET_KEY must be set in production")
```

---

### LOW-02 — Twilio signature verification falls back silently to rejection when token not configured
**File:** `backend/routers/twilio_webhooks.py` (lines 34–36)

```python
def _verify_twilio_signature(request: Request, body: bytes) -> bool:
    if not settings.twilio_auth_token:
        return False
```

When `TWILIO_AUTH_TOKEN` is not configured, signature verification returns `False`, which causes `handle_missed_call` to return HTTP 403. This is secure behavior (rejects requests), but it will also silently block all legitimate Twilio webhooks without a clear error. The logging at line 89 warns on failure but not on misconfiguration.

**Fix:** Log a distinct startup warning when Twilio is partially configured (account SID set but no auth token), to make misconfiguration obvious.

---

## Passing Checks

| Check | Result |
|-------|--------|
| Hardcoded `sk_live_`, `sk_test_`, `sk-ant-` in source files | PASS — none found |
| `eval()`, `exec()`, `os.system()` in backend | PASS — none found |
| `subprocess` with `shell=True` | PASS — none found |
| `pickle.loads()` with user input | PASS — none found |
| Raw SQL string concatenation (f-strings in SQL) | PASS — Supabase ORM used throughout |
| Password hashing algorithm | PASS — bcrypt used correctly (`bcrypt.hashpw`, `bcrypt.checkpw`) |
| JWT algorithm specified explicitly | PASS — `algorithms=[_JWT_ALGORITHM]` in all decode calls |
| JWT secret key used in decode | PASS — secret always passed, no `algorithms=[]` bypass |
| Password logging | PASS — no logger calls include passwords or tokens |
| Stripe webhook signature verification | PASS — `stripe.Webhook.construct_event()` used |
| Twilio webhook signature verification | PASS — HMAC-SHA1 verified (when configured) |
| SSRF protection in website crawler | PASS — `_is_safe_url()` blocks private IPs and localhost |
| npm audit (frontend) | PASS — 0 vulnerabilities found |
| ConversationsPage renderMarkdown XSS | PASS — `_inlineMd()` escapes `&`, `<`, `>` before processing; links restricted to `https?://` |
| Tenant isolation (all 10 sampled routers) | PASS — all verify `claims["tenant_id"] == tenant_id` before queries; all DB queries filter by tenant_id/client_id |
| Role-based access on sensitive routes | PASS — `require_role("owner")` on billing portal, MCP key generation, team management |
| Password reset token entropy | PASS — `secrets.token_urlsafe(32)` used |
| Forgot-password email enumeration | PASS — same response returned whether email exists or not |
| File upload type validation (service photos) | PASS — content_type allowlist and 10MB size cap enforced |

---

## Priority Remediation Order

1. **CRIT-01** — Rotate Supabase service key now. Verify .env is not in git history.
2. **HIGH-01 / HIGH-02** — Install DOMPurify and replace both custom regex sanitizers.
3. **HIGH-04** — Add security headers middleware (5-minute fix).
4. **MED-01** — Sanitize snippets.py search input; add `%` and `_` escaping across all ilike searches.
5. **MED-02** — Separate billing auth from JWT signing key.
6. **HIGH-03** — Split CORS configuration to restrict dashboard routes.
7. **LOW-01** — Add hard startup failure when fallback JWT secret detected in production.
8. **MED-03** — Replace hardcoded API URL with `settings.api_url`.
