---
type: map
name: "Open Loops"
tags:
  - map
  - moc
last_updated: 2026-06-22
---

# Open Loops

Unfinished work + blockers (business scope). Ordered by priority.

## High
- ~~[[Insurance Quote for Launch]]~~ — **DONE 2026-06-23 (owner).** The single HIGH rubric zero is cleared → launch verdict flips NO-GO → GO. Remaining launch items are MEDIUM/owner-content (log sink 4.5, case study 8.5, outreach 9.5).
- [[Align Pricing Across Surfaces]] — owner decision + alignment pass (G5).
- [[Convert Beta Tenants to Paid]] — revenue priority (led by [[MTOptions]]).
- ~~[[Weekly Value Digest]]~~ — G2 retention lever. **Shipped 2026-06-23**: the Friday emailer already existed; added dollar-framed estimated pipeline `$`, configurable `avg_lead_value` (graceful when column absent, no migration), conversations count, + 23 tests. `backend/services/weekly_value.py` + `scheduled_jobs_ext.py`.

## Medium
- [[Connect Public Domain]] — repoint agentnexlify.com to the live Vercel project.
- [[Proactive AI Opportunities Job]] — nightly proactive suggestions (G7).

## Infra / hygiene (from sources, not yet broken out)
- Log retention/sink, uptime monitor, status page, Sentry OAuth (rubric). Source: [[planning-launch-readiness-rubric]]
- OAuth creds pending: Google Business Profile, social, real SERP. Source: [[eng-memory-blocked-items]]
- Untracked deps (no requirements.txt entries) — reproducibility risk. Source: [[eng-memory-blocked-items]]

## From GitHub (smoke pass 2026-06-22, corrected 2026-06-23)
- **#263 — RESOLVED 2026-06-23. Prod schema drift = 0.** The "24 pending" was a false count (005/007 duplicate-numbered files + unreliable history table). Real pending was 2; both applied to prod via `apply_migration` (project pxserpybmajixqrmzaly): `117_zapier_api_keys` + `129_chat_messages_os_mirror`, all 6 objects verified live. Migration 154 was already applied. Source: `audits/audit-schema-drift-2026-06-23.md` + `docs/dev-knowledge/schema-log.md`.
- **#329 — DONE.** Migration 154 (conversation sentiment + intent) confirmed already live in prod (`conversations.sentiment`/`intent` exist, verified 2026-06-23).
- **#330** — human legal review of TermsOfService §4 (payment terms).
- **#266** — finish integrations-secret encryption (backfill + sunset plaintext).
- KB embeddings broken since ~2026-04-30: root cause = missing `VOYAGE_API_KEY` (owner-gated) **plus** no graceful degradation in `backend/services/embeddings.py:34,52,70` (hard 401 raise) + the cron compile path swallows the crash as success. Code patch drafted (not applied). Source: `audits/audit-kb-embeddings-2026-06-23.md`
- Recently fixed overnight: #308 (webhook idempotency), #292/#293 (stale plan names).

## Review 2026-06-23 — 4-lane foundation/launch pass
- **Launch rubric correction:** `brain/Projects/Paid Launch Readiness.md` mislabeled Sentry (4.2) + uptime (4.3) as zeros — both already **scored 1** in `planning/launch-readiness-rubric.md` (code shipped: Sentry `main.py:135-146`, uptime workflow + probe; only owner secrets pending). Real rubric **0s = 4.5 log retention, 7.5 status page, 8.5 case study, 9.5 outreach, 10.6 insurance**.
- **7.5 status page — built 2026-06-23**: new `backend/routers/status_page.py` (`/status` + `/status.json`, no auth/no tenant scope, 503 when degraded). Gives the uptime monitor a clean public JSON target.
- Remaining buildable zeros are owner-gated content/secrets: 4.5 needs a log-sink account, 8.5 needs partner+MTOptions consent, 9.5 is owner-authored sales copy.
- Source: `audits/audit-launch-readiness-2026-06-23.md`

## Review 2026-06-23 (round 2) — money-path + moat hardening
Theme: launch is gated by the owner insurance call; engineering de-risks the beta→paid conversion path + the KB moat so nothing breaks on conversion day.
- **#93 money-path bug — ALREADY FIXED on this branch (verified 2026-06-23).** `guard_checkout_for_fraud` already exempts `payment_status=no_payment_required` (100%-off coupon / comped $0 checkout) — `backend/services/fraud_guard.py:122-128`, regression test `test_allows_no_payment_required`, 16/16 pass. No net change needed; GitHub issue #93 can be closed. **Watch-out:** comped checkout sessions must carry the `plan` key in Stripe metadata or `_handle_checkout_completed` silently no-ops the upgrade.
- **KB embeddings — code half DONE.** `backend/services/embeddings.py` now raises typed `EmbeddingUnavailable` on missing key (no doomed 401), 13 tests. Still owner-gated: set `VOYAGE_API_KEY` in Railway + `/kb-compile --full` backfill, AND guard the cron snippet in `.claude/skills/kb-compile/SKILL.md:104-115` with `try/except EmbeddingUnavailable` (SKILL.md = owner edit). Until the SKILL guard lands the cron still skips embeddings, but now fails observably, not as a 401 swallowed-as-success.
- **Reproducibility — 3 untracked deps pinned** in `backend/requirements.txt` (authoritative per railway.json→Dockerfile): **PyYAML** (was a module-level `import yaml` reachable from boot → clean Railway deploy would CRASH AT STARTUP), `qrcode[pil]`, `python-dateutil`. Source: `audits/audit-untracked-deps-2026-06-23.md`.
- **G5 pricing alignment — DONE (2026-06-23).** `landing-page-v2/index.html` swept to chatbot $19.99 / agent_os $99.99. Audited `frontend/src`: live conversion surfaces ALREADY correct (`SignupPage.jsx`, `wizard/WizardStepPlan.jsx`, `TidioAlternative.jsx` all state $19.99/$99.99 + no free tier). Fixed gating copy in `MessagingSettingsCards.jsx`: "Professional plan" → "Agent OS plan" (Professional is retired-from-sale legacy; live-answering gate unlocks on agent_os). Competitor prices + widget JS untouched; invariants pass.
- **OWNER DECISION NEEDED — trial UI vs the killed-trial decision.** `frontend/src/components/StripeTrialBanner.jsx` (`plan_status==="trialing"`, "card charged when trial ends") + the legacy free `TrialBanner` in `App.jsx` (`plan==="free"`) still render 7-day-trial messaging, but [[Decision Log]] has "Kill Trial Charge On Signup" — which itself was "reversed #299" once. Whether tenants still enter `trialing` is a Stripe-config + backend `plan_status` question; NOT safe to blind-edit. Decide: are paid trials live or dead? If dead, remove both banners + the `trialing` UI path.

## Review 2026-06-23 (round 3) — owner-gated action pass
Owner cleared #1 (insurance) + is setting env-var secrets (#2). I did the doable parts of 3/4/5/6:
- **#4 prod migrations — DONE** (117+129 applied, drift=0; see #263 line above).
- **#3 + #6 owner runbooks/drafts written** (turn owner-only items into copy-paste tasks): `docs/launch/owner-action-runbook-2026-06-23.md` (DNS repoint, the 4 secrets + which surface each lives on, log-sink + Railway log-drain for 4.5, Supabase restore drill 6.1), `outreach/templates/cold-outreach-templates.md` (9.5 — 3 verticals, $19.99, placeholders), `docs/launch/case-study-template.md` (8.5 — needs MTOptions consent + real numbers). All em-dash-clean, correctly priced, no fabricated metrics.
- **#5 money-path safety — in progress** (`backend/routers/billing.py`): make a comped/`no_payment_required` checkout with no resolvable `plan` fail LOUD (logged/alerted), not silently no-op. Observability only, no activation-behavior change; billing → owner review before merge.
- Still irreducibly owner-only: DNS repoint, secret values, log-sink account, case-study consent + numbers, outreach send config, the trials live/dead decision, convert-beta sales motion.

## Dependency Reduction — reduce external-secret surface (analysis 2026-06-23)
Goal: fewer external API keys to set/own. Each env-var the owner must provision is a failure point + a launch chore. Code-side reductions (deterministic-first, CLAUDE.md):
- **Voyage embeddings → OPTIONAL.** `kb_articles.content` (migration 081) exists; add a Postgres FTS column (`to_tsvector`) + GIN index + an FTS path in the KB retrieval helper. KB retrieval then works with ZERO external embedding API; embeddings become a recall enhancement when `VOYAGE_API_KEY` is present. Removes the moat's hard dependency on Voyage. Biggest win; pairs with the graceful-degradation already shipped. (S/M)
- **Slack alerts → Resend email.** `SLACK_ALERT_WEBHOOK_URL` is only used in CI monitoring (`scripts/monitoring/railway-error-to-slack.sh`, `railway-error-watch.yml`). Email infra (`owner_alerts.py`/`platform_mailer.py`/Resend) is already core. Route the alert to owner email; drop the Slack secret + integration. Solo founder, no Slack team. (S)
- **Sentry → optional + self-hosted fallback.** `SENTRY_DSN` already guarded (no-op when unset). Log-sink (4.5) + structured JSON logs cover most error visibility; optionally add a lightweight `error_events` Supabase table as a zero-dependency fallback. Keep Sentry optional. (S, low priority)
- **RAILWAY_TOKEN → app self-report.** `railway-error-watch.yml` polls the Railway API for errors. Alternative: app pushes errors to Supabase + the watcher queries the public `/status.json` + Supabase instead of the Railway API. Removes a CI secret. (M, lower priority — CI infra)

### Highest-value next items I can complete (code/docs)
1. Finish KB cron guard — `.claude/skills/kb-compile/SKILL.md` try/except EmbeddingUnavailable (closes the embeddings-resilience loop; mine to do). (S)
2. Voyage-optional: Postgres FTS fallback for KB retrieval (dependency reduction #1 above). (S/M)
3. Slack → Resend owner-email alert path (dependency reduction #2). (S)
Owner-only (unchanged): trials live/dead decision, env-var values, DNS, log-sink, case-study consent, convert-beta.

### BUILT 2026-06-23 (all 4 dependency-reduction lanes shipped to branch / PR #358)
- **L1 KB cron guard** — `.claude/skills/kb-compile/SKILL.md` catches `EmbeddingUnavailable`. DONE.
- **L2 Voyage-optional FTS** — `migrations/155_kb_articles_fts.sql` (content_tsv + GIN + `match_kb_articles_fts` RPC) + `_query_kb_articles` embedding→FTS fallback in `widget_chat_helpers.py` + 9 tests. **Follow-ups:** apply 155 to prod (owner/approved); the helper is built+tested but NOT yet wired into the live widget retrieval path (separate integration, touches `widget_chat.py` hot path).
- **L3 Slack→Resend email** — `scripts/monitoring/send-alert-email.sh` + both monitoring workflows swapped off Slack; also fixed a real latent bug (uptime probe exit swallowed by `| tee` → downtime alert was dead). **Owner:** add `RESEND_API_KEY` + `OWNER_ALERT_EMAIL` GitHub secrets, delete `SLACK_ALERT_WEBHOOK_URL`.
- **L4 Sentry-optional** — `migrations/156_error_events.sql` + `error_events.py` + wired into existing `global_error_handler` + 6 tests. **Follow-up:** apply 156 to prod (owner/approved).
- **Net:** required external secrets 4 → 1 (RESEND only), and **`RESEND_API_KEY` is already configured — DONE (confirmed by owner 2026-06-23)**. So the core path needs ZERO new external keys; Voyage + Sentry are now optional enhancements only. Remaining (non-secret) follow-ups: apply prod migrations 155 + 156 (owner-approved), wire FTS into the widget hot path, and confirm the monitoring workflows can read `RESEND_API_KEY` + `OWNER_ALERT_EMAIL` as GitHub Actions secrets (app env already has the Resend key; Actions secret store is separate).

## Business-level (GTM) highest-value — the constraint is now distribution (2026-06-23)
Product is live + works (7 paid tenants, moat wired, retention loops running). The binding constraint is no longer product quality, it is **distribution + activation** (only 12 tenants total). Highest-value business levers:
1. **Funnel visibility / instrumentation (I can build).** No analytics today — signup→activate→first-lead→paid→retained is invisible. Build an internal funnel/cohort metrics view so optimization stops being guesswork. Highest leverage: makes every later decision data-driven.
2. **Activation speed / onboarding-v2 (I can build).** The onboarding-v2 epic (#128-142, vertical presets + wizard) is frozen. A new tenant should get a vertical-tuned widget live in minutes. Faster activation = more beta→paid.
3. **Distribution (mostly owner / partial me).** Public site not live (DNS repoint = owner), outreach templates drafted-but-unsent (owner), SEO + programmatic per-vertical landing pages untapped (I can build the SEO/landing side).
4. **Referral loop (I can build, cheap + compounding).** The widget "Powered by AgentNexLiFy" watermark sits on every tenant site = a free distribution surface. Make it a real referral/attribution link.
Owner-only GTM: DNS repoint, send outreach, sales calls (convert-beta via MTOptions).

## Prod data snapshot (2026-06-23, project pxserpybmajixqrmzaly)
- 12 tenants (7 paid), **2,717 chat_messages**, **27 leads**, **9 appointments**, 16 kb_articles (all embedded).
- Read: the product is LIVE and used, not pre-launch theory. The funnel `2717 messages → 27 leads → 9 appointments` is the value chain — improving chat→lead→booking conversion is now the highest-value product lever (it's literally the product's job). The KB moat content is THIN (16 global articles; per-tenant depth is the `widget.knowledge_base` config) → G8 vertical depth matters.

### Next highest-value (data-grounded, 2026-06-23)
1. **Lead-capture + booking conversion audit/improve** — verify the widget actually extracts a lead + offers booking at the right moments across the 2717 messages; fix any leak. Core revenue lever. (`tenant-chatbot-audit` skill; `_extract_lead_info`, booking flow)
2. **KB content depth (G8)** — 16 global articles is shallow; build per-vertical KB packs for the top-PMF industries (salon, plumber/HVAC, dental) so the moat actually answers.
3. ~~**Ship it**~~ — **DONE: PR #358 MERGED to prod 2026-06-23 (merge sha e85b73f).** 15 commits live on main (auto-deploy Railway+Vercel): KB moat wiring (widget retrieves tenant KB), value digest hardening, billing fixes (fraud-guard comp path + comp-activation alerting), dependency reduction (FTS/email/error-sink), status page, schema audits. Migrations 117/129/154/155/156 all applied to prod. Next product work lands in a follow-up PR off the same branch.
4. **G3 voice/phone live-answering** — partly built; competitors answer phones.

## Product activation — highest-value next (analysis 2026-06-23)
Launch-hardening is done; the bottleneck is now beta→paid conversion, which depends on the product visibly DELIVERING value. Highest-value buildable items:
- **Activate the vertical-KB moat in the widget (the differentiator).** `_query_kb_articles` (semantic + FTS fallback, built in L2) exists in `widget_chat_helpers.py` but is NOT called from `backend/routers/widget_chat.py` — the widget answers customers without retrieving the tenant KB. Wire it into the chat path (behind a flag, feed into `_build_system_prompt`, graceful-empty), apply migration 155. This is the moat going live. The single highest-value product change.
- **G7 proactive opportunities — ALREADY LIVE (verified 2026-06-23; gap-analysis G7 note is STALE).** `run_opportunity_scan` runs every 30 min (`main.py:421`, daily-gated per tenant, per-tenant failure isolated), `compute_suggestions` serves `GET /api/v1/os/insights` (`os_insights.py:30`), and `frontend/src/components/os/OsInsightsCard.jsx` renders the suggestions on the dashboard. No work needed. G7 = done.
- **Value digest is LIVE + hardened (2026-06-23).** `send_weekly_digest` targeting fixed to `plan != 'free' AND plan_status IN ('active','trialing')` (was missing the status filter → would have emailed cancelled/paused tenants); per-tenant work now isolated (one crash can't abort the batch); `empty_state_message()` gives zero-activity tenants a "here's what your AI is ready to do" message instead of a zeros table. 23 dollar-math tests still green.
- **Migrations 155 + 156 — APPLIED to prod 2026-06-23** (project pxserpybmajixqrmzaly): `kb_articles.content_tsv` + GIN + `match_kb_articles_fts` (155), `error_events` table + index (156). All 5 objects verified live. FTS path + error sink active in prod; the moat goes fully live when the widget-wiring lane merges.
- Bigger bets (gap analysis): G3 voice/phone live-answering (partly built — `voice_ai_enabled`, `calls.py`, `propose_appointment`), G8 vertical-pack depth beyond top-5 industries.

## Related
- [[Paid Launch Readiness]] · [[Paid Launch Readiness Pack]] · [[Autonomous Dev Operation]]
