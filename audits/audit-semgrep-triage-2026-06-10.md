# Semgrep Triage — 2026-06-10

Closes launch-rubric 2.7 ("automated security scan run" — scan ran in CI since April, but the finding backlog was never triaged). This is the full triage.

**Scan:** `semgrep scan --config auto` v1.165.0 over `backend/`, `widget/`, `scripts/`.
**Result:** 41 findings (1 ERROR, 40 WARNING). April's local scan reported 50; the delta is code that has since been removed/fixed (e.g. `mask_email` rollout on 2026-06-10 cleared email-in-log hits in `email_sender.py`).

## Verdict: 3 real → all FIXED this session. 38 false positives / accepted — each justified below.

---

## Fixed (3)

| Finding | Location | Fix |
|---|---|---|
| `missing-user` (ERROR) — container ran as root | `backend/Dockerfile` | Added `useradd appuser` (uid 10001) + `chown /app` + `USER appuser`. Safe: app binds ports 8000/8080 (>1024), only runtime write is the LLM trace log which is already fault-tolerant (`llm_runtime.py:_write_trace` try/except). |
| `python-logger-credential-disclosure` — **raw email logged** | `backend/routers/auth.py:720` (forgot-password DB-error path) + `:770` (reset-email send failure, same class, not flagged by semgrep but found in triage) | Both now use `mask_email()` from `email_sender.py` ("j***@domain.com"). |
| `raw-html-format` — tenant-supplied `owner_name` interpolated into reset-email HTML unescaped | `backend/routers/auth.py:759` | `html.escape()` applied. Low actual risk (HTML injection into the tenant's OWN reset email; email clients don't execute script) but the fix is one line. |

## False positives — logger rule (29 remaining of 32)

The `python-logger-credential-disclosure` rule keys off the words token/password/key/credential appearing in a log *message* alongside any format arg. Every remaining hit logs only a tenant_id / lead_id / boolean / count — never a secret value. Verified line-by-line:

- `auth.py:747,828,833` — "reset token"/"password" in message text; arg is `tenant_id`.
- `channels_facebook.py:199` — logs `hub_verify_token == expected_token` (a **boolean**), not the token. `:311` — tenant_id.
- `client_portal.py:347,363` — "portal token" message; arg is `lead_id`.
- `gbp.py:128,154`, `google_calendar.py:118,120,178`, `hubspot_tenant.py:223,232,258`, `m365_calendar.py:211,220,245,280` — OAuth refresh failure paths; arg is `tenant_id` only.
- `widget_chat.py:980` — logs `api_key_status` which is the literal string `"CONFIGURED"`/`"MISSING"` (`widget_chat.py:940`), not a key. `:1008,1023` — token *counts*. `:1030` — exception message from Anthropic SDK auth error; SDK does not echo the key.
- `llm_runtime.py:147,172` — `max_tokens` / `input_tokens` / `output_tokens` counts.
- `ai_usage_guard.py:210` — "token reservation" message; args tenant/period.
- `scripts/demos/seed_powerwash_demo.py:240,262,332` — prints the **demo widget public api_key** it just created; that key is the script's deliverable for the operator and widget api keys are embedded client-side by design (public). Accepted.

## Accepted by design (6)

| Finding | Location | Justification |
|---|---|---|
| `wildcard-cors` | `backend/main.py:625` | Intentional: the embeddable widget must be callable from any tenant website. `allow_credentials=False` is set, so no cookie/credential reflection; auth is Bearer-token based. Comment block above the middleware documents this. Per-route security headers restrict framing to widget paths only. |
| `non-literal-import` ×4 | `backend/services/os_actions/__init__.py:36,41`, `os_sync/__init__.py:36,41` | `pkgutil.iter_modules` plugin discovery over **our own package directory** — module names come from files shipped in the image, not from user input. |
| `dynamic-urllib-use-detected` ×2 | `scripts/monitoring/public_uptime_probe.py:37`, `scripts/public_smoke.py:45` | Operator-owned constant endpoint lists; both already carry `# noqa: S310` with justification. |
| `missing-user` follow-ups | — | none; fixed above. |

## Re-scan cadence

- CI already runs `semgrep scan --config auto` on PRs (`.github/workflows/pr-check.yml`).
- This document is the triage baseline. New findings beyond these 38 accepted ones = regression, triage in-PR.
