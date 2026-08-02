# Improvement Backlog — Run 101 Update
**Date:** 2026-08-02-pm

## THIS RUN — Approved for execution
- [ ] **Step 9G: KB self-healing trigger** — Add to `.claude/skills/nightly-commit-review/SKILL.md`. XS effort. Closes KB self-repair gap. See `winning-concept.md`.

## READY (next 1-3 runs)
- [ ] **Connector token expiry health check (Step 9H candidate)** — Nightly scan of `gmail_integrations` + `connector_registry` for tokens last_refreshed >30d. Requires schema-guardian verify of actual column names first. S effort.
- [ ] **Social publisher post-delivery receipt** — `social_posts.delivery_status` column + `send_owner_push` on failure. Requires migration. S effort. Let social_publisher.py bake in prod first (land after 2026-08-09).

## BACKLOG (valid, lower priority)
- [ ] **Inbox triage AI cost guard** — Plug `inbox_triage.py` into `ai_usage_guard.PLAN_BASELINE_TOKENS`. S effort. Revisit after 1-2 weeks of production inbox data (earliest: 2026-08-16).
- [ ] **PWA install prompt in dashboard** — `usePWAInstall` hook + install banner. M effort. customer_value category. Route through compound-engineering pipeline with human approval.

## FROZEN (do not re-propose)
- `ai_human_handoff` — frozen per governance.json

## RETIRED THIS RUN
- None — no new retirements.
