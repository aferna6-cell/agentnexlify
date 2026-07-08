# Morning Digest — 2026-07-08

Generated: 2026-07-08 UTC (automated routine)

---

## Commits (last 24h)

- `a0874c4` brain: scheduled refresh from GitHub + Supabase
- `f958ab7` ops: nightly-commit-review 2026-07-08
- `84abd7d` subconscious: run 82 (2026-07-07-pm) — migrate KB autopopulate to GitHub Actions
- `6ef10ba` ops: morning-digest 2026-07-07

**4 commits. Automation pipeline healthy — nightly review + subconscious + brain sync all fired.**

---

## Issues (opened/updated since 2026-07-07)

- **#394** OPEN `human-action-required` — Fix brain-refresh[bot] credentials (GitHub 403 + SUPABASE_ACCESS_TOKEN missing) — _Day 8. Still blocked. Escalating._
- **#385** OPEN `ai-ready` — Add SMS Compliance Dashboard (backend + frontend) — _ai-ready label applied run 81. Issue-to-pr-loop should have triggered._
- **#397** OPEN `digest` — Morning digest 2026-07-07 _(yesterday's digest issue)_

**1 critical blocker (#394). #385 unblocked and queued for autonomous execution.**

---

## Open PRs Needing Action

| # | Title | Age | Status |
|---|-------|-----|--------|
| #387 | brain: sync Maps to 2026-07-01 reality + widget drift fix | 7d | DRAFT — promote + merge |
| #396 | bump @typescript-eslint/parser 8.62.0→8.62.1 | 2d | dep |
| #383 | bump react-router-dom 7.17.0→7.18.0 | 9d | dep |
| #382 | bump jsdom 29.0.2→29.1.1 | 9d | dep |
| #381 | bump @playwright/test 1.61.0→1.61.1 | 9d | dep |
| #380 | bump eslint 9.39.4→10.6.0 | 9d | dep |
| #372 | Referral reward: $20 credit to referrer on first paid invoice | 15d | DRAFT |
| #281 | bump @vitest/coverage-v8 4.1.8→4.1.9 | 23d | dep |
| #279 | bump vitest 4.1.8→4.1.9 | 23d | dep |
| #86 | fix(hooks): add 4 missing post-edit checks from harness audit | 74d | DRAFT |

**10 open PRs. #387 is the only real work item (ready for promote+merge). 7 Dependabot dep bumps — batch-merge to clear queue.**

---

## Subconscious (last 2 runs)

**Run 82 (2026-07-07-pm) — WINNER:**
- Recommendation: Create `.github/workflows/kb-autopopulate.yml` — migrate KB autopopulate from local cron to GitHub Actions
- Root cause confirmed: `scripts/daily/kb-autopopulate.sh` requires local `claude` CLI at `/home/aidan/...` — not available in CI/remote environments
- KB last successful run: **2026-05-05 — 63 days stale**
- Confidence: HIGH | Effort: S | Autonomous-executable: YES
- Impact: Restores twice-daily KB growth; platform intelligence layer running on May 2026 data

**Run 81 (2026-07-07) — WINNER:**
- Applied `ai-ready` label to GH #385 (SMS Compliance Dashboard)
- Status: EXECUTED — issue-to-pr-loop should have triggered within 15 min
- Mandate for run 82: verify PR opened for #385 + diagnose KB cron (completed)

---

## Top 3 Priorities Today

### 1. FIX BRAIN CONNECTOR CREDENTIALS — GH #394 (7 min, human required)
**Day 8. Critical.** All autonomous agents operating on stale context since 2026-07-01.
- GitHub PAT: Settings → Developer settings → Personal access tokens → new classic token (`repo`, `issues` read) → Railway Variables
- Supabase: dashboard → Project Settings → API → service_role key → Railway Variable `SUPABASE_ACCESS_TOKEN`
- Verify: `python brain/_tools/refresh_connectors.py` → `tail -10 brain/INGESTION-LOG.md`
- Resolving this also unblocks KB pgvector upsert (run 82 winner note: same `SUPABASE_ACCESS_TOKEN`)

### 2. IMPLEMENT RUN 82 WINNER — KB Autopopulate GitHub Action (S effort, autonomous-executable)
**63 days of stale KB.** Create `.github/workflows/kb-autopopulate.yml`:
- Schedule: `cron: '0 6,18 * * *'` (matches original local cron intent)
- Secrets needed: `ANTHROPIC_API_KEY` (required) · `VOYAGE_API_KEY` (optional) · `SUPABASE_ACCESS_TOKEN` (optional, graceful-skip)
- Pattern: mirrors `.github/workflows/refresh-brain.yml` already in place
- Keep `scripts/daily/kb-autopopulate.sh` as local fallback

### 3. MERGE PR #387 + BATCH DEP BUMPS (10 min)
- #387: Promote from draft → merge (brain Maps sync + widget byte-identical fix, 7d old)
- #279 #281 #380 #381 #382 #383 #396: Batch-merge Dependabot deps (aging 2–23d, all low-risk)
- #86: Review 74d-old hooks draft — merge or close

---

## Status Snapshot

| System | Status |
|--------|--------|
| Brain connectors | FAILING — 8 consecutive days (#394 human-required) |
| SMS Dashboard (#385) | QUEUED — ai-ready, issue-to-pr-loop should have fired |
| KB autopopulate | DEGRADED — 63 days stale (run 82 winner: GH Action fix, executable) |
| Subconscious | HEALTHY — run 82 executed, KB root cause identified |
| Nightly commit review | HEALTHY — ran 2026-07-08 |
| Dependabot PRs | 7 open dep bumps, aging 2–23d |
| PR #387 | READY — promote + merge |
| SLACK_ALERT_WEBHOOK_URL | NOT SET (pending) |

---

_Full log: `ops/routines/logs/morning-digest-2026-07-08.md`_
_Next digest: 2026-07-09_
