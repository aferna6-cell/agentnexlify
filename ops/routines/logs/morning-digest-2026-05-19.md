# Morning Digest — 2026-05-19

Generated: 2026-05-19 UTC | Moratorium Day 11

---

## Commits (last 24h)

- `8076519` subconscious: run 2026-05-19 (run 25) — Invoke /moratorium-sprint (tool ready, execute 4 S-effort items)
- `7985fbb` ops: nightly-commit-review 2026-05-19

**2 commits. Automated only. Nightly review applied 1 LOW-risk fix: created `.claude/skills/moratorium-sprint/SKILL.md`.**

---

## Issues Opened/Updated (last 24h)

No new issues opened today. Active high-priority open issues:

- `#170` Morning digest 2026-05-18 — digest (still OPEN, not closed yet)
- `#169` [subconscious] Moratorium active: 5 pending items, oldest 30 days — OPEN
- `#114` Migration 118 — p0, ai-ready (17d)
- `#128` Migration 119 — p0, ai-ready (17d)
- `#129` Migration 120 — p0, ai-ready (17d)
- `#143` Migration 122 — p0, ai-ready (17d)

---

## Open PRs Needing Action

| # | Title | Age | Action |
|---|-------|-----|--------|
| #80 | [DRAFT] feat(onboarding-v2): Week 1 foundation | 26d | **SPRINT BLOCKER** — 14+ P0/P1 issues gated — merge or reset |
| #85 | [DRAFT] feat: intent engineering layer | 25d | Stale DRAFT — review or close |
| #86 | [DRAFT] fix(hooks): 4 missing post-edit checks | 24d | Merge when moratorium exits |
| #65 | bump cross-env 7→10.1.0 | 29d | **MAJOR bump** — review before merge |
| #67 | bump sentry-sdk 2.20→2.58 | 29d | **Large range** — review before merge |
| #71 | feat: Zapier docs + KB article | 29d | Stale non-draft — merge or close |
| #72 | feat: KB article provenance | 29d | Stale non-draft — merge or close |
| #73 | feat: widget conversation memory tier | 29d | Stale non-draft — merge or close |
| #74 | feat: /memory/ frontmatter extension | 29d | Stale non-draft — merge or close |
| #104 | bump uvicorn 0.34→0.46 | 22d | **12 minor versions** — test backend first |
| #164 | bump @playwright/test 1.59.1→1.60.0 | 8d | **SAFE** — merge |
| #102 | update youtube-transcript-api ≥1.2.4 | 22d | **SAFE** — merge |
| #103 | bump python-multipart 0.0.26→0.0.27 | 22d | **SAFE** — merge |
| #171 | bump @typescript-eslint/parser 8.58→8.59.4 | 1d | **SAFE** — merge (new today) |
| #172 | bump eslint 9.39.4→10.4.0 | 1d | **MAJOR version** — test frontend first |

**Safe to merge now: #102, #103, #164, #171. (<5 min total)**

---

## Subconscious (Run 25 — 2026-05-19)

**Winner: Invoke `/moratorium-sprint` — skill is ready, execute 4 S-effort items now.**

- Moratorium ACTIVE — `pending_approvals = 10` > threshold 2
- Skill `.claude/skills/moratorium-sprint/SKILL.md` created by nightly review — activation energy at all-time low
- Sprint (~50 min total):
  - **Item A** (~5 min): Wire `check_project_invariants.py` into pre-commit as Check 10
  - **Item B** (~15 min): Widget 3-copy sync guard — `check-widget-sync.sh` + pre-push + CLAUDE.md fix
  - **Item C** (~10 min): Encode Moratorium Escalation Protocol in `nightly-commit-review/SKILL.md`
  - **Item D** (~20 min): CI eval workflow — `.github/workflows/lead-qualifier-eval.yml`
- Drops pending 10→6 on PR merge. Exit condition: pending ≤ 2.
- Three independent systems (skill discovery, subconscious loop, nightly review) all agree: `/moratorium-sprint` is the action.
- Full sketch: `subconscious/runs/2026-05-18/winning-concept.md`

---

## Top 3 Priorities Today

1. **`/moratorium-sprint`** — skill exists, zero context-loading overhead, one command. Moratorium day 11, oldest pending 25+ days. Execute items A→D, open draft PR, pending 10→6. This is the critical path to all other work.
2. **Merge safe deps** — merge #102, #103, #164, #171 in one pass. All patch/minor. No testing needed. <5 min.
3. **Clear stale non-draft PRs** — #71, #72, #73, #74 (29d old, memory-hygiene + Zapier). Merge or close. Cleans up PR board ahead of moratorium exit.

---

*Full log: `ops/routines/logs/morning-digest-2026-05-19.md`*
