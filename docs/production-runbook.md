# Production Runbook

Use this when shipping backend, frontend, or migration changes to production.

## Required Gates

1. Confirm the branch is clean and up to date with `main`.
2. Run backend tests with Python 3.12: `.\.venv312\Scripts\python.exe -m pytest -q`.
3. Run frontend tests: `npm --prefix frontend run test -- --run`.
4. Run frontend build: `npm --prefix frontend run build`.
5. Run diff hygiene: `git diff --check`.
6. For dependency/security checks, run `npm --prefix frontend audit --omit=dev --audit-level=high` and review the Python advisory audit in CI.

## Deploy Order

1. Apply database migrations first when the new code depends on them.
2. For migration `096`, run the Supabase SQL migration, then run the migration smoke test.
3. Deploy backend after the migration succeeds.
4. Deploy frontend after backend `/api/v1/healthz` and `/api/v1/version` respond.
5. Watch backend and frontend logs for at least 15 minutes.

## Migration 096 Checks

Run after applying `migrations/096_production_hardening.sql`:

```sql
SELECT conname, convalidated
FROM pg_constraint
WHERE conname IN ('leads_client_id_fkey', 'conversations_client_id_fkey');
```

```sql
SELECT COUNT(*) AS orphaned_leads
FROM leads l
WHERE l.client_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = l.client_id);

SELECT COUNT(*) AS orphaned_conversations
FROM conversations c
WHERE c.client_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM tenants t WHERE t.id = c.client_id);
```

If both orphan counts are `0`, validate:

```sql
ALTER TABLE leads VALIDATE CONSTRAINT leads_client_id_fkey;
ALTER TABLE conversations VALIDATE CONSTRAINT conversations_client_id_fkey;
```

## Smoke Checks

Set these locally or as GitHub Actions secrets:

Current marketing/public production values:

```bash
PUBLIC_BASE_URL=https://agentnexlify.vercel.app
API_BASE_URL=https://agentnexlify-production.up.railway.app
```

Dashboard app smoke checks use `PUBLIC_BASE_URL=https://app.agentnexlify.com` with the same `API_BASE_URL`.

```powershell
$env:PUBLIC_BASE_URL = "https://agentnexlify.vercel.app"
$env:API_BASE_URL = "https://agentnexlify-production.up.railway.app"
$env:PUBLIC_WIDGET_API_KEY = "optional-widget-key"
```

Run:

```bash
python3 scripts/public_smoke.py
```

```powershell
.\.venv312\Scripts\python.exe scripts\public_smoke.py
```

The public smoke test checks:

- frontend homepage loads
- frontend `/api/v1` rewrite reaches backend health
- frontend `/api/v1/version` returns build metadata
- direct backend health responds
- widget script loads with the expected content
- CORS preflight responds for the backend
- widget config loads when `PUBLIC_WIDGET_API_KEY` is set

## Manual Product Smoke

Test these before considering production healthy:

- widget chat opens and sends a message
- lead capture creates a lead
- file upload rejects disallowed file types and accepts a small valid image
- unsubscribe link returns a success page
- automation scheduler logs show one worker acquiring the DB lease
- email quota reservation does not error
- Facebook OAuth connect starts and returns through the callback
- booking reschedule and cancel links work

## Rollback

1. If frontend is broken, rollback or redeploy the previous Vercel deployment.
2. If backend is broken, rollback the Railway deployment to the previous image.
3. If the failure is migration-related, do not blindly run destructive SQL. Capture the failing query and row counts first.
4. If migration `096` leaves FK constraints `NOT VALID`, that is acceptable while orphaned historical rows are being repaired.
5. Re-run `scripts\public_smoke.py` after rollback.

## Required Production Environment

Backend:

- `ENV` or equivalent set to `production`
- `API_SECRET_KEY`
- `JWT_SECRET_KEY`
- `ADMIN_API_SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_KEY`
- `FRONTEND_URL`
- `API_URL`
- `CORS_ALLOWED_ORIGINS` or `WIDGET_ALLOWED_ORIGINS`

Frontend:

- `VITE_API_BASE_URL` when not relying on the Vercel `/api/v1` rewrite

GitHub smoke workflow:

- `PRODUCTION_PUBLIC_URL`
- `PRODUCTION_API_URL`
- `PRODUCTION_WIDGET_API_KEY` optional
- `APP_PUBLIC_URL` optional, enables dashboard app smoke checks

## Log Locations

- Backend runtime logs: Railway service logs
- Frontend runtime and deployment logs: Vercel project deployments
- Scheduled smoke checks: GitHub Actions `Public Smoke Test`
- Migration smoke checks: GitHub Actions `Staging Migration 096 Smoke Test`
