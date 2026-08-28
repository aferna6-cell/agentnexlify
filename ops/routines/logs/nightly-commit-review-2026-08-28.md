# Nightly Review — 2026-08-28

## Commits reviewed (last 24h)

| SHA | Message | Risk |
|-----|---------|------|
| 245dacf | ops: morning-digest 2026-08-27 | LOW |
| e21e7ee | ops: correct step 9J in nightly-commit-review 2026-08-27 [auto-nightly-2026-08-27] | LOW |
| 7df3205 | ops: nightly-commit-review 2026-08-27 | LOW |

**Note:** Session started in detached HEAD state. Fixed via `git checkout main && git pull origin main --rebase` before analysis.

All 3 commits are ops/logs only. No production code changes.

## Findings

### Fixed autonomously (0)
None. No LOW-risk bugs in production code.

### Issues opened (0)
None. All open concerns tracked in existing issues (see extended checks).

### Skipped
- FORBIDDEN paths: none touched
- Guardrails: not triggered (0 production files changed)

## Extended Checks

### Step 9A — Moratorium
`moratorium_active: false` — skip. 1 pending_approval item (below >3 threshold).

### Step 9B — Healthz Monitor
`ops/monitoring/healthz-alert.sh` exists — monitoring active, skip.

### Step 9C — Brain Connector Health
Last successful run: 2026-07-23T14:38Z → **36 days stale** (threshold: 14 days).
INGESTION-LOG shows consecutive `skipped — SUPABASE_ACCESS_TOKEN not set` entries prior to 2026-07-23.
- Open issue #684 exists (escalated yesterday with 35-day count).
- **Added comment to #684** with updated 36-day count + action steps. ✓
- No new issue (duplicate of #684).

**Step 9C: brain connector 36 days stale — comment added to #684.**

### Step 9D — Issue-to-PR Loop Health
3 open `ai-ready` issues, all stalled (>24h, no directly-linked open PR):
- #643 (2026-08-07, 21 days old) — appointment_briefs.py security
- #660 (2026-08-15, 13 days old) — scoring_config.py block_demo_role
- #669 (2026-08-20, 8 days old) — 95 routers missing block_demo_role

PR search for #643 returned #575, #626, #653 — none are implementation PRs for #643.
Loop dormancy already flagged in yesterday's report. No new issue created (duplicate concern).
**Step 9D: 3 ai-ready issues, all stalled, loop health unknown — no new issue (already tracked).**

### Step 9E — Credential Rotation
Schedule: `ops/credential-rotation-schedule.md` ✓

| Credential | Last rotated | Days since | Status |
|------------|-------------|-----------|--------|
| AUTOPILOT_GH_TOKEN | 2026-07-04 (est.) | ~55 days | OK (< 76) |
| Brain connector GitHub PAT | 2026-07-04 (est.) | ~55 days | OK (< 76) |
| SUPABASE_ACCESS_TOKEN | unknown | N/A | Unknown — tracked in #684 |

**Step 9E: 2 credentials checked, 0 approaching expiry, 1 unknown state.**

### Step 9F — KB Autopopulate Staleness
Last KB log entry: 2026-08-26 19:28 → **2 days ago**. PASS (< 7 days). No action.

### Step 9G — KB Autopopulate Self-Healing
Step 9F clean — skip.

### Step 9I — Demo-Role Security Sweep
114 router files contain mutating endpoints. No new router files added in last 24h.
Existing violations tracked in:
- #669 (95 routers, class-wide issue) — open, ai-ready
- #660 (scoring_config.py) — open, ai-ready
**Step 9I: 114 files scanned, 0 new violations, 0 new issues filed (existing #669, #660 still open).**

### Step 9J — Dependabot Auto-Merge
Checked 3 highest-priority Dependabot PRs:
- #679 — eslint 10.7→10.9: `mergeable_state: unknown` — skip
- #666 — @typescript-eslint/parser 8.64→8.67: `mergeable_state: unknown` — skip
- #629 — @playwright/test 1.61.1→1.62.1: `mergeable_state: unknown` — skip

20+ Dependabot PRs open total. All checked return `unknown` (GitHub hasn't recomputed mergeability for stale-base PRs). Skill requires `"clean"` — 0 merged.
**Step 9J: 3 PRs checked (#679, #666, #629), all `mergeable_state: unknown`, 0 merged.**

## Next actions

- **Brain connector (#684)**: NEEDS HUMAN — rotate GitHub PAT + set SUPABASE_ACCESS_TOKEN in Railway (36 days stale, comment added).
- **ai-ready loop (#643, #660, #669)**: 3 security issues, all stalled, no linked PRs. Human should check loop health or manually prioritize — #643 is 21 days old.
- **Dependabot PRs**: 20+ open, all `mergeable_state: unknown`. Trigger rebase via @dependabot comment or merge manually after CI passes.
- All clear on production code commits from last 24h.
