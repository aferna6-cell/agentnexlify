# Owner-Action Runbook - Remaining Launch Items (2026-06-23)

Copy-paste tasks for the owner-gated launch items. No code work left in these.
Each item has steps the owner runs in a dashboard plus a **DONE-WHEN** acceptance bar.

Source: `audits/audit-launch-readiness-2026-06-23.md`. Env-var locations verified
against `railway.json`, `backend/config.py`, `.github/workflows/railway-error-watch.yml`,
`.github/workflows/public-uptime-watch.yml`.

Order by impact: insurance flips the go/no-go gate; the rest close score gaps.

---

## 0. Insurance quote - the go/no-go gate (rubric 10.6)

This is the only HIGH-severity zero. The launch score already clears the 210
threshold (221/262). This single item flips NO-GO to GO. No repo work exists.

Steps:
1. Call an insurance broker. Ask for two quotes: **E&O (errors and omissions /
   professional liability)** and **cyber liability**.
2. Describe the business: multi-tenant SaaS, AI chat widget on small-business
   sites, stores leads and appointment data, processes payments via Stripe.
3. Get the premium numbers in writing (email or PDF).

**DONE-WHEN:** a written E&O + cyber quote exists with a premium figure. Save the
PDF to `docs/ops/` or note the number in the launch tracker.

---

## 1. Repoint agentnexlify.com + www to the live Vercel project

The public domain is attached to the stale `agentnexlify-site` Vercel project.
Edits to `landing-page-v2` deploy to the `agentnexlify` project but do NOT reach
the live domain until the domains move. Source: `CLAUDE.md` directory WARNING.

### Step 1 - check the live project first (do this before moving anything)
1. Vercel dashboard, open the `agentnexlify` project.
2. Settings, Deployment Protection: confirm production is **not** password /
   auth-protected. If it is, turn protection off for production (or set it to
   preview-only). A protected prod URL serves a login wall to visitors.
3. Deployments tab: confirm the latest production deploy status is **Ready**, not
   **Blocked** or **Error**. If BLOCKED, check Settings, Usage / spend limits and
   the billing page. Clear the limit, then redeploy.
4. Open the project's `*.vercel.app` production URL in a private window. Confirm
   the live landing page renders with no login wall.

Do not move the domain until step 1 passes. Moving a domain onto a blocked or
auth-walled project takes the public site down.

### Step 2 - move the domains
1. Vercel dashboard, open `agentnexlify-site` (the stale project), Settings, Domains.
2. Remove `agentnexlify.com` and `www.agentnexlify.com` from `agentnexlify-site`.
3. Open the `agentnexlify` project, Settings, Domains, Add Domain.
4. Add `agentnexlify.com`. Set `www.agentnexlify.com` to redirect to the apex (or
   the reverse, matching current setup). Vercel shows the required DNS records.
5. If DNS is at Vercel already, records auto-apply. If DNS is external (Cloudflare
   or registrar), update the A / CNAME records Vercel shows.
6. Wait for Vercel to show **Valid Configuration** on both domains (DNS can take
   minutes to a few hours).

### Step 3 - verify
1. Private window, open `https://agentnexlify.com` and `https://www.agentnexlify.com`.
2. Confirm both load the current `landing-page-v2` content, HTTPS valid, no login wall.
3. Confirm `www` redirects to apex (or apex to `www`, per your choice) cleanly.

**DONE-WHEN:** `agentnexlify.com` and `www` both serve the live `landing-page-v2`
content over valid HTTPS, with no auth wall, from the `agentnexlify` project.

---

## 2. Set the env-var secrets

Four secrets across two surfaces. Exact names verified in repo. Do not commit any
of these values; they live only in the dashboards below.

| Secret | Goes in | Read by | Verified location |
|--------|---------|---------|-------------------|
| `VOYAGE_API_KEY` | Railway (backend service env) | KB embeddings | `backend/config.py:122`, `backend/services/embeddings.py:37` |
| `SENTRY_DSN` | Railway (backend service env) | error capture | `backend/config.py:56`, `backend/main.py` Sentry init |
| `RAILWAY_TOKEN` | GitHub repo secret | error-watch workflow | `.github/workflows/railway-error-watch.yml:55` |
| `SLACK_ALERT_WEBHOOK_URL` | GitHub repo secret | error-watch + uptime workflows | `railway-error-watch.yml:56`, `public-uptime-watch.yml:36` |

### 2a. VOYAGE_API_KEY (Railway backend env) + KB backfill

`VOYAGE_API_KEY` powers semantic-search embeddings (`voyage-3-lite`, 512-dim). With
it missing, new KB articles store a null vector and semantic search is degraded.

1. Get a key from voyageai.com (dashboard, API Keys).
2. Railway dashboard, open the backend service, Variables tab.
3. Add `VOYAGE_API_KEY` = the key. Save. Railway redeploys the service.
4. Confirm the backend came back up: `GET /api/health` returns 200.
5. Run the full backfill so existing articles get embeddings (not just new ones):
   ```
   /kb-compile --full
   ```
   This regenerates all embeddings. Source: `.claude/skills/kb-compile/SKILL.md:25`.
6. Spot-check with `/kb-query` on a known topic; confirm relevant articles return.

**DONE-WHEN:** `VOYAGE_API_KEY` is set on Railway, `/api/health` is 200, the
`/kb-compile --full` backfill finished, and `/kb-query` returns relevant hits.

### 2b. SENTRY_DSN (Railway backend env)

Sentry init is code-complete; it activates only when the DSN is present.

1. sentry.io, create (or open) a project for the FastAPI backend.
2. Project Settings, Client Keys (DSN): copy the DSN string.
3. Railway dashboard, backend service, Variables: add `SENTRY_DSN` = the DSN. Save.
4. After redeploy, check `GET /api/health` (or `/readyz`) reports
   `sentry_configured: true`.
5. Optional sanity check: trigger a test error and confirm it lands in Sentry.

**DONE-WHEN:** `SENTRY_DSN` is set on Railway and the health endpoint reports
`sentry_configured: true`.

### 2c. RAILWAY_TOKEN + SLACK_ALERT_WEBHOOK_URL (GitHub repo secrets)

These power the hourly Railway error-watch and the 30-minute public uptime watch.
Both workflows exit silently (no alert) until both secrets exist.

1. Railway: account, Tokens, create a project/account token. Copy it.
2. Slack: create an Incoming Webhook for the alert channel
   (api.slack.com/apps, your app, Incoming Webhooks). Copy the webhook URL.
3. GitHub repo, Settings, Secrets and variables, Actions, New repository secret:
 - `RAILWAY_TOKEN` = the Railway token.
 - `SLACK_ALERT_WEBHOOK_URL` = the Slack webhook URL.
4. Actions tab: run `railway-error-watch` manually (Run workflow) and confirm it
   no longer prints the "skipping scan" notice.
5. Confirm a test message reaches the Slack channel (the uptime probe posts on a
   simulated failure, or watch the next scheduled run).

**DONE-WHEN:** both GitHub secrets exist, `railway-error-watch` runs without the
"not set, skipping" notice, and a test alert reaches the Slack channel.

---

## 3. Log retention 30+ days (rubric 4.5)

Railway keeps logs ~7 days by default. The backend already emits structured JSON
logs (`backend/main.py` JsonFormatter). The gap is a log sink with 30+ day
retention, fed by a Railway log drain. Pick one option below.

### Option A - BetterStack (Logtail) - recommended for free-tier 30-day
1. betterstack.com, Logs, create a source of type "HTTP" (or "Vercel/Railway"
   if shown). Copy the ingest URL / token it gives.
2. Confirm the plan retains logs 30+ days (BetterStack free tier covers a 3-day
   default; pick a paid tier or a plan whose retention is 30+ days before relying
   on it for the rubric).
3. Railway dashboard, backend service, Settings, Log Drains (or Observability,
   Drains): add an HTTP drain pointing at the BetterStack ingest URL.
4. Generate traffic (hit `/api/health` a few times). Confirm log lines appear in
   BetterStack within a minute.

### Option B - Axiom - generous free retention
1. axiom.co, create a dataset. Settings, API Tokens: create an ingest token.
2. Axiom's ingest endpoint is `https://api.axiom.co/v1/datasets/<dataset>/ingest`.
   Confirm the dataset retention is 30+ days on your plan.
3. Railway, backend service, Log Drains: add an HTTP drain to the Axiom ingest URL
   with the token in the auth header (Axiom docs show the exact header).
4. Verify log lines land in the Axiom dataset.

### Option C - Logtail/Datadog/Papertrail (if already used elsewhere)
Same shape: create a log source, get the ingest URL, add it as a Railway HTTP log
drain, confirm 30+ day retention on the plan, verify ingestion.

**DONE-WHEN:** a Railway log drain forwards backend logs to a sink whose plan
retains them 30+ days, and a fresh log line is visible in that sink.

---

## 4. Backup restore drill (rubric 6.1)

Logical restore mechanics were already verified (`docs/ops/restore-drill-2026-06-10.md`).
What remains is one managed-backup restore into a scratch project, without touching
prod. Supabase project ref: `pxserpybmajixqrmzaly`.

Steps (10 minutes, dashboard only):
1. supabase.com/dashboard, project `pxserpybmajixqrmzaly`, Database, Backups.
2. Confirm a recent daily backup or PITR window exists. Screenshot the timestamp.
3. Take the current production counts for comparison (run in the SQL editor on prod):
   ```sql
   SELECT
     (SELECT count(*) FROM tenants)       AS tenants,
     (SELECT count(*) FROM leads)         AS leads,
     (SELECT count(*) FROM chat_messages) AS chat_messages;
   ```
4. Use **Restore to a new project** (point-in-time or daily backup). Do NOT restore
   over production. This spins up a separate scratch project.
5. In the restored scratch project's SQL editor, run the same count query.
6. Compare counts to the production numbers from step 3. They should match (allow
   for rows written between the snapshot time and step 3).
7. Delete the scratch project (it bills hourly).

**DONE-WHEN:** a managed backup was restored to a scratch project, row counts match
production within the snapshot window, the scratch project is deleted, and the
restore is logged (append a dated entry to `docs/ops/restore-drill-2026-06-10.md`
or a new dated drill doc).

---

## Quick checklist

- [ ] 10.6 Insurance: written E&O + cyber quote
- [ ] Domains: agentnexlify.com + www serve live landing-page-v2 from `agentnexlify` project
- [ ] `VOYAGE_API_KEY` on Railway + `/kb-compile --full` backfill done
- [ ] `SENTRY_DSN` on Railway, health reports sentry_configured: true
- [ ] `RAILWAY_TOKEN` + `SLACK_ALERT_WEBHOOK_URL` GitHub secrets, alerts reach Slack
- [ ] 4.5 Log drain to a 30+ day sink, ingestion verified
- [ ] 6.1 Managed-backup restore to scratch project, counts match, scratch deleted, logged
