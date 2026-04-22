---
name: deploy-workflow
description: "Use BEFORE pushing to main or triggering a Railway/Vercel deploy. Runs pre-deploy gates (build, tests, migration status, widget-file sync) and flags any blocker before remote deploy starts. This is the Type 7 (CI/CD & Deployment) skill per the 9-type taxonomy."
version: 1.0.0
origin: claude
user-invocable: true
disable-model-invocation: true
triggers: ["deploy", "deploy check", "ship", "push to main", "ready to deploy", "pre-deploy"]
allowed-tools: ["Bash", "Read", "Grep", "Glob"]
effort: medium
---

# Deploy Workflow

Pre-deploy validation + deploy orchestration for Railway (backend) + Vercel (frontend). Type 7 in the 9-type skill taxonomy (CI/CD & Deployment).

## When to Use
- Any time the user asks to deploy, ship, push, or release
- Before running `git push origin main` when the push will trigger a production deploy
- After finishing a feature build, before calling it "done"
- When a deploy fails and you need to diagnose which gate broke

## When NOT to Use
- Frontend-only dev work that doesn't trigger a deploy
- Staging/branch deploys (use CI pipeline directly)
- Rollback scenarios (use `/recover` or Railway/Vercel dashboards)
- Emergency hotfixes where the user explicitly says "bypass checks"

## Pre-Deploy Gates (in order)

Run these in sequence. A failure at any gate is a hard stop — do NOT continue to the next gate until the current one is green.

### Gate 1: Clean working tree
```bash
git status --short
```
Any uncommitted change is a blocker unless explicitly authorized. Stage + commit or stash before deploying.

### Gate 2: Frontend build
```bash
cd frontend && npm run build 2>&1 | tail -10
```
Build must complete with "built in Xs". Any error aborts the deploy.

### Gate 3: Backend tests
```bash
python3 -m pytest backend/tests/ -q 2>&1 | tail -20
```
Every test that previously passed must still pass. Skipped tests are OK; failures are not.

### Gate 4: Widget file sync
```bash
diff widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js
```
Must be byte-identical. Pre-push hook enforces this, but run it here for faster feedback.

### Gate 5: Migration status
```bash
ls -1 migrations/ | tail -5
```
Check each recent migration is applied in prod. See `migration-workflow` skill for verification SQL.

### Gate 6: Secret scan on staged diff
```bash
git diff --cached | grep -E "sk-ant-|sk-live-|rk_live_|SUPABASE_SERVICE_KEY.*=" || echo "clean"
```
Any hit is a hard block. Never commit secrets.

### Gate 7: Health endpoints (local)
```bash
curl -s http://localhost:8000/health 2>&1 || echo "backend not running locally - skip"
```
Optional if local backend isn't running.

## Deploy Targets

### Backend — Railway
- Trigger: `git push origin main`
- Service: `agentnexlify-production`
- Auto-build from latest `main` commit
- Env vars: managed via Railway dashboard OR `railway variables set KEY=VAL`
- Rollback: Railway dashboard → Deployments → Rollback

### Frontend — Vercel
- Trigger: `git push origin main` (auto-deploys)
- Project: `agentnexlify-frontend`
- Build command: `npm run build`
- Rollback: Vercel dashboard → Deployments → Promote previous

## Post-Deploy Verification

After the push, wait for the deploy to finish (Railway: ~3 min, Vercel: ~1 min), then:

```bash
curl -s https://agentnexlify-production.up.railway.app/health | head -20
curl -s https://agentnexlify-production.up.railway.app/api/v1/managed-agents/health | head -20
```

Expected: `{"status": "ok"}` and (if Managed Agents configured) the 8-agent list.

## Gotchas

- **Railway deploys on every push to main.** No manual trigger step. If the push goes through, the deploy starts. Don't push speculative changes.
- **Vercel + Railway are independent.** A Railway failure doesn't block Vercel and vice versa. Always verify both URLs after a deploy.
- **In-memory caches are per-worker.** Production runs 4 Uvicorn workers. A deploy wipes all 4 caches simultaneously — the first 20-30 requests after deploy will miss cache and run slow. This is expected.
- **Railway env var sync is manual.** Adding an env var in `.env.example` does NOT propagate to Railway. Must set via dashboard or MCP. 2026-04-10 managed agent deploy broke because the 5 new env vars weren't in Railway. Always run `/railway-env-check` or list-variables before pushing a feature that depends on a new env var.
- **Migration files don't auto-apply.** Prod schema must be updated separately via Supabase MCP or Management API. See `migration-workflow` skill. Widget fallback (migration 101) broke in local tests because the column didn't exist yet.
- **Pre-push hook can be bypassed with `--no-verify`.** DO NOT DO THIS without the user's explicit instruction. The hook is the only automated gate between local work and prod.
- **SSH key missing → `git push` fails silently.** "Host key verification failed" means gh auth or SSH setup is broken. Fix auth before retrying, don't keep pounding on the push.
- **Stripe webhooks are keyed to `STRIPE_WEBHOOK_SECRET` per env.** Prod and staging use different secrets. Copying env vars between envs → signature verification fails → webhooks 400.
- **CORS config change deploys instantly.** No gradual rollout. If you change `allow_origins` and break the widget, every embed on every customer site breaks within 3 minutes of the push. Test with a curl preflight first.
- **Railway build uses Python 3.11.** Local dev often uses 3.12. Packages that work locally may fail in Railway build. When in doubt, test imports against Python 3.11 before pushing.
- **Field-monitor cron runs on GitHub Actions, not Railway.** Deploying backend doesn't update the cron — it's a separate workflow file.

## Files in This Skill

- `SKILL.md` — this file (the trigger + workflow)
- `scripts/preflight.sh` — runs all 7 pre-deploy gates in sequence, exits 0 on pass, 1 on first failure
- `references/railway-cli.md` — Railway CLI cheat sheet for deploys, env vars, logs, rollback
- `references/vercel-cli.md` — Vercel CLI cheat sheet

## Related

- `verification-loop` — broader verification, use when not deploying
- `migration-workflow` — migration-specific checks
- `widget-test` — widget-specific verification (Gate 4 is a subset)
- `/deploy` slash command — manual invocation
- `/deploy-check` slash command — gates only, no push
