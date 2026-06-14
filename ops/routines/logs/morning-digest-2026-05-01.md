# Morning Digest — 2026-05-01

> Period: last 24h | 14 commits | 4 issues updated | 10 open PRs | subconscious run 12

---

## Commits (last 24h) — 14 total

**Subconscious / ops:**
- `fd9dc98` subconscious: run 12 — JS Silent Catch Guard Check 10 (numbering corrected)
- `b34e687` ops: nightly-commit-review 2026-05-01
- `b489004` merge: reconcile remote run 10 state with local run 11 artifacts
- `405e180` subconscious: run 11 (2026-04-30-pm) — JS Silent Catch + governance correction
- `e9a0fb4` kb(log): append run summary 2026-04-30 18:37

**Features / merges:**
- `2baf7b2` merge: slice 3 UI — totals headline + activity feed UI
- `37c151c` plans(onboarding-v2): add implementation plan + 21 issue drafts; kb: MIT ML textbook list

**Skills / docs:**
- `8b91ec7` skills(agent-filter): add Kimi K2.6 / GPT-5.5 cross-provider routing to skip list

**Auto-commits (5):**
- `60fdbe2`, `06dc1e8`, `4716fa5`, `7854ede`, `90ba1c5` / `c6960d8` — AI auto-commits

---

## Issues — updated last 24h

| # | Title | Status | Labels |
|---|-------|--------|--------|
| **#110** | ops: wire lead-qualifier golden eval harness to CI | OPEN — new today | nightly-review, backend |
| **#109** | fix: AdminAnalyticsPage silent-catch swallows 6 API failures | OPEN — new today | nightly-review, frontend |
| #108 | Morning digest 2026-04-30 | OPEN (digest) | digest |
| #107 | fix(zapier): enforce plan_status check in _get_api_key_client | OPEN | nightly-review, medium, backend |

**#110 detail:** Lead qualifier golden eval (`backend/tests/evals/`) always skipped in CI — gated behind `RUN_LEAD_QUALIFIER_EVAL=1`, never set. Regressions go undetected. Fix: add weekly GH Actions workflow.

**#109 detail:** `AdminAnalyticsPage.jsx:117-122` — 6 `.catch(() => null)` with zero logging. Silent null on API failure → UI shows zeroes. Subconscious run 12 winner addresses this directly.

**#107 detail (carry-forward):** `backend/routers/zapier.py:99-135` — `plan_status` selected but never checked. Churned tenants keep Zapier access. Fix: add `plan_status not in {"active","trialing"} → 402`.

---

## Open PRs — 10 total

| # | Title | Age | Draft | Action |
|---|-------|-----|-------|--------|
| #104 | bump uvicorn 0.34→0.46.0 | 4d | — | **MERGE** |
| #103 | bump python-multipart 0.0.26→0.0.27 | 4d | — | **MERGE (security)** |
| #102 | update youtube-transcript-api ≥1.2.4 | 4d | — | MERGE |
| #101 | bump @typescript-eslint/parser 8.58→8.59 | 4d | — | MERGE |
| #86 | fix(hooks): 4 missing post-edit checks | 6d | DRAFT | review → undraft → merge |
| #85 | feat: intent engineering layer | 7d | DRAFT | needs migration `112_intent_config.sql` applied |
| #80 | feat(onboarding-v2): Week 1 foundation | 8d | DRAFT | Week 2 backend pending |
| #73 | feat: widget conversation memory tier | 11d | — | needs review |
| #72 | feat: KB article provenance | 11d | — | needs review |
| #65 | bump cross-env 7→10.1.0 | 11d | — | **CAUTION — MAJOR, ESM-only** |

**Batch-mergeable now: #101 + #102 + #103 + #104**

---

## Subconscious — run 12 (2026-05-01)

**Winner:** JS Silent Catch Guard — Fix `AdminAnalyticsPage.jsx:117-122` + Add **Check 10** to `scripts/hooks/pre-commit`

- Prior runs (9–11) mislabeled this as "Check 9" — pre-commit has 9 existing checks; JS guard is Check 10
- Pattern: 4 violations fixed manually (2026-04-28, commit `e68677a`) → 6 new ones already present in AdminAnalyticsPage. Fix-without-guard cycle at iteration 4
- Onboarding V2 sprint (21 issues, `37c151c`) starts now — every new JSX file is a risk vector
- Moratorium: 4 pending winners, lifts at ≤3. Implementing run 3 drops count to 3 → moratorium lifts
- Confidence: HIGH

**Run 11 (carry-forward note):** governance correction — run numbering discrepancy between local/remote resolved via merge `b489004`.

---

## KB Status

- Last compile: 2026-04-30 18:37 — raw=11 wiki=4
- Total articles: ~98
- Embedding errors: `VOYAGE_API_KEY` missing from cron env — upserts skipped every run
- **Action needed:** set `VOYAGE_API_KEY` in Railway/cron env

---

## Top 3 Priorities Today

1. **JS Silent Catch Guard (run 12 winner)** — fix `AdminAnalyticsPage.jsx:117-122` (issue #109) + add Check 10 to `scripts/hooks/pre-commit`. S-effort. Lifts subconscious moratorium. Guards Onboarding V2 sprint before first new JSX lands.

2. **Fix #107** — `backend/routers/zapier.py:99-135`: add `plan_status` guard. One-liner + test in `test_zapier_auth.py`. Churned tenants bypass billing until this ships.

3. **Batch merge #101 + #102 + #103 + #104** — 4-day dep queue. Security bump in #103 (python-multipart). Mechanical — no review depth needed.

---

*Full log: `ops/routines/logs/morning-digest-2026-05-01.md`*
*Future: replace GH issue step with post to #dev-standup when Slack connector attached.*
