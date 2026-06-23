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

## Related
- [[Paid Launch Readiness]] · [[Paid Launch Readiness Pack]] · [[Autonomous Dev Operation]]
