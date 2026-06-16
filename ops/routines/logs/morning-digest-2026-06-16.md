# Morning Digest — 2026-06-16

> Caveman mode. Bullets. No fluff.

---

## Commits (last 24h) — 11 landed

- `ff2ca28` Gate signup behind payment; grandfather existing tenants (#291)
- `f67fd42` Reprice competitor-comparison landing pages to two-plan model (#290)
- `98a935f` Security/drift follow-ups: admin-secret, XFF key, OAuth rate limits, audit_log, field-def fix (#289)
- `9bed342` Reprice to two plans (Chatbot $19.99 / Agent OS $99.99) + usage caps + buy-more-usage (#288)
- `ded0c3d` docs: auto-log bug fix from cc1bd4a
- `cc1bd4a` Launch hardening: sign support-chat sessions + cap cost (#287)
- `bec069d` Platform support channels: Agent OS alerts, support form email, support widget (#285)
- `38f92c3` chore(deps): bump dompurify 3.4.0 → 3.4.10 (#276)
- `8bc9d98` feat(frontend): integration-keys settings page + API client (#139 slice)
- `702379e` chore(deps-dev): bump @playwright/test 1.59.1 → 1.60.0 (#164)
- `42c7a43` feat(integrations): tenant integration-keys API + provider health checker (#132)

Heavy day: repricing shipped, payment gate live, support infra up.

---

## Issues — opened/updated

### Bugs (nightly-review, from repricing)
- **#293** MEDIUM: `orchestrator.py` + `billing_reconciliation.py` use stale plan names after reprice — `agent_os` misses branded email; reconciliation caps wrong for `chatbot`/`agent_os`
- **#292** MEDIUM: `sms_rate_limiter` + `api_key_auth` missing new plan names (`chatbot`/`agent_os`)

### Critical / Blocking
- **#263** CRITICAL: 24 pending migrations unsynced (schema-sync, updated 2026-06-15) — **needs apply**
- **#266** security: integrations-secret encryption incomplete — backfill + sunset plaintext still open
- **#265** deps: fastapi capped at <0.136 (starlette 0.50 blocker)

### Old / Stalled
- **#217** Stripe Connect self-serve — BLOCKED on billing-architecture decision
- **#193** Subconscious moratorium: 13 items, oldest 44 days
- **#114/#128/#143** Pending migrations 118/119/122 — `ai-ready`, stalled

---

## Open PRs needing action

| # | Title | Age |
|---|-------|-----|
| #286 | feat(os+support): Agent OS fail/abstain alerts + email-routed support form | 1d |
| #282 | chore(deps): stripe <12,>=11 → >=15.2.1,<16 | 1d |
| #283 | chore(deps): uvicorn 0.34 → 0.49 | 1d |
| #284 | chore(deps): python-jose >=3.3 → >=3.5 | 1d |
| #275 | chore(deps): react 18.3.1 → 19.2.7 (frontend) | 1d |
| #274 | chore(deps): react-dom 18.3.1 → 19.2.7 (frontend) | 1d |
| #279–281 | demo-platform: vitest + react bumps | 1d |

**#286** is the only real-code PR — review + merge. Dep bumps are Dependabot; react 18→19 is a **major version jump**, needs manual verification before merge.

---

## Subconscious recommendation

**Run 2026-06-13 (HIGH confidence):** Sync `landing-page-v2/widget/agentnexlify-widget.js` with `widget/agentnexlify-widget.js` — PR #254 updated widget + public copy but missed landing-page-v2. Single `cp` command. Clears CLAUDE.md Critical Invariant #4 (byte-identical widget copies).

Run 2026-06-12: Add pre-commit Check 13 blocking `from __future__ import annotations` in backend/ — 4 infected files after PR #238 auth split.

---

## Top 3 priorities today

1. **Fix plan-name stale refs** — #293 + #292. Two MEDIUM bugs from yesterday's reprice. `orchestrator.py:238,319` needs `agent_os` in branded-email gate; `billing_reconciliation.py:35-49` + `sms_rate_limiter` + `api_key_auth` need `chatbot`/`agent_os` entries. Fast fix, ships clean repricing story.

2. **Review + merge #286** — Agent OS fail/abstain alerts + support form. 1 day old, real feature, unblocked.

3. **Execute subconscious widget sync** — `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`. Single command. Clears invariant #4. Nightly has been flagging this since PR #254.

---

## Watch list

- **#263 (24 pending migrations)** — schema is drifting. Apply or triage before adding more.
- **react 18→19 Dependabot PRs** (#274/#275/#278/#280) — major version bump; test before merge.
- **KB log** — last compile 2026-04-30; embeddings failing (no Voyage key in cron env). Not urgent today but stale.

---

*Generated: 2026-06-16 | Source: git log + GitHub issues/PRs + subconscious/runs/2026-06-13*
