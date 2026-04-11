# Vercel CLI Reference

Quick cheat sheet for Vercel operations agentnexlify uses for the frontend.

## Project info

| Field | Value |
|---|---|
| Project | `agentnexlify-frontend` |
| Framework | Vite (React) |
| Build command | `npm run build` |
| Output dir | `dist/` |
| Node version | 20 |
| Root directory | `frontend/` |

## Auth

```bash
vercel login           # browser-based auth
vercel whoami          # verify token
vercel link            # link local dir to Vercel project
```

## Deploy

```bash
vercel                 # deploys to a preview URL
vercel --prod          # promotes to production
```

Normal flow: `git push origin main` → Vercel auto-builds and deploys `frontend/` to production. Manual `vercel --prod` is for out-of-band deploys only.

## Logs

```bash
vercel logs                        # list recent deployments
vercel logs <deployment-url>       # specific deployment build logs
vercel inspect <deployment-url>    # full deploy metadata
```

Runtime logs for Vercel serverless functions are in the dashboard under the deployment's "Functions" tab. agentnexlify doesn't use serverless functions — the frontend is static, so logs are only build-time.

## Env vars

```bash
vercel env ls                            # list
vercel env add VITE_API_BASE production  # add for production
vercel env rm VITE_API_BASE              # remove
```

**Env vars don't auto-refresh.** After changing, redeploy:

```bash
vercel --prod --force
```

## Rollback

1. Dashboard → Deployments → find the last good build
2. Click "..." → Promote to Production
3. Takes ~20s to swap the alias

No CLI equivalent for `promote` — must use dashboard.

## Variables list

Frontend env vars (all `VITE_` prefixed):
- `VITE_API_BASE` — backend URL (https://agentnexlify-production.up.railway.app)
- `VITE_STRIPE_PUBLIC_KEY` — Stripe publishable key
- `VITE_SUPABASE_URL` — public Supabase URL
- `VITE_SUPABASE_ANON_KEY` — public anon key

## Gotchas

- **Vite env vars must be `VITE_`-prefixed.** Without the prefix, the value is NOT exposed to the browser bundle.
- **Env var changes need a rebuild.** Vercel caches the build output; setting a new env var does NOT rebuild until you push or `vercel --prod --force`.
- **Build output size matters.** Vercel has a 100MB limit per deployment. `recharts` and `react-vendor` chunks are the biggest offenders.
- **Preview deploys are public by default.** Any PR gets a publicly-accessible preview URL. Don't put secrets in branch names.
- **`vercel --prod` from a dirty working tree uploads uncommitted files.** Always commit before using this. Normal flow (git push) only deploys what's in the remote.
- **Custom domains have their own SSL cert rotation.** If a customer-facing domain alias stops working, check the SSL status in the dashboard.
