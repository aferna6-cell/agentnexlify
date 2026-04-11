# Railway CLI Reference

Quick cheat sheet for Railway operations agentnexlify uses in production.

## Service info

| Field | Value |
|---|---|
| Service | `agentnexlify-production` |
| URL | https://agentnexlify-production.up.railway.app |
| Region | us-east |
| Build | nixpacks → Python 3.11 + Node 18 |
| Workers | 4 Uvicorn workers |

## Auth

```bash
railway login           # opens browser for auth
railway whoami          # verify token
railway link            # link local repo to Railway project
```

When token expires:
```bash
railway logout && railway login
```

## Logs

```bash
railway logs                           # tail latest deployment
railway logs --deployment <deploy_id>  # specific deploy (get id from status)
railway logs --service agentnexlify-production
```

Railway UI shows only the last ~100 lines in the dashboard; use CLI for the full dump.

## Env vars

```bash
railway variables                    # list current env
railway variables set KEY=value      # set a variable (triggers redeploy!)
railway variables delete KEY         # remove
```

**Every `variables set` triggers a redeploy.** Batch multiple sets in a single command if possible:

```bash
railway variables set FOO=1 BAR=2 BAZ=3
```

## Deploy

```bash
railway up                    # one-off deploy from local dir (rare — use git push instead)
railway status                # current deploy status
railway redeploy              # rerun the last deploy (no code change)
```

Normal flow: `git push origin main` → Railway auto-builds from `main` branch. `railway up` is for out-of-band deploys only.

## Rollback

1. `railway logs` → note the last good `<deploy_id>`
2. Dashboard → Deployments → select the good one → "Redeploy"
3. Railway CLI doesn't expose a rollback command as of 2026-04 — must use dashboard

## Variables list (current as of 2026-04-10)

Agent-related env vars:
- `ANTHROPIC_API_KEY`
- `SUPPORT_AGENT_ID`, `STRUCTURED_EXTRACTOR_AGENT_ID`, `DEEP_RESEARCHER_AGENT_ID`, `FIELD_MONITOR_AGENT_ID`, `DATA_ANALYST_AGENT_ID`
- `LEAD_QUALIFIER_AGENT_ID`, `DOCUMENT_DRAFTER_AGENT_ID`, `CODEBASE_REVIEWER_AGENT_ID`
- `MANAGED_AGENTS_ENV_ID`

Core:
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `API_SECRET_KEY`, `JWT_SECRET_KEY`, `ADMIN_API_SECRET_KEY`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `TWILIO_AUTH_TOKEN`, `TWILIO_ACCOUNT_SID`
- `RESEND_API_KEY`

## Gotchas

- **CLI token != dashboard session.** If `railway whoami` fails, re-run `railway login`.
- **`railway up` ignores `.railwayignore`.** Don't use for pushing non-repo files.
- **Setting a new var = redeploy.** Downtime ~30s. Avoid mid-customer-demo.
- **Variables aren't namespaced by env.** Staging and prod are separate Railway projects entirely — don't assume `RAILWAY_ENVIRONMENT` matters.
