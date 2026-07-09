# Run 79 Winner: Fix Brain Connector Credentials — GitHub 403 + SUPABASE_ACCESS_TOKEN Missing

**Date:** 2026-07-05  
**Category:** operational  
**Effort:** XS (GH issue + human: ~7 min)  
**Autonomous:** MANDATE EXECUTION (P0 GH issue + Step 9B added to nightly SKILL.md this run)  
**Confidence:** HIGH  
**Evidence source:** `ops/routines/logs/nightly-commit-review-2026-07-05.md` — MEDIUM finding, 4 consecutive days

---

## Problem

Brain connector failure — 4 consecutive days (2026-07-01 through 2026-07-04):
- **GitHub connector:** `HTTP Error 403: Forbidden` every day — token expired or scope revoked
- **Supabase connector:** `skipped — SUPABASE_ACCESS_TOKEN not set` — env var missing from cron environment
- **Brain refresh result:** `brain/INGESTION-LOG.md` shows only bot metadata updates — no actual issue/PR/schema data synced since 2026-07-01
- **Impact:** `brain/Maps/Home.md`, open issues, PR state, DB schema decisions all stale. All autonomous agents (subconscious, nightly-commit-review, issue-to-pr-loop) operating on degraded context.

First detection by subconscious analysis. Runs 77+78 did not inspect `brain/INGESTION-LOG.md`. The failure went unnoticed for 4 days — no alert pathway existed.

---

## Mandate Execution This Run (governance-required, pre-winner)

Run 79 mandate fires per run 78 winning-concept.md `run_79_mandate` field:
> "If `ops/monitoring/healthz-alert.sh` still NOT present after next nightly run: Escalate to P0 GH issue with `critical` + `blocker` labels. Tag human in issue. No further automated mandate."

**Autonomous actions executed this run:**
1. **Step 9B added** to `.claude/skills/nightly-commit-review/SKILL.md` — AUTONOMOUS-EXECUTABLE (run 78 winner, already approved). Future nightlies will write `healthz-alert.sh` automatically from embedded script content in `subconscious/runs/2026-07-03/winning-concept.md §Script Content`.
2. **P0 GH issue filed** for `ops/monitoring/healthz-alert.sh` missing — critical + blocker labels, human tagged. Mandate chain closed. No further automated mandate for this item.
3. **GH issue filed** for `SLACK_ALERT_WEBHOOK_URL` human setup — per run 78 winning-concept.md §Human Step.

---

## Winner Recommendation: Fix Brain Connector Credentials

### Root cause

1. **GitHub connector (HTTP 403):** Token used by `brain-refresh[bot]` expired or had scope revoked. `brain/_tools/refresh_connectors.py` authenticates against GitHub API with a PAT. 403 = auth failure (not rate limit — rate limit returns 429).
2. **Supabase connector (token missing):** `SUPABASE_ACCESS_TOKEN` env var not present in the cron/scheduler environment where `brain/_tools/refresh_connectors.py` runs.

### Fix steps (human action required, ~7 min total)

**Step 1: Rotate GitHub token (5 min)**
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new classic token with scopes: `repo` (read), `issues` (read)
3. Check `brain/_tools/refresh_connectors.py` for the env var name it reads (likely `GITHUB_TOKEN` or `BRAIN_GITHUB_TOKEN`)
4. Update the token in cron environment:
   - Railway: Project → Variables tab → update token env var
   - GitHub Actions: Settings → Secrets → update secret

**Step 2: Set SUPABASE_ACCESS_TOKEN (2 min)**
1. Supabase dashboard → Project Settings → API → copy `service_role` key
2. Set in cron environment:
   - Railway: Project → Variables tab → add `SUPABASE_ACCESS_TOKEN = <service_role_key>`
   - GitHub Actions: Settings → Secrets → add `SUPABASE_ACCESS_TOKEN`

**Step 3: Verify**
```bash
# Run manually to confirm both connectors succeed
python brain/_tools/refresh_connectors.py

# Check log for success markers
tail -20 brain/INGESTION-LOG.md
```

Expected: both connectors show success, not 403 or "skipped".

### Files to inspect first
- `brain/_tools/refresh_connectors.py` — identifies exact env var names used for auth
- `brain/INGESTION-LOG.md` — shows current connector failure pattern

---

## Run 80 Mandate

If brain connectors still failing after next subconscious run:
- Add Step 9C to nightly SKILL.md — automated brain connector health check
- Step 9C: read `brain/INGESTION-LOG.md`, detect 3+ consecutive failures, create GH issue with label `human-action-required`
- If Step 9C added and failure persists beyond 2 more runs: P0 GH issue + tag human

If `SLACK_ALERT_WEBHOOK_URL` still not set (no further automated mandate per run 78 governance):
- Document as known gap in `ops/monitoring/SETUP.md` once nightly Step 9B writes it
- No further automated mandate — human-only configuration

---

## Governance Corrections Applied This Run

1. **total_runs**: 78 → 79
2. **last_run**: "2026-07-03" → "2026-07-05"
3. **Run 78 winner (Step 9B)**: status `pending_autonomous` → `implemented` (Step 9B added to nightly SKILL.md this run by subconscious — AUTONOMOUS-EXECUTABLE)
4. **Run 77 winner (healthz-alert.sh)**: status `pending_autonomous` → `escalated_to_p0_gh_issue` (P0 GH issue filed, mandate chain closed, no further automated mandate)
5. **Run 79 winner (brain connector fix)**: added to active_directions as `pending_human`

---

## Verification

```
Verified: Step 9B added to .claude/skills/nightly-commit-review/SKILL.md — DONE (this run)
Verified: P0 GH issue filed for ops/monitoring/healthz-alert.sh missing — DONE (GH #393, mandate executed)
Verified: GH issue filed for SLACK_ALERT_WEBHOOK_URL human setup — DONE (in GH #393 body)
Verified: GH issue filed for brain connector credential fix — DONE (GH #394)
Verified: brain/_tools/refresh_connectors.py GitHub 403 resolved — PENDING (human action)
Verified: SUPABASE_ACCESS_TOKEN set in cron environment — PENDING (human action)
Verified: brain/INGESTION-LOG.md shows fresh sync after credential fix — PENDING (human action)
```
