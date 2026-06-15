# Morning Digest — 2026-06-15

Generated: 2026-06-15 UTC

---

## Commits (last 24h)

- `87b5eb8` ops: nightly-commit-review 2026-06-15
- `65a8a40` chore(deps): bump python-multipart 0.0.26→0.0.27 (#103)
- `01fa4e5` chore(deps): bump sentry-sdk 2.20.0→2.58.0 (#67)
- `9f9203d` feat(security): encrypt integrations secrets at rest — key vault + fastapi<0.136 fix (#129, #131, #264)
- `cfdd6e3` Launch-readiness batch 2: CI eval wiring, schema-log resolution, email-sequence perf, frontend tests (#262)

**5 commits.** Big one: integrations encryption landed yesterday (#264).

---

## Issues — opened/updated last 24h

- `#266` [OPEN] 2026-06-14 — **security: finish integrations-secret encryption — backfill + sunset plaintext columns**
  - Staged plan: provision INTEGRATIONS_ENC_KEY in Railway → migrate readers → backfill → drop plaintext columns. Half-migration still open.
- `#265` [OPEN] 2026-06-14 — **deps: re-raise the fastapi <0.136 cap once starlette 0.50-compatible release lands**
  - Holding fastapi below 0.136 because of Starlette compat; re-raise when starlette catches up.
- `#263` [OPEN] 2026-06-14 — **Schema Sync [CRITICAL]: 24 pending migrations**
  - 24 migrations written but not applied. Production schema drift risk.

---

## Open PRs needing action

| # | Title | Age | Status |
|---|-------|-----|--------|
| #267 | feat(integrations): tenant integration-keys API + provider health checker | 0d | DRAFT |
| #260 | feat(pre-commit): wire Check 10 + governance corrections (runs 55+57) | 2d | DRAFT |
| #258 | Remove em dashes from landing page front page | 2d | DRAFT |
| #27 | deps: bump dompurify 3.3.3→3.4.0 | 1d | Open (needs merge/close) |
| #31 | deps: bump react-dom 18.3.1→19.2.5 (demo-platform) | 2d | Open |
| #29 | deps: bump react 18.3.1→19.2.5 (demo-platform) | 2d | Open |

**Note:** 3 draft PRs need author to mark ready or merge. Dependabot PRs (#27, #31, #29, etc.) are stacking — worth a batch-merge pass.

---

## Subconscious Recommendation

**Run 2026-06-13 (HIGH confidence):** Copy `widget/agentnexlify-widget.js` → `landing-page-v2/widget/agentnexlify-widget.js` — fixes widget drift introduced by PR #254 (Spanish translation + web push). Single `cp` command. Clears Critical Invariant #4. Check_project_invariants confirmed live violation.

**Run 2026-06-12 (HIGH confidence):** Add pre-commit Check 13 — reject any staged `backend/**/*.py` containing `from __future__ import annotations`. 4 files currently infected after PR #238 god-class split. Same class as Check 11/12 (both autonomously wired by nightly). Prevents infinite whack-a-mole on future router splits.

---

## Top 3 Priorities Today

1. **Finish the integrations encryption migration (#266)** — `9f9203d` shipped the vault but plaintext columns still exist in prod. Provision `INTEGRATIONS_ENC_KEY` in Railway, run backfill script, then drop columns. Rule 8: no half-migrations.

2. **Clear the schema sync CRITICAL (#263): 24 pending migrations** — 24 unnapplied migrations is a prod drift bomb. Apply via Supabase MCP or UI before any new backend work.

3. **Merge subconscious wins (widget sync + Check 13)** — Both are LOW-risk, HIGH-confidence, single-file changes. Widget copy clears Invariant #4. Check 13 guard prevents `from __future__` re-infection on every future god-class split. PR #260 (runs 55+57) is already drafted — review and mark ready.

---

## Backlog Radar

- `#193` Moratorium: 13 pending items (oldest 44 days) — subconscious flagged this; consider a sweep session.
- `#217` Stripe Connect (BLOCKED on billing-architecture decision) — no action until decision made.
- `#114/#128/#129/#130/#131` Migration series (ops-automation, onboarding-v2) — part of the 24-pending pile above.

---

*Next digest: 2026-06-16 08:00 UTC*
