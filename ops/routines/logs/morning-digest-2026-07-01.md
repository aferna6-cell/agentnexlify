# Morning Digest — 2026-07-01

*Auto-generated. Caveman-mode. Log: `ops/routines/logs/morning-digest-2026-07-01.md`*

---

## Commits (last 24h)

- `b3a3bbe` — brain: scheduled refresh from GitHub + Supabase
- `8a3b071` — subconscious: run 2026-07-01 — Zapier plan_status enforcement (GH #107)
- `ff9e867` — ops: nightly-commit-review 2026-07-01
- `c3298be` — subconscious: run 2026-06-30-pm — SMS Compliance Dashboard (run 74 escalation)
- `6bec066` — ops: morning-digest 2026-06-30

**5 commits. 0 product code. 5 ops/planning. Zero features shipped in 24h. 3+ days of no production commits.**

---

## Issues Opened / Updated (24h)

- **#385** — Add SMS Compliance Dashboard (OPEN, filed by nightly 2026-07-01)
  - 10+ days overdue. Paste-ready code in `subconscious/runs/2026-06-30-pm/winning-concept.md`.
  - Labels: `backend`, `frontend`, `nightly-review`, `medium-risk`
  - GH issue activates issue-to-pr-loop autonomous path.
- **#384** — Morning digest 2026-06-30 (OPEN, informational)

---

## Open PRs Needing Action

| # | Title | Age | Action |
|---|-------|-----|--------|
| #383 | Dependabot: react-router-dom 7.18.0 | 2d | Merge (patch) |
| #382 | Dependabot: jsdom 29.1.1 | 2d | Merge (dev) |
| #381 | Dependabot: @playwright/test 1.61.1 | 2d | Merge (dev) |
| #380 | Dependabot: eslint 9.39.4 → **10.6.0 MAJOR** | 2d | Read changelog first |
| #341 | KB: drift sweep | 9d | Review/merge or close |
| #328 | Billing: save-offer before cancel | 13d | Needs migration 160 check |
| #372 | Referral reward: $20 credit to referrer | 8d | DRAFT — blocked on referral infra |
| #281 | Dependabot: @vitest/coverage-v8 4.1.9 | 16d | Merge (dev) |
| #279 | Dependabot: vitest 4.1.9 | 16d | Merge (dev) |
| #86 | fix(hooks): 4 missing post-edit checks | **67d** | Close or schedule |

**10 open PRs. #86 is 67 days stale — needs decision. #380 eslint major — verify no breaking config changes.**

---

## Subconscious — Run 75 Winner

**Zapier plan_status enforcement in `_get_api_key_client`**

- Category: code_health / security
- Effort: S (~30 min)
- Confidence: HIGH
- AUTONOMOUS-EXECUTABLE: YES — moratorium override (zero human queue impact)
- GH #107, open 62 days in `bug-patterns.md`

**What it fixes:** Cancelled and past-due tenants can currently authenticate Zapier API calls after their subscription ends. Two files:
1. `backend/services/zapier_auth.py` — add `plan_status IN ('active','trialing')` check after API key resolution
2. `backend/tests/test_zapier_plan_status.py` (new) — 4 regression tests

Full code sketch: `subconscious/runs/2026-07-01/winning-concept.md`

**Run 75 governance:** SMS Dashboard (#385) now in `pending_autonomous` via issue-to-pr-loop. Subconscious pivoted to 62-day revenue/security debt.

---

## Signals / Flags

- **Widget drift #378** — 8th consecutive invariant failure. HUMAN ONLY. 30-second fix:
  ```bash
  cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
  git add landing-page-v2/widget/agentnexlify-widget.js
  git commit -m "fix: sync widget to landing-page-v2 (resolves invariant FAIL)"
  git push
  ```
- **KB cron** — `knowledge-base/log.md` last entry: 2026-05-05. KB fix `65284cc` shipped but no new log entry confirms cron is running. Verify: `tail -5 knowledge-base/log.md`
- **SMS Dashboard** — 10+ days unimplemented. Run 74 delivered paste-ready code. Issue-to-pr-loop activated via #385.
- **Home.jsx (1006L) + email_sequences.py (1143L)** — two god classes in parking lot. Unblock after Zapier + SMS ship.

---

## Top 3 Priorities Today

1. **Zapier plan_status enforcement** — 62-day revenue/security bug. 30 min. Code in `subconscious/runs/2026-07-01/winning-concept.md`. No schema change, no migration. `AUTONOMOUS-EXECUTABLE`.

2. **Widget drift** — 8 days of invariant failure. 30 seconds. One `cp` command above. **Human only** (landing-page-v2 is forbidden for autonomous systems).

3. **SMS Compliance Dashboard** — 10+ days overdue. Full paste-ready code in `subconscious/runs/2026-06-30-pm/winning-concept.md`. 30-min execution. Now also routed via issue-to-pr-loop #385.

---

*Next check: `/evening` or tomorrow 08:00 via cron.*
