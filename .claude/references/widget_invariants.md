# Widget Invariants — Reference Pack

Load before editing `widget/` or `frontend/public/widget/`.

## Byte-Identical Rule

`widget/agentnexlify-widget.js` MUST be byte-identical to `frontend/public/widget/agentnexlify-widget.js`.

**Why:** tenants embed the public copy from their site. Dev copy is source of truth. Mismatched → embeds break silently on tenant sites.

**How to apply:**
- Edit `widget/agentnexlify-widget.js` first
- Copy byte-for-byte to `frontend/public/widget/agentnexlify-widget.js`
- Verify: `diff widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js` → empty output
- Commit both files in same commit

## Cross-Origin Embedding

Widget loads from `*.agentnexlify.com` → embedded on `*.client-domain.com`. Cross-origin boundary at every API call.

**Required:**
- All API calls include `credentials: 'omit'` unless cookie auth is intentional
- CORS on FastAPI must allow specific tenant origins, not `*` when credentials involved
- `postMessage` between iframe + parent uses explicit target origin, never `*`
- No `window.parent.*` access without origin check

**Forbidden:**
- `localStorage` / `sessionStorage` assumptions — may be blocked in third-party context
- Cookies set without `SameSite=None; Secure` when needed cross-site
- Synchronous XHR — blocks parent page rendering

## Script Loading Contract

Tenant site includes:
```html
<script src="https://agentnexlify.com/widget/agentnexlify-widget.js" async data-tenant-id="..."></script>
```

**Required:**
- `async` safe — script must not depend on DOM ready synchronously
- `data-tenant-id` attribute read at boot, used for all API calls
- No global namespace pollution beyond `window.AgentNexLiFy`
- Single boot only — re-including script must not double-boot

## Widget API Surface

All endpoints consumed by widget:
- `POST /api/chat` — message stream (SSE)
- `POST /api/leads` — lead capture
- `POST /api/appointments` — booking
- `GET /api/tenant/{tenant_id}/config` — tenant-facing config only (no secrets)

**Required:**
- Every payload includes `client_id` (tenant identifier) — see `tenant_isolation.md`
- Never send or accept `tenant_id` column name — legacy, removed
- Rate limit gracefully — widget must not break when backend throttles

## Testing

- Cross-origin smoke via `.claude/skills/widget-test/SKILL.md`
- Open tenant HTML with widget in iframe, check network + console
- Verify byte-identical copy before every commit touching widget

## Anti-patterns

- Never `localStorage.getItem(...)` without try/catch + fallback
- Never call `window.parent.postMessage(data, '*')` — use explicit origin
- Never inline secrets in widget JS — widget is PUBLIC
- Never break the single-bundle constraint by adding import statements
- Never skip the byte-identical verification when touching widget

## Cross-refs

- `CLAUDE.md` — Critical invariant #4 (byte-identical)
- `.claude/rules/widget-rules.md`
- `.claude/skills/widget-test/SKILL.md`
- `widget/CONTEXT.md`
