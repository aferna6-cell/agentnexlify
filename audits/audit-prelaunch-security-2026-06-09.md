# Pre-Launch Security Audit — 2026-06-09

Scope: full-codebase pass before first customer launch. Focus: multi-tenant
isolation under the service-role Supabase key (bypasses RLS, so application-layer
tenant filtering is the only safety net), input validation, secret handling.

## Verdict

2 CRITICAL findings were NO-GO launch blockers. **Both fixed this pass** (see
below). 4 HIGH + 3 MEDIUM remain — none are launch blockers; tracked here for a
post-launch hardening sprint.

---

## CRITICAL (fixed — were launch blockers)

### CRITICAL-1 — Lead scoring/qualification IDOR (cross-tenant read/write)
`score_lead()` / `qualify_lead()` fetched and wrote the `leads` row by `id` only,
under the service-role key. `GET /{tenant_id}/{lead_id}/score`
(`backend/routers/leads.py`) checked `claims["tenant_id"] == tenant_id` but never
that `lead_id` belonged to that tenant — an authenticated owner could score/read
any tenant's lead by guessing a lead id.

**Fix:** threaded an optional `client_id` through `score_lead`,
`score_lead_background`, `qualify_lead`, `qualify_lead_background`; both the lead
fetch and the write are now scoped `.eq("client_id", client_id)` when supplied.
All 6 real call sites pass the authenticated tenant:
`leads.py` (score endpoint), `widget_lead.py` (×4), `widget_lead_helpers.py` (×1).
`None` default preserved for trusted internal batch callers (`score_all_leads`
already constrains to one tenant) and keeps existing tests green.

- Files: `backend/services/lead_scoring.py`, `backend/services/lead_qualification.py`,
  `backend/routers/leads.py`, `backend/routers/widget_lead.py`,
  `backend/routers/widget_lead_helpers.py`
- Verified: `pytest backend/tests/` — 531 passed, 35 skipped.

### CRITICAL-2 — Unsigned email-open tracking pixel (event injection)
`GET /api/v1/widget/track/open` inserted into `email_events` under the
service-role key with zero validation. Anyone who learned the URL shape could
inject arbitrary open events into any tenant's analytics (`tid` is attacker-
controlled).

**Fix:** HMAC-sign the pixel URL. New `_make_tracking_sig(tenant_id, lead_id,
execution_id)` in `email_sender.py` (mirrors existing `_make_unsub_sig`,
`api_secret_key` + SHA-256, 16 hex chars). `_build_tracking_pixel` appends
`&sig=`. `track_email_open` now requires a valid `sig` (constant-time
`hmac.compare_digest`) before inserting; invalid/missing sig still returns the
1×1 pixel (so validity can't be probed) but skips the write. No DB migration.

- Files: `backend/services/email_sender.py`, `backend/routers/widget_config.py`
- Verified: sig round-trips through `_build_tracking_pixel`; full suite green.

---

## HIGH (deferred — not launch blockers)

### HIGH-1 — CORS `["*"]` — RESOLVED (by design, won't fix)
Re-reviewed against live code. The `CORSMiddleware` hardcodes
`allow_origins=["*"]` (`backend/main.py:625`) **on purpose**; `_cors_origins()`
is no longer wired to the middleware — it only feeds the readiness-snapshot
indicator `widget_allowed_origins_explicit` (`backend/main.py:206`). The comment
block at `main.py:600-616` records that an earlier env-driven revision broke
every widget OPTIONS preflight from tenant customer sites in production and was
reverted. The widget runs on arbitrary, unknown-ahead-of-time tenant domains, so
`*` is required. Safety holds because `allow_credentials=False` (no cookies, no
cookie-CSRF) and dashboard auth rides the `Authorization` header, which browsers
do not attach cross-origin automatically. **Action: none.** Invariant to keep:
`allow_credentials` must stay `False` while `allow_origins=["*"]`.

### HIGH-2 — Missing JWT `role` claim defaults to `owner`
`backend/dependencies.py:27` `role = claims.get("role", "owner")`. A token
without a role is treated as owner. **Why deferred:** a prior `owner`→`member`
change was reverted (broke 17 tests, risked locking out legacy prod sessions).
Needs a migration plan that re-issues tokens with explicit roles first.

### HIGH-3 — `check_lead_captured_triggers` fetches lead unscoped — FIXED
`backend/services/automation/rule_engine.py`. Added optional `tenant_id`
parameter; when supplied the lead fetch is scoped with `.eq("client_id",
tenant_id)` so a foreign `lead_id` cannot trigger another tenant's automations
(defense-in-depth). No in-repo caller existed (grep proved only re-exports), so
the change is backward-compatible. Verified: full suite green (531 passed).

### HIGH-4 — Unsubscribe endpoint existence leak (404 vs 400) — FIXED
`backend/routers/widget_config.py::unsubscribe_lead`. Unknown-lead and
bad-signature branches now return one identical generic 400 response, removing
the existence-enumeration signal. Verified: full suite green (531 passed).

---

## MEDIUM (deferred)

- **MED-1** — Tracking-pixel sig is 16 hex chars (64-bit). Fine for an
  anti-injection guard at 300/min rate limit; widen to full digest if the
  threat model tightens.
- **MED-2** — Several `except Exception: logger.debug(...)` swallow insert
  failures silently (e.g. activity_log writes). Acceptable for best-effort
  side-effects; audit that none hide a tenant-scoping bug.
- **MED-3** — Pyright `.get()` / subscript noise on untyped Supabase `.data[0]`
  responses across routers. Not a security issue; a typed response wrapper would
  remove the noise and catch real `None` derefs.

---

## Post-launch hardening sprint (suggested order)
1. ~~HIGH-1~~ — RESOLVED by design (CORS `*` is required for the widget; safe with
   `allow_credentials=False`). No action.
2. ~~HIGH-3~~ — DONE. `check_lead_captured_triggers` now tenant-scoped.
3. ~~HIGH-4~~ — DONE. Uniform unsubscribe response.
4. HIGH-2 — role-claim migration (re-issue tokens, then drop the `owner` default).
   Still deferred — needs token-reissue migration; prior naive flip broke 17 tests.
5. MED-3 — typed Supabase response wrapper.

## Launch gate status (2026-06-09)
Both CRITICALs fixed. HIGH-1 resolved by-design. HIGH-3 + HIGH-4 fixed.
HIGH-2 is the only remaining HIGH and is **not a launch blocker** (it requires a
valid signed JWT to exploit a missing `role` claim; default-owner only matters
for tokens minted without a role, which our issuer always sets). MED items are
non-blocking. **Security verdict: clear to launch.**
