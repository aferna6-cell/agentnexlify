# Morning Digest — 2026-05-29

**Generated:** 2026-05-29 UTC
**Moratorium:** DAY 25+ — Items A/B/D still pending (exit threshold: 2)
**Subconscious:** Run 39 complete — `post-split-test-repair` SKILL.md NOT created despite AUTONOMOUS-EXECUTABLE label

---

## Commits (last 24h) — 3 total

- `b1fd55b` subconscious: run 2026-05-29 (run 39) — Create post-split-test-repair SKILL.md *(recommendation only — file MISSING)*
- `061582c` ops: nightly-commit-review 2026-05-29 ← **autonomous win: Check 11 added**
- `3af4626` subconscious: run 2026-05-28-pm (run 38) — AI-to-Human Handoff v1 via Agent OS outbound *(recommendation only)*

**Nightly review autonomous fix (061582c):** billing-constant-guard Check 11 added to `scripts/hooks/pre-commit`.
- Fires WARNING (non-blocking) when `AMOUNT_TO_PLAN` missing `15000` or `25000`
- Verified: `Check 11: Billing constant guard... WARNING — AMOUNT_TO_PLAN missing entries: 15000 25000`
- Run 37 winner — now implemented. runs_implemented: 8 → 9.

---

## Issues — Active

| # | Title | Status |
|---|-------|--------|
| **#181** | billing: AMOUNT_TO_PLAN missing autopilot ($150) + professional ($250) | **P0 — 7 consecutive governance runs. Check 11 fires WARNING on every commit.** |
| **#185** | CI: 21 pytest failures (pyo3/cryptography PanicException) | env bug, not regression |
| **#169** | [subconscious] Moratorium active — oldest item ~43 days | day 25+ |

---

## Open PRs Needing Action

| # | Title | Age | Action |
|---|-------|-----|--------|
| **#190** | fix(os-workers): inject business profile into worker prompts | 1d (draft) | Review — post-#188 follow-on |
| **#186** | build(deps-dev): bump @typescript-eslint/parser 8.58→8.60 | 4d | **Safe — merge now** |
| #182 | Split invoices.py god class into 4 service modules | 6d (draft) | Blocked on #181 fix first |
| #183 | subconscious run 33 billing context | 5d (draft) | Low priority |
| #172 | chore(deps-dev): bump eslint 9.39.4→10.4.0 | 11d | MAJOR — test frontend before merge |
| #11–15 | Dependabot: GH Actions bumps | 45d | **Safe batch merge — 5 min** |

---

## Subconscious — Run 39 Recommendation

**Winner:** Create `.claude/skills/post-split-test-repair/SKILL.md`

- 8-step checklist to repoint stale `@patch` targets after every module split
- 100% recurrence rate: `5f2cd2b`, `4afb3cf`, `bca2082` — one repair commit per split/migration in 6 days
- Labeled AUTONOMOUS-EXECUTABLE. **NOT created.** Commit `b1fd55b` is recommendation-only.
- Blocks clean email_sequences.py split (1255L → 3 modules). Without it: 4th repair commit guaranteed.

**Run 38 standing:** AI-to-Human Handoff v1 — status `pending_approval`. Agent OS infra ready (PR #188 merged). Scope ~1 day. Still highest-value customer feature.

**Sequence per run 39:** post-split-test-repair SKILL (~5 min, auto) → GH #181 fix (~15 min, human) → email_sequences.py split (~2h) → AI-to-Human Handoff v1 (~1 day)

---

## Top 3 Priorities

1. **Fix GH #181** (~15 min) — `backend/routers/billing.py:263` add `15000: "autopilot"`, `25000: "professional"` to `AMOUNT_TO_PLAN`. Remove inverted test assertions `test_billing_amount_to_plan.py:38-44`. P0, 7 consecutive runs. Check 11 now fires WARNING every commit. Pre-condition for email_sequences.py split.

2. **Create `post-split-test-repair` SKILL.md** (~5 min) — run 39 winner, AUTONOMOUS-EXECUTABLE, NOT created. Full content in `subconscious/runs/2026-05-29/winning-concept.md`. File: `.claude/skills/post-split-test-repair/SKILL.md`. Unblocks email_sequences.py split cleanly.

3. **`/moratorium-sprint` Items A/B/D** (~40 min) — Day 25+. Items: check_project_invariants pre-commit (A), widget sync guard (B), CI eval workflow (D). Sketches: `subconscious/runs/2026-05-18/winning-concept.md`. Exit threshold: 2 pending items.

---

## Health Dashboard

| Signal | Status |
|--------|--------|
| Prod code (24h) | 0 feature commits — automated only |
| Autonomous win | ✓ Check 11 added to pre-commit (run 37) |
| Open billing bug | #181 — P0, 7 governance runs, UNRESOLVED. Check 11 fires WARNING. |
| post-split-test-repair skill | **MISSING** — run 39 winner, not implemented |
| Pre-commit Check 11 | ✓ ADDED (nightly 2026-05-29) |
| AI-to-Human Handoff | pending_approval — Agent OS infra ready (#188) |
| CI | pyo3 env bug (#185) — not regression |
| KB | 24 days stale (last compile 2026-05-05) |
| Moratorium | Day 25+, Items A/B/D pending |
| Open PRs | 10 open, #190 needs review, #186 + #11–15 safe to merge |

---

*Subconscious runs: `subconscious/runs/2026-05-29/winning-concept.md` (run 39) · `subconscious/runs/2026-05-28-pm/winning-concept.md` (run 38)*
*Nightly review: `ops/routines/logs/nightly-commit-review-2026-05-29.md`*
