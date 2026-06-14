# Morning Digest — 2026-05-21

Generated: 2026-05-21 (run 28 subconscious active)

---

## Commits (last 24h)

- `2057df2` subconscious: run 2026-05-21 (run 28) — Invoke /moratorium-sprint (governance audit clears pending 12→4)
- `841df50` ops: correct nightly-review-2026-05-21 — GH #175 was false alarm, commits on origin
- `c79b1e1` ops: nightly-commit-review 2026-05-21
- `752c3d2` subconscious: run 2026-05-20-pm (run 27) — Invoke /moratorium-sprint (final interactive rec, run 28 mandate)

**4 commits. All automated. No human-authored code today.**

---

## Issues Opened/Updated (last 24h)

- `#175` [CLOSED] [nightly-review] 15 commits orphaned off main — **FALSE ALARM, self-corrected by nightly review.** All commits confirmed on origin/main. Local main ref was stale.
- `#174` [OPEN] Morning digest 2026-05-20 — digest (yesterday's digest, age 1d)
- `#169` [OPEN] [subconscious] Moratorium active — **updated today** (nightly escalation auto-comment, age 5d). Still blocked.

---

## Open PRs Needing Action (20 total)

### Safe to merge now (<5 min total)
| # | Title | Age |
|---|-------|-----|
| #102 | update youtube-transcript-api ≥1.2.4 | 24d |
| #103 | bump python-multipart 0.0.26→0.0.27 | 24d |
| #164 | bump @playwright/test 1.59.1→1.60.0 | 10d |
| #171 | bump @typescript-eslint/parser 8.58→8.59.4 | 3d |

### Review required before merge
| # | Title | Age | Risk |
|---|-------|-----|------|
| #172 | bump eslint 9.39.4→**10.4.0** (MAJOR) | 3d | Test frontend first |
| #67 | bump sentry-sdk 2.20→2.58 (38 minor versions) | 31d | Large range, review changelog |
| #104 | bump uvicorn 0.34→0.46 (12 minor versions) | 24d | Test backend first |
| #65 | bump cross-env 7→**10.1.0** (MAJOR) | 31d | Review first |

### Stale DRAFTs — sprint blockers
| # | Title | Age | Action |
|---|-------|-----|--------|
| #80 | feat(onboarding-v2): Week 1 foundation | 28d | **SPRINT BLOCKER** — merge or reset |
| #86 | fix(hooks): 4 missing post-edit checks | 26d | Merge when moratorium exits |
| #85 | feat: intent engineering layer | 27d | Stale — review or close |

### Stale non-draft PRs (31d, memory-hygiene + Zapier)
| # | Title | Age |
|---|-------|-----|
| #71 | feat: [zapier] Docs + KB article + featured CRM comparisons | 31d |
| #72 | feat: [memory-hygiene] KB article provenance | 31d |
| #73 | feat: [memory-hygiene] Widget conversation memory tier | 31d |
| #74 | feat: [memory-hygiene] Extend /memory/ frontmatter | 31d |

### CI/Actions bumps (37d, low risk)
- #12 actions/setup-python 5→6
- #13 peter-evans/create-pull-request 6→8
- #14 actions/setup-node 4→6
- #15 actions/upload-artifact 4→7
- #18 @vitejs/plugin-react 4.7.0→6.0.1 (**MAJOR**)

---

## Subconscious (Run 28 — 2026-05-21)

**Winner: Invoke `/moratorium-sprint` — Items A, B, D. ~40 min. Pending 12→4 (after governance audit) → 4→2 (after sprint) = moratorium exits.**

Key new info vs run 27:
- Governance audit in Phase 6 marks 8 items as superseded/subsumed → true pending = 4 (not 12)
- Nightly review formally declined autonomous execution of run 27's hard mandate — governance system working as designed
- Interactive-only path confirmed as the only valid execution path
- Item C already done (2ce31b2, 2026-05-20)

**3 items remaining:**
| Item | Work | Time |
|------|------|------|
| A | Wire `check_project_invariants.py` into pre-commit as Check 10 | ~5 min |
| B | Create `scripts/check-widget-sync.sh` + pre-push hook + CLAUDE.md Invariant #4 fix | ~15 min |
| D | `.github/workflows/lead-qualifier-eval.yml` — closes #110 | ~20 min |

Sketches: `subconscious/runs/2026-05-18/winning-concept.md`
Confidence: **HIGH**

---

## Top 3 Priorities Today

1. **`/moratorium-sprint`** — Run 28 is the interactive session. Sprint exists, sketches ready, ~40 min. Exits moratorium. Unlocks all future subconscious work. One command.
2. **Merge safe dep PRs #102, #103, #164, #171** — <5 min. Zero risk. Board hygiene.
3. **Triage stale non-draft PRs #71–74 (31d)** — merge or close. Clean board before moratorium exit.

---

## KB Status

Last compile: 2026-04-29 (no cron activity since). 98 wiki articles. Embedding backlog exists (4 articles pending reindex via `scripts/reindex_contextual.py` once SUPABASE_ACCESS_TOKEN present). Not blocking current work.

---

*Full run: `ops/routines/logs/morning-digest-2026-05-21.md`*
