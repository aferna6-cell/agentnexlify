# Morning Digest — 2026-07-09

Generated: 2026-07-09 UTC (automated routine)

---

## Commits (last 24h) — 5 commits

- `17714e3` brain: scheduled refresh from GitHub + Supabase
- `5f841e6` subconscious: run 2026-07-09 — Add proactive credential rotation tracking (Step 9E)
- `e8b2ddc` ops: nightly-commit-review 2026-07-09
- `774ef80` subconscious: run 83 (2026-07-08-pm) — Add issue-to-pr-loop health check to nightly Step 9D
- `1e4e56b` ops: morning-digest 2026-07-08

**Automation pipeline healthy — nightly review + subconscious runs + brain sync all fired.**

---

## Issues — Open blockers (human-action-required)

| # | Title | Labels | Age |
|---|-------|--------|-----|
| **#399** | autopilot-issue-loop GH Actions failing 5+ days — AUTOPILOT_GH_TOKEN expired | `human-action-required` `operational` | NEW today |
| **#394** | Fix brain-refresh[bot] credentials (GitHub 403 + SUPABASE_ACCESS_TOKEN missing) | `human-action-required` | Day 8 |
| **#393** | CRITICAL: ops/monitoring/healthz-alert.sh missing — 3rd consecutive miss [P0] | `human-action-required` | 4d |
| **#391** | P0: Set SLACK_ALERT_WEBHOOK_URL in Railway — healthz alerts currently silent | `human-action-required` `critical` `blocker` | 6d |
| **#392** | Brain refresh connectors failing 4+ consecutive days (GitHub 403, Supabase token) | `nightly-review` `ops` | 4d |
| **#388** | DOWNTIME: public uptime probe failing | `critical` `uptime` | 7d |

**CRITICAL: 4 human-action-required issues open. Pipeline partially dead.**

---

## Issues — Feature queue

| # | Title | Status |
|---|-------|--------|
| **#385** | Add SMS Compliance Dashboard (backend + frontend) | `ai-ready` — queued 8+ days, BLOCKED (autopilot loop dead, see #399) |
| **#377** | fix: sync widget to landing-page-v2 mirror | `bug` — open 12d |
| **#378** | Widget drift: landing-page-v2 out of sync | `nightly-review` — open 10d |

---

## Open PRs needing action

| # | Title | Age | Action |
|---|-------|-----|--------|
| **#387** | brain: sync Maps to 2026-07-01 reality + widget drift fix | 8d | DRAFT → promote + merge |
| #396 | bump @typescript-eslint/parser 8.62.0→8.62.1 | dep | batch-merge |
| #383 | bump react-router-dom 7.17.0→7.18.0 | dep | batch-merge |
| #382 | bump jsdom 29.0.2→29.1.1 | dep | batch-merge |
| #381 | bump @playwright/test 1.61.0→1.61.1 | dep | batch-merge |
| #380 | bump eslint 9.39.4→10.6.0 | dep | batch-merge |
| **#372** | Referral reward: $20 credit to referrer on first paid invoice | 15d | DRAFT — needs review |
| #281 | bump @vitest/coverage-v8 4.1.8→4.1.9 | 23d | batch-merge |
| #279 | bump vitest 4.1.8→4.1.9 | 23d | batch-merge |
| #86 | fix(hooks): add 4 missing post-edit checks from harness audit | 74d | DRAFT — stale, review |

**10 open PRs. #387 ready to ship. 7 Dependabot bumps — batch-merge to clear.**

---

## Subconscious (runs 83–84)

**Run 84 (2026-07-09 AM) — WINNER: Step 9E proactive credential rotation**
- Recommendation: Add Step 9E to nightly SKILL.md + create `ops/credential-rotation-schedule.md`
- Step 9E reads rotation schedule, computes days since last rotation, files `credential-rotation` GH issue if any credential is within 14 days of 90-day expiry window
- Root cause: AUTOPILOT_GH_TOKEN + brain PAT both expired same day (2026-07-04) — simultaneous two-system kill
- Steps 9B/9C/9D are reactive; Step 9E is first proactive monitor in the system
- Confidence: HIGH | Effort: S | Autonomous-executable: YES
- **Parallel human action required first**: #399 (rotate AUTOPILOT_GH_TOKEN, 5 min) + #394 (rotate brain PAT + set SUPABASE_ACCESS_TOKEN, 7 min)

**Run 83 (2026-07-08-pm) — WINNER: Step 9D issue-to-pr-loop health check**
- Recommendation: Add Step 9D to nightly — detect stalled ai-ready issues (no PR after 24h) + check autopilot-issue-loop.yml last-run timestamp
- Status: EXECUTED (commit `774ef80`) — nightly now monitors loop dormancy

---

## Top 3 priorities for today

### 1. URGENT (5 min): Rotate AUTOPILOT_GH_TOKEN — #399
- autopilot-issue-loop dead for 5+ days, 30 ai-ready issues stalled
- Go to GitHub → Settings → Developer Settings → Personal access tokens → regenerate
- Add new token to GitHub Secrets as `AUTOPILOT_GH_TOKEN`
- Update `ops/credential-rotation-schedule.md` (new today) after rotation

### 2. URGENT (7 min): Rotate brain PAT + set SUPABASE_ACCESS_TOKEN — #394
- Brain data stale 8+ days; brain connector failing with GitHub 403
- Rotate GitHub PAT used by `brain/_tools/refresh_connectors.py`
- Set `SUPABASE_ACCESS_TOKEN` in Railway Variables (currently missing)
- Closes #394 and unblocks brain sync + subconscious run quality

### 3. Promote + merge PR #387
- brain: sync Maps to 2026-07-01 reality — draft for 8 days, verified work
- Closes widget drift issues #377 + #378
- After merge: batch-merge Dependabot bumps (#279, #281, #380, #381, #382, #383, #396)

---

## KB status

Last compile: 2026-05-05 (63 days stale). KB autopopulate migration to GitHub Actions recommended by subconscious run 82 — not yet implemented. Embeddings also blocked by missing SUPABASE_ACCESS_TOKEN (same as #394).

---

_Next: Fix #399 + #394 → unblocks autopilot loop → #385 SMS Dashboard ships autonomously_
