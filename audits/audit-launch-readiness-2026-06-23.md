# Launch-Readiness Zero-Map Audit — 2026-06-23

Maps every rubric criterion currently scoring **0** to a concrete buildable task
with exact in-repo file targets, effort, dependencies, and a hard split between
**"engineer builds in-repo"** vs **"owner does in a dashboard"**.

Source rubric: `planning/launch-readiness-rubric.md` (last scored 2026-06-10 PM,
**221/262 = 84.4%**, verdict **NO-GO solely on one HIGH-severity zero: 10.6
insurance**). Prior sweep: `audits/audit-launch-readiness-2026-06-15.md`.

> Key correction to the `brain/` summaries: the brain notes call 4.2 (Sentry),
> 4.3 (uptime), 4.5 (log retention) "zeros." In the **live rubric** 4.2 and 4.3
> are already scored **1** (partial — code shipped, owner account/secret pending),
> not 0. The only true rubric **0s** are: **4.5, 7.5, 8.5, 9.5, 10.6.** Items at
> score 1 are listed below the zero table because they share the same owner-gated
> shape and are the cheapest path to raising the weakest dimension (Observability).

---

## THE ONE HARD BLOCKER (owner-only, not buildable)

| # | Criterion | Severity | Why it blocks | Owner action |
|---|-----------|----------|---------------|--------------|
| **10.6** | Insurance (E&O / cyber) quoted | **HIGH (dim 10)** | Rubric go-rule: any HIGH-dim 0 = NO-GO regardless of total. Score 221 ≥ 210 threshold; this single item flips NO-GO → GO. | **Aidan/partner phone call** to a broker (E&O + cyber). ~1 hour. No repo work exists or is possible. |

Nothing in this repo can clear 10.6. Every other zero below is non-fatal to the
go/no-go gate (none are in HIGH dims 2/3/10 except 10.6) but each closes score gap.

---

## RUBRIC ZEROS — full map

| # | Criterion | Dim (sev) | Current state in repo | Concrete task | Owner-gated? | Effort |
|---|-----------|-----------|------------------------|---------------|--------------|--------|
| **4.5** | Log retention ≥ 30 days | 4 Observability (w2) | **Missing.** Railway default 7d. No log sink. Structured JSON logs already emitted (`backend/main.py:124-128` JsonFormatter; request log line `main.py:800-811`). No drain configured. | **Engineer (small):** add a log-drain forwarder config + doc. **Owner (account):** provision a sink (BetterStack/Axiom/Logtail free tier ≥30d) and set the Railway log-drain URL. Code side is just env wiring + a doc; the retention itself is the sink account. | **Mostly owner** (account + Railway drain). Engineer: tiny doc + optional env var. | **S** |
| **7.5** | Status page exists | 7 Support (w1) | **Was missing → PARTIAL now.** No customer-facing page existed (`/health` was JSON-only, dev-facing). **This audit scaffolded** a public `/status` HTML page + `/status.json` (see below). status.agentnexlify.com DNS still unset. | **DONE in-repo (this audit):** `backend/routers/status_page.py` serves `/status` (HTML) + `/status.json`, reusing live health probe. **Owner:** (optional) CNAME `status.agentnexlify.com` → the app, or adopt a hosted product (Statuspage/BetterUptime) and point it at `/status.json`. | **Split** — page built; DNS/hosted-product = owner. | **S (done)** |
| **8.5** | Case study / design-partner logo | 8 Brand (w1) | **Missing.** 5 testers (MTOptions top), no public writeup. Help page has a "How we compare" section but no logo strip/case study. | **Engineer (small):** add a logo-strip / case-study block to `frontend/src/pages/Home.jsx` once content exists. **Owner/partner:** get MTOptions consent + write the case-study copy + supply logo asset. | **Mostly owner** (consent + content). Engineer build is trivial once copy exists. | **S** (blocked on content) |
| **9.5** | Cold-outreach templates + partner assignment | 9 Sales (w1) | **Missing.** No template set or assignment rules. `outreach/` dir exists (`outreach/email-infra-setup.md`) but no templates. | **Owner/partner (content):** write outreach templates + assignment rules. **Engineer (optional):** drop them in `outreach/templates/` as markdown. | **Owner** (sales content, partner scope). | **S** |
| **10.6** | Insurance quoted | 10 Risk (w2, **HIGH**) | **Not buildable.** See hard-blocker section above. | Phone a broker. | **Owner only** | n/a |

---

## ADJACENT SCORE-1 ITEMS (not zeros, but same owner-gated shape — cheapest dimension lift)

Observability (dim 4) is the weakest engineering dimension. These are already
**code-complete at score 1**; they need an owner secret/account to reach 2.

| # | Criterion | Repo state (verified) | Remaining to reach score 2 | Owner-gated? | Effort |
|---|-----------|------------------------|----------------------------|--------------|--------|
| 4.1 | Error alerts < 5 min | `.github/workflows/railway-error-watch.yml` polls Railway logs hourly → Slack; `scripts/monitoring/railway-error-to-slack.sh`. Exits 0 silently without secrets. | Owner sets repo secrets `RAILWAY_TOKEN` + `SLACK_ALERT_WEBHOOK_URL`. | **Owner** (2 secrets) | S |
| 4.2 | Sentry captures unhandled exc | **Code-complete.** `backend/main.py:135-146` inits Sentry when `settings.sentry_dsn` set; `config.py:56 sentry_dsn`; `sentry_sdk` in `backend/requirements.txt`; `/health` + `/readyz` report `sentry_configured`. | Owner sets `SENTRY_DSN` on Railway (Sentry project OAuth/DSN). No code work. | **Owner** (1 env var) | S |
| 4.3 | External uptime monitor, SLO ≥ 99.5% | `.github/workflows/public-uptime-watch.yml` probes 4 prod endpoints every 30 min (`scripts/monitoring/public_uptime_probe.py`, config `ops/monitoring/uptime-checks.json`); auto-files `uptime`-labeled GH issue on failure. | Owner sets `SLACK_ALERT_WEBHOOK_URL`; for score-2 SLO history, adopt UptimeRobot/BetterUptime pointed at `/api/v1/healthz` or new `/status.json`. | **Owner** (secret + optional hosted monitor) | S |
| 6.1 | Backup restore verified | Logical drill done (`docs/ops/restore-drill-2026-06-10.md`). | Owner runs one Supabase dashboard PITR restore into a scratch project; document it. | **Owner** (dashboard) | M |
| 10.4 / 10.5 | Bus-factor / dead-man switch | Runbooks exist (`docs/ops/service-continuity-plan.md`, `partner-runbook.md`). | Credential distribution + real partner rehearsal. | **Owner/partner** | M |

---

## WHAT I BUILT THIS SESSION (in-repo, additive, new file only)

**New customer-facing status page (closes 7.5 in-repo half):**
- `backend/routers/status_page.py` — **new file.** Serves:
  - `GET /status` — public HTML status page (dark theme, no auth, no tenant
    scope, no DB writes). Live Supabase connectivity reflected as
    Operational/Degraded; returns 503 when degraded.
  - `GET /status.json` — machine-readable status for external monitors / embeds.
  - Reuses the exact Supabase probe pattern from `main.py:health()` so the page
    and JSON health agree. No new dependencies. No `from __future__` annotations.
- `backend/main.py` — **two one-line registrations only:** added `status_page`
  to the `from backend.routers import (...)` tuple and
  `app.include_router(status_page.router)`. No other edits to existing routers.

Verification: `ast.parse` clean on both files; import added to existing router
tuple; registration line matches sibling routers. Full app import not run here
(would need the prod env/deps), CI + `/healthz` will confirm on deploy.

This does NOT close 7.5 to a "2" by itself — score 2 wants a hosted/branded
status surface or `status.agentnexlify.com`. It removes the "no status page
exists at all" zero and gives the uptime monitor (4.3) a clean public JSON
target.

---

## RANKED BUILDABLE LIST (engineer effort, by leverage)

1. **7.5 status page — DONE in-repo this session** (S). Owner: optional DNS/hosted product.
2. **4.5 log retention** (S) — engineer adds Railway log-drain env wiring + a
   short ops doc; **owner provisions the sink account** and sets the drain URL.
   Without the sink account there is nothing more to build.
3. **8.5 case study block** (S) — trivial `Home.jsx` logo-strip/case-study
   section, **blocked on partner content + MTOptions consent.**
4. **9.5 outreach templates** (S) — markdown drop into `outreach/templates/`,
   **owner-authored content (sales/partner scope).**

There is no large (L) engineering task among the zeros. The remaining gap is
overwhelmingly **account provisioning and partner content**, not code.

---

## OWNER-GATED LIST (no repo work clears these)

| Item | Owner action | Dashboard |
|------|--------------|-----------|
| **10.6 insurance** (the gate) | Get E&O + cyber quote | Broker phone call |
| 4.5 log sink | Provision ≥30d log sink, set Railway log-drain URL | BetterStack/Axiom/Logtail + Railway |
| 4.1 error alerts | Set `RAILWAY_TOKEN` + `SLACK_ALERT_WEBHOOK_URL` | GitHub repo secrets |
| 4.2 Sentry | Set `SENTRY_DSN` | Railway env + Sentry |
| 4.3 uptime SLO | Set `SLACK_ALERT_WEBHOOK_URL`; optional hosted monitor on `/status.json` | GitHub secret / UptimeRobot |
| 7.5 status DNS | CNAME `status.agentnexlify.com` or hosted status product | Vercel/DNS / Statuspage |
| 8.5 case study | MTOptions consent + write copy + logo asset | partner |
| 9.5 outreach | Author templates + assignment rules | partner |
| 6.1 restore | One Supabase PITR restore drill into scratch project | Supabase |
| 10.4/10.5 | Credential distribution + partner rehearsal | partner |

---

## Bottom line

- **Go/no-go is gated entirely by 10.6 (insurance) — a phone call only Aidan/partner can make.** Score already clears the 210 threshold.
- The "infra zeros" from the brain summary are **mostly already built**: Sentry init, 4 health/readiness endpoints, uptime probe workflow, Railway error watch, structured JSON logging all ship today. They sit at score 1 awaiting **owner secrets**, not code.
- The only genuine in-repo gap (no customer-facing status surface) is now scaffolded as a new `/status` page.
- Net engineering work remaining across all zeros: **near-zero** — everything left is owner account-provisioning or partner-authored content.
