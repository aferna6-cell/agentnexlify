# Morning Digest — 2026-05-20

Generated: 2026-05-20 UTC | **Moratorium Day 15** (15 days no production commits)

---

## Commits (last 24h)

- `1300394` subconscious: run 2026-05-20 (run 26) — Invoke /moratorium-sprint (3 items, Item C done)
- `2ce31b2` ops: nightly-commit-review 2026-05-20
- `056b3df` ops: morning-digest 2026-05-19

**3 commits. Automated only. Key win: nightly review (2ce31b2) autonomously completed Item C — added Moratorium Escalation Protocol section to `.claude/skills/nightly-commit-review/SKILL.md`.** That's 2 autonomous implementations in 2 days (moratorium-sprint SKILL.md yesterday, Item C today).

---

## Issues Opened/Updated (last 24h)

- `#173` Morning digest 2026-05-19 — digest (OPEN, 1d)

**No new issues opened today.** Active high-priority open issues:

- `#169` [subconscious] Moratorium active — OPEN. Nightly escalation protocol now live: GH #169 will receive auto-comments nightly until /moratorium-sprint executes.
- `#173` Morning digest 2026-05-19 — digest (OPEN, unresolved from yesterday)
- `#114` Migration 118 — p0, ai-ready (25d)
- `#128` Migration 119 — p0, ai-ready (25d)
- `#129` Migration 120 — p0, ai-ready (25d)
- `#143` Migration 122 — p0, ai-ready (25d)

---

## Open PRs Needing Action (15 total)

| # | Title | Age | Action |
|---|-------|-----|--------|
| #80 | [DRAFT] feat(onboarding-v2): Week 1 foundation | 27d | **SPRINT BLOCKER** — merge or reset |
| #85 | [DRAFT] feat: intent engineering layer | 26d | Stale DRAFT — review or close |
| #86 | [DRAFT] fix(hooks): 4 missing post-edit checks | 25d | Merge when moratorium exits |
| #65 | bump cross-env 7→10.1.0 | 30d | **MAJOR bump** — review before merge |
| #67 | bump sentry-sdk 2.20→2.58 | 30d | **Large range** — review first |
| #71 | feat: Zapier docs + KB article | 30d | Stale non-draft — merge or close |
| #72 | feat: KB article provenance | 30d | Stale non-draft — merge or close |
| #73 | feat: widget conversation memory tier | 30d | Stale non-draft — merge or close |
| #74 | feat: /memory/ frontmatter extension | 30d | Stale non-draft — merge or close |
| #104 | bump uvicorn 0.34→0.46 | 23d | 12 minor versions — test backend first |
| #102 | update youtube-transcript-api ≥1.2.4 | 23d | **SAFE — merge now** |
| #103 | bump python-multipart 0.0.26→0.0.27 | 23d | **SAFE — merge now** |
| #164 | bump @playwright/test 1.59.1→1.60.0 | 9d | **SAFE — merge now** |
| #171 | bump @typescript-eslint/parser 8.58→8.59.4 | 2d | **SAFE — merge now** |
| #172 | bump eslint 9.39.4→10.4.0 | 2d | **MAJOR version** — test frontend first |

**Safe to merge immediately (no testing needed): #102, #103, #164, #171. <5 min total.**

---

## Subconscious Recommendation (Run 26 — 2026-05-20)

**Invoke `/moratorium-sprint` — 3 items remain (A, B, D). Item C done today. ~40 min. Pending 9→6 when PR merges.**

- Item A: Wire `check_project_invariants.py` into pre-commit as Check 10 (~5 min)
- Item B: Widget 3-Copy Sync Guard — `check-widget-sync.sh` + pre-push hook + CLAUDE.md fix (~15 min)
- Item D: Lead Qualifier Eval CI Workflow — `.github/workflows/lead-qualifier-eval.yml` (~20 min)
- All have pre-written sketches in `subconscious/runs/2026-05-18/winning-concept.md §Steps 1-4`
- Escalation path now live: GH #169 receives nightly auto-comments until sprint executes
- After sprint PR merges: resolve runs 20/21/22 → pending 6→3 → moratorium within 1 more resolution of exit

---

## KB / Automation Health

- KB last updated: 2026-05-05 (15 days stale — network sandbox blocking outbound discover)
- Nightly review: ACTIVE, running nightly, autonomously fixing LOW-risk items
- Subconscious loop: ACTIVE, run 26 complete
- Issue-to-PR loop: INACTIVE (moratorium blocks PR work)
- Moratorium escalation protocol: LIVE as of today (2ce31b2)

---

## Top 3 Priorities Today

1. **`/moratorium-sprint`** — skill exists, Item C done, 3 items left (~40 min). One command. Critical path to all other work. Pre-written sketches ready. Pending 9→6 on PR merge.
2. **Merge safe dep PRs** — #102, #103, #164, #171. Patch/minor versions, no testing needed. <5 min. Clean the noise.
3. **Triage stale non-draft PRs #71–74 (30d)** — merge or close. Four PRs at 30 days is tech debt accumulating daily. Do this before or after sprint.

---

*Full subconscious: `subconscious/runs/2026-05-20/winning-concept.md`*
*Log: `ops/routines/logs/morning-digest-2026-05-20.md`*
