# Morning Digest — 2026-09-16

Generated: 2026-09-16 UTC | Auto-routine

---

## Commits (last 24h)

- `5f4c631` docs(nightly): review 2026-09-16 [auto-nightly]

1 commit. Nightly review auto-commit only. No feature work landed overnight.

---

## Issues Opened / Updated (last 24h)

| # | Title | Status | Labels |
|---|-------|--------|--------|
| #875 | fix(billing): 40 functions call AI without metering guard — #871 closed but violations persist | OPEN NEW | ai-ready, nightly-review, billing |
| #403 | Set ANTHROPIC_API_KEY in GitHub Actions secrets — blocks autopilot loop AND KB autopopulate | OPEN | critical, human-action-required, ops |
| #800 | Brain connector 44 days stale — last run 2026-07-23 | OPEN | human-action-required, brain-connector |

**Notable:**
- #875 is new today — nightly review found that #871 (billing metering fix) did NOT close all 40 unguarded AI call sites. Violations persist.
- #403 and #800 are long-standing human-action-required blockers. GH Actions still has no API key. Brain connector still dead (54+ days now).

---

## Open PRs Needing Action

| # | Title | Age | State | Note |
|---|-------|-----|-------|------|
| #874 | subconscious: run 121 — Step 9E credential expiry escalation (2nd carry-forward) | 1d | DRAFT | Needs undraft + merge — carry-forward 2, autonomous-exec at run 122 |
| #870 | [security] 90+ backend routers missing Depends(block_demo_role) | P1 | OPEN issue | Corresponding PR needed |
| #864 | chore(deps): update mcp >=2.2.0,<3 in /backend | 2d | open | Dependabot, review + merge |
| #863 | chore(deps): bump react-dom 18→19 in /demo-platform | 2d | open | Dependabot, needs testing |
| #861 | chore(deps): bump react 18→19 in /demo-platform | 2d | open | Dependabot, needs testing |
| #860 | chore(deps): bump react 18→19 in /frontend | 2d | open | Dependabot — React 19 breaking changes, careful |
| #859 | chore(deps-dev): bump vitest 4→5 in /frontend | 2d | open | Dependabot, low risk |

**React 19 upgrade warning**: PRs #860 and #863 bump React 18→19. React 19 has breaking changes (ref as prop, removed forwardRef, changed Suspense behavior). Do NOT merge without running frontend build + E2E smoke.

---

## Subconscious Recommendation

**Run 120 (2026-09-11-pm)**: Step 9E credential expiry escalation — earlier warning + GH issue filing.
- AUTOPILOT_GH_TOKEN: was 69 days old on Sep 11 → now ~74 days old today (threshold 76d, rotation interval 90d, expires **~2026-10-02 — 16 days away**).
- Current Step 9E: logs warning only. Does NOT file GH issue. No email/assignee. Explains why 3 consecutive nightlies logged warnings with zero human action.
- PR #874 carries the fix. 2nd carry-forward. Autonomous-executable at run 122 (tomorrow).
- **Recommendation: Rotate AUTOPILOT_GH_TOKEN today.** Do not wait for automation.

---

## Top 3 Priorities Today

### 1. ROTATE AUTOPILOT_GH_TOKEN — 16 days left, loop dies if missed
- Token expires ~2026-10-02. 74 of 90 days since last rotation.
- If it expires: nightly-commit-review, issue-to-pr-loop, autonomous engineering loop all stop.
- Open: GitHub → Settings → Developer Settings → Personal Access Tokens → rotate.
- Then update `ops/credential-rotation-schedule.md` + add to GH #399 comment.

### 2. Fix issue #875 — 40 unguarded AI call sites still live after #871
- Nightly found #871 closed but violations persist. 40 production call sites calling Claude API without `ai_usage_guard` check.
- Real cost risk: any tenant on free plan can burn unbounded tokens via these paths.
- ai-ready label = autonomy can pick this up, but needs a human to confirm scope first.

### 3. Merge PR #874 and triage React 19 dep bumps
- #874 (subconscious Step 9E fix) is DRAFT — undraft and merge to unblock autonomous escalation at run 122.
- React 19 PRs (#859–863): run `cd frontend && npm run build` against each before merging. Vitest 5 (#859) is lowest risk, start there.

---

## Blockers (human-required, no automation fix)

- #403: `ANTHROPIC_API_KEY` missing from GH Actions secrets → KB autopopulate + autopilot loop broken since Jul 9
- #800: Brain connector dead since Jul 23 → brain/Maps/ stale 54+ days
- #399: AUTOPILOT_GH_TOKEN expired or near-expiry → autonomous loop degraded

All three require owner action in GitHub UI or secrets management. Cannot be resolved by any routine.

---

## KB Status

Last autopopulate: **2026-08-26**. 21 days stale (blocked by missing ANTHROPIC_API_KEY in GH Actions, per #403).
Manual trigger available: `bash scripts/daily/kb-autopopulate.sh` (requires local env with valid API keys).
