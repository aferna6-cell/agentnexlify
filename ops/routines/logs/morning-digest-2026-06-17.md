# Morning Digest — 2026-06-17

> Caveman mode. Bullets. No fluff.

---

## Commits (last 24h) — 17 landed

- `bc91e97` ops: nightly-commit-review 2026-06-17
- `25d5aac` Update brand tagline to "Your hardest working employees that don't stop" (#307)
- `c03df18` Recolor floating CTA from black to brand blue (light-theme fix) (#306)
- `529dd7b` Refresh link-preview OG card to AI Workforce positioning (#305)
- `021e245` Landing redesign + AI Front Desk / AI Workforce repositioning (#304)
- `ac8ac3b` Profit-guarantee usage caps + $24.99 usage pack (#303)
- `9c4cc5e` docs: auto-log bug fix from cd284ba
- `cd284ba` Fix pricing cards leaving empty space on wide screens (#302)
- `47c7f8b` Launch retention + security hardening: dunning recovery, trial countdown, conversion funnel, webhook fixes (#301)
- `d500044` docs: auto-log bug fix from 34b9d0f
- `34b9d0f` Launch hardening: trial-end access contract, dunning recovery fix, trial banner, flaky-test fix (#300)
- `379b230` Growth monetization: 7-day trial, activation funnel event, owner paid-signup alert (#299)
- `1e7e4c9` Reconcile free-chatbot funnel to the two-plan (paid) model (#298)
- `e994349` Home.jsx: remove "2-Minute Setup" from Chatbot pricing CTA (#297)
- `3123da0` Home.jsx: two-plan pricing (Chatbot $19.99 / Agent OS $99.99) (#296)
- `007ef5d` Launch readiness: webhook-race hardening + paid-signup smoke + pricing sweep (#295)
- `81df6b2` subconscious: run 2026-06-16 (run 58) — Wire check_project_invariants.py into pre-commit as Check 13

Heavy sprint: landing redesign, AI Workforce repositioning, trial + retention infra, profit-guarantee usage caps all shipped.

---

## Issues — opened/updated (last 24h)

### NEW — opened today
- **#308** `bug billing nightly-review` — **MEDIUM: Webhook idempotency early-write drops events on handler failure**
  - Idempotency row written BEFORE handler completes. Handler fails → row exists → Stripe retry skipped → tenant stays locked forever even after card fixed.
  - Files: `idempotency.py:85-93`, `billing.py:233-236`, `stripe_webhooks.py:64-66`
  - Introduced by: `47c7f8b` (yesterday's launch hardening)
  - Fix: Option A — delete idempotency row on exception before raising 500 (no schema change)

### Still open from yesterday
- **#293** `bug medium-risk nightly-review` — orchestrator + billing_reconciliation use stale plan names
  - `orchestrator.py:238,319` — `agent_os` tenants never get branded email (gate is `professional`/`enterprise` only)
  - `billing_reconciliation.py:35-49` — `chatbot`/`agent_os` not in plan cap dicts → audit reports wrong caps
- **#292** `bug medium-risk nightly-review` — sms_rate_limiter + api_key_auth missing new plan names
  - `sms_rate_limiter.py:10` — new tenants capped at 50 SMS/day (both plans hit the floor)
  - `api_key_auth.py:29` — `chatbot`/`agent_os` tenants get 402 on Zapier settings page
  - Decision needed: should `chatbot` be SMS-unlimited? Zapier on both plans or agent_os-only?

### Chronic / watch
- **#266** security: integrations-secret encryption backfill + plaintext sunset — OPEN
- **#265** deps: fastapi capped at <0.136 (starlette 0.50 blocker) — OPEN
- **#263** CRITICAL: 24 pending migrations unsynced — OPEN, schema drifting

---

## Open PRs needing action

| # | Title | Age | Action |
|---|-------|-----|--------|
| #286 | feat(os+support): Agent OS alerts + email support form | 2d | Review + merge — only real-code PR |
| #284 | chore(deps): python-jose >=3.5 | 2d | Safe merge |
| #283 | chore(deps): uvicorn 0.34 → 0.49 (15 major versions) | 2d | Check changelog, then merge |
| #282 | chore(deps): stripe >=15.2.1,<16 | 2d | Safe merge |
| #275 | chore(deps): react 18→19 frontend | 2d | MAJOR — needs manual test before merge |
| #274 | chore(deps): react-dom 18→19 frontend | 2d | MAJOR — bundle with #275 |
| #280 | chore(deps): react 18→19 demo-platform | 2d | Minor risk (demo only) |
| #278 | chore(deps): react-dom 18→19 demo-platform | 2d | Minor risk (demo only) |
| #281 | chore(deps-dev): vitest bump | 2d | Safe |
| #279 | chore(deps-dev): vitest bump (demo) | 2d | Safe |

React 18→19 on `/frontend` (#274/#275) is production — do not merge without full dashboard smoke test.

---

## Subconscious recommendation

**Run 58 (2026-06-16) — HIGH confidence:** Wire `check_project_invariants.py` into pre-commit as Check 13.
- All 6 invariant classes now passing cleanly.
- Mechanism proven (Check 11 + 12 landed autonomously same way).
- 6-line bash block, zero false positives on current codebase.
- **AUTONOMOUS-EXECUTABLE** — nightly can apply this tonight.

**Run 57 (2026-06-13) — still pending:** `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js` — widget drift from PR #254 unresolved, Critical Invariant #4 still failing.

---

## Top 3 priorities today

1. **Fix #308 (BILLING BUG)** — Webhook idempotency early-write. Payment recovery events silently dropped = tenants permanently locked after fixing card. Option A fix in `idempotency.py`/`billing.py`/`stripe_webhooks.py`, add regression test. Narrow blast radius now, catastrophic if ignored.

2. **Fix #292 + #293 (NEW TENANT BREAKAGE)** — Stale plan names block new signups: SMS hard-capped, Zapier returns 402, branded email skipped for `agent_os`. Fast fixes (2–4 lines each). Decide: Zapier on both plans or agent_os-only? SMS chatbot capped or unlimited?

3. **Widget sync + Check 13 gate** — `cp widget/ → landing-page-v2/` (1 line, run 57). Then wire Check 13 into pre-commit (6 lines, run 58). Both AUTONOMOUS-EXECUTABLE tonight if not done manually.

---

## Watch list

- **React 18→19 PRs (#274/275)** — production breaking change, test dashboard before merge
- **uvicorn 0.34→0.49 (#283)** — 15 versions, verify no ASGI contract breaks
- **#263 (24 pending migrations)** — schema still drifting, apply before next backend sprint
- **KB embeddings** — failing since ~2026-04-30 (no Voyage key in cron env), 50+ articles unembedded

---

*Generated: 2026-06-17 | ops/routines/logs/morning-digest-2026-06-17.md*
