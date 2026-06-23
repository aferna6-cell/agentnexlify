# Audit — Untracked Python Dependencies (Reproducibility)

**Date:** 2026-06-23
**Branch:** claude/agent-nexlify-testing-28d597
**Scope:** third-party packages that `backend/**/*.py` imports but were NOT pinned in the requirements file Railway installs.
**Method:** deterministic AST scan (`ast` + `sys.stdlib_module_names`) over 381 backend `.py` files; import-name → distribution-name mapping; diff against pinned set.

---

## Authoritative requirements file for Railway

`backend/requirements.txt` is authoritative for the backend deploy. Chain:

- root `railway.json` → `build.dockerfilePath = backend/Dockerfile`
- `backend/Dockerfile` → `pip install --no-cache-dir -r backend/requirements.txt`
- base image `python:3.11-slim` (matches CLAUDE.md "Python 3.11")

There is **no** root `requirements.txt`. `agent-service/railway.json` is a separate **Node** service (`node --experimental-strip-types src/server.ts`) — out of scope for Python deps.

---

## Result

**3 genuinely-missing runtime deps.** All 3 safely pinned (versions determinable). 0 left for owner pinning.

### Pinned (added to `backend/requirements.txt`)

| Dist | Pin | Import sites | Risk if missing |
|------|-----|--------------|-----------------|
| `PyYAML` | `>=6.0,<7` | `services/attribution_service.py:19` (module-level, **unguarded**) | **Boot crash.** `attribution_service` is on the import chain from `services/activity.py`, which is imported by `routers/auth.py`, `leads.py`, `billing.py`, `stripe_webhooks.py`, etc. (all registered in `main.py`). Missing PyYAML → `ModuleNotFoundError` at startup. Highest severity. |
| `qrcode[pil]` | `>=7.4,<9` | `routers/widget_config.py:508` (lazy, inside route) | QR-code endpoint 500s on call. `[pil]` extra bundles Pillow (image backend). Not a boot failure. |
| `python-dateutil` | `>=2.8,<3` | `routers/invoices.py:519`, `automation/scheduled_jobs_ext.py:695` (lazy `relativedelta`) | Invoice + scheduled-job paths 500 on call. Not a boot failure. |

Pins verified to resolve together cleanly via `pip install --dry-run` (Python 3.11). Conservative ranges chosen to match the file's existing pinning style and avoid surprise majors.

### Not added — transitive (provided by pinned `supabase==2.28.3`)

| Import | Why not pinned |
|--------|----------------|
| `supabase_auth` (`models/database.py:8`, module-level) | Hard dependency of `supabase` 2.x (ships supabase-auth/gotrue with **version-locked** constraints). Pinning independently risks a resolver conflict with the supabase pin. Supabase owns this. |
| `postgrest` (`tests/test_schema_integration.py:95` only) | Transitive dep of `supabase`; also test-only. No deploy risk. |

### Not added — test-only / by-design

| Import | Why not pinned |
|--------|----------------|
| `pytest` | Test framework. Correctly absent from a production requirements file. |

### Noted — guarded, not a blocker

| Import | Status |
|--------|--------|
| `twilio` (`services/integration_health_checker.py:106`) | `try/except ImportError` → returns `_red(provider, "twilio sdk unavailable")`. Degrades gracefully; not in requirements by deliberate decision (see `backend/requirements.txt` lines 20-23: SDK removed 2026-04-16; `twilio_service.py` uses raw httpx). The health-checker SDK import is the only SDK usage and is import-guarded, so the dep stays optional. No action. |

---

## False-positive guards applied (not flagged)

Import-name vs distribution-name mismatches correctly resolved and treated as already-pinned:
`yaml`→PyYAML, `jose`→python-jose, `dateutil`→python-dateutil, `pythonjsonlogger`→python-json-logger,
`googleapiclient`→google-api-python-client, `google_auth_oauthlib`→google-auth-oauthlib,
`google`→google-auth, `pydantic_settings`→pydantic-settings, `sentry_sdk`→sentry-sdk.

Repo-local top-level names excluded: `backend`, `ops`, `scripts` (relative/local imports, not PyPI distributions).

---

## Verification

- AST scan: 0 parse failures across 381 files.
- Updated `backend/requirements.txt` parses and dry-run resolves with no conflict/error lines.
- Edits confined to owned files: `backend/requirements.txt` + this report. No `.py`, billing logic, embeddings, frontend, or `brain/` touched.
