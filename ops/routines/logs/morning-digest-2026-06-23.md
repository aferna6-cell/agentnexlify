# Morning Digest — 2026-06-23

Generated: 2026-06-23 UTC | Caveman mode.

---

## Commits (last 24h) — 10 landed

- `4660771` docs(launch): close rubric 9.5 + remaining-work owner punch-list (#351)
- `4c19f1d` docs: triage all 48 open PRs with gated execution plan (#350)
- `c461cef` refactor(plans): wire every premium gate to plan_catalog — kill drift bug class (#349)
- `8445bf8` ci: cut Actions minute burn below free tier; document zero-minute gate (#348)
- `63cd035` fix(rate-limit): current paid plans no longer fall back to free-tier cap (#347)
- `d1ec148` docs: correct stale facts across live/authoritative docs (#346)
- `3d4c7db` plan-catalog: canonical plan sets + drift-guard test; migration triage (#344)
- `2dfd480` Merge PR #343 (agent-nexlify-testing)
- `4b4999b` brain: add source-backed second-brain vault + agent-first wiring
- `8c33d1e` ops: morning-digest 2026-06-22

**Signal:** Heavy docs + plan-catalog day. Rate-limit fix (#347) + plan_catalog drift-guard (#349) likely address #292/#293 — but issues still OPEN on GH. Needs close.

---

## Open PRs Needing Action

| # | Title | Status |
|---|-------|--------|
| #333 | main-pending: 51 commits — billing repricing, AI Workforce, Conversations | 🔴 NEEDS MERGE DECISION |
| #328 | Billing: save-offer step before cancel (retention) | open |
| #327 | AI Workforce: upgrade prompt on 402 | open |
| #325 | Checkout fixes: kill Stripe Link emails + land paid customers on dashboard | open |
| #341 | kb: drift sweep 2026-06-22 | open |
| #286 | Agent OS fail/abstain alerts + email-routed support | open |
| #342 | chore: bump vitest 4.1.8→4.1.9 | dep bump — auto-merge candidate |
| #340 | chore: bump @typescript-eslint/parser 8.58→8.61 | dep bump — auto-merge candidate |
| #284 | chore: update python-jose ≥3.3.0 | dep bump |
| #283 | chore: bump uvicorn 0.34→0.49 | dep bump — MAJOR bump, needs test |

**Priority action:** #333 is a 51-commit mega-branch. Decide: merge or split into smaller PRs.

---

## Issues — Open / Needs Action

### Critical / Blocking
- **#263** 🔴 Schema Sync CRITICAL: 24 pending migrations — still open, stale
- **#329** Apply migration 154 (conversation sentiment + intent) to production — NOT applied
- **#330** Human legal review: TermsOfService section 4 — **needs human, not Claude**

### Close candidates (likely fixed by today's commits)
- **#292** sms_rate_limiter + api_key_auth missing chatbot/agent_os — `63cd035` + `c461cef` likely fix. **Close if confirmed.**
- **#293** orchestrator + billing_reconciliation stale plan names — same fix batch. **Close if confirmed.**

### High priority
- **#266** security: finish integrations-secret encryption — backfill + sunset
- **#265** deps: re-raise fastapi <0.136 cap (starlette blocked)
- **#217** Stripe Connect: BLOCKED on billing-arch decision
- **#193** Moratorium active: 13 pending items, oldest 44+ days — needs triage pass

### Old migration issues (stale, needs audit)
- **#114, #128, #130, #143** — migrations 118/119/121/122, all old. Check if applied; close if so.

---

## Subconscious (latest: Run 64 — 2026-06-20-pm)

**Winner:** Fix #292/#293 — wire chatbot/agent_os into plan-name dicts (sms_rate_limiter, api_key_auth, billing_reconciliation).

**Status:** Commits `63cd035` + `c461cef` landed 2026-06-23 and appear to cover this. Subconscious last ran 2026-06-20 — 3 days stale. Alternating mandate loop (#308 ↔ #292/#293) should resolve once GH issues closed.

**Unresolved from subconscious:** #308 (webhook idempotency early-write) still not fixed per last run. `idempotency.py` still needs `delete_key` + stripe_webhooks exception-path cleanup. ~20 min, human approval required.

---

## KB / Automation Health

- **KB log:** Last entry 2026-05-05 — **7 weeks stale**. Autopop cron not running (network sandbox + no VOYAGE_API_KEY in cron env).
- **Subconscious:** Last run 2026-06-20-pm — 3 days stale. Expected daily.
- **Embeddings:** Supabase MCP unauthorized errors persist across multiple log entries. 4+ articles in wiki/ not upserted to kb_articles.

---

## Top 3 Priorities Today

1. **Merge or split #333** — 51-commit pending branch is the largest risk surface. Either merge main-pending → main or break into smaller PRs. Blocking everything downstream.

2. **Close #292/#293** — verify commits `63cd035`/`c461cef` cover the plan-name dict fixes; close issues if confirmed. Clears the subconscious alternating-mandate loop.

3. **Apply migration 154** (#329) — conversation sentiment + intent columns blocked in production. Low risk, high value.

---

*Next: Fix #308 (webhook idempotency) — 20 min, human approval needed. Sketch in `subconscious/runs/2026-06-20/winning-concept.md`.*
