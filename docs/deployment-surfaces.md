# Deployment Surfaces

Use this map when debugging GitHub, Vercel, Railway, or production smoke failures.

## Canonical Surfaces

| Surface | Platform | Root directory | Primary URL | Purpose |
| --- | --- | --- | --- | --- |
| Marketing/public site | Vercel | `landing-page-v2` | `https://agentnexlify.vercel.app` | Public landing page plus widget asset and API rewrite smoke coverage |
| Dashboard app | Vercel | `frontend` | `https://app.agentnexlify.com` | Customer/admin React dashboard |
| Backend API | Railway | repo root | `https://agentnexlify-production.up.railway.app` | FastAPI API, widget config, health, and version endpoints |

## Git Author For Vercel Checks

Vercel's GitHub integration must be able to map the commit author email to a GitHub account. For agent commits on this repository, use the GitHub noreply address for `aferna6-cell`:

```bash
git config --global user.name "aferna6-cell"
git config --global user.email "228568372+aferna6-cell@users.noreply.github.com"
```

Check the author before pushing:

```bash
git log -1 --format='%an <%ae>'
```

If Vercel shows `No GitHub account was found matching the commit author email address`, push a new commit with the noreply author. Avoid rewriting `main` history unless everyone working from the branch agrees.

## GitHub Secrets

The `Public Smoke Test` workflow runs on pushes to `main`, on a daily schedule, and manually.

Required or defaulted:

- `PRODUCTION_PUBLIC_URL`: marketing/public site URL. Defaults to `https://agentnexlify.vercel.app` when unset.
- `PRODUCTION_API_URL`: Railway API URL. Defaults to `https://agentnexlify-production.up.railway.app` when unset.

Optional:

- `PRODUCTION_WIDGET_API_KEY`: enables the authenticated widget config smoke check.
- `APP_PUBLIC_URL`: enables an additional dashboard app smoke pass, usually `https://app.agentnexlify.com`.

`PRODUCTION_WIDGET_API_KEY` should point at the dedicated Supabase smoke tenant:

- business name: `AgentNexLiFy Smoke Test`
- owner email: `smoke-test@agentnexlify.invalid`
- reusable smoke lead email: `smoke-e2e@agentnexlify.invalid`

Use this tenant for uptime and deployment checks so production monitoring does not depend on a real customer or demo account.

## Widget Asset Sync

The canonical widget files live in `widget/`. Run this after changing either widget asset:

```bash
python scripts/sync_widget_assets.py
```

CI enforces that these copies stay identical:

- `frontend/public/widget/agentnexlify-widget.js`
- `frontend/public/widget/preview.html`
- `landing-page-v2/widget/agentnexlify-widget.js`
- `landing-page-v2/widget/preview.html`

## Deployment Log Access

`npx vercel inspect <deployment-id> --logs` requires a logged-in Vercel account or a valid Vercel token. Without credentials, use the Vercel dashboard deployment logs for the relevant project, then verify the repo-side fixes with:

```bash
python scripts/public_smoke.py
npm --prefix frontend run build
```

## Uptime Monitoring

Use `ops/monitoring/uptime-checks.json` as the source of truth for external uptime monitors. Import those checks into Better Stack, UptimeRobot, Uptime Kuma, or the hosted monitor you use for production alerting. The production checks should alert after two consecutive failures and should notify an external channel, such as Slack or email, so outages are not only visible inside GitHub Actions.

The `Public Uptime Watch` workflow runs the same probe every five minutes and can post failures to Slack when `SLACK_ALERT_WEBHOOK_URL` is set. Keep the external monitor provider as the primary pager because GitHub-hosted scheduled jobs can be delayed during platform incidents.

GitHub repository secrets currently needed for Slack/Railway log alerts:

- `SLACK_ALERT_WEBHOOK_URL`
- `RAILWAY_TOKEN`
