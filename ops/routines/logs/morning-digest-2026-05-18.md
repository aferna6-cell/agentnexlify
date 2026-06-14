# Morning Digest — 2026-05-18

Generated: 2026-05-18 UTC

---

## Commits (last 24h)

- `2483466` subconscious: run 2026-05-18 (run 23) — Moratorium Exit Sprint PR (4 S-effort items, one branch)
- `f0c879e` ops: correct nightly-review-2026-05-18 — 6187d5f confirmed on main not dangling
- `db9a5d0` ops: nightly-commit-review 2026-05-18
- `6187d5f` subconscious: run 2026-05-17-pm (run 22) — Wire check_project_invariants.py into pre-commit

**4 commits. Automated only. No manual feature work. Moratorium day 10.**

---

## Issues Opened/Updated (last 24h)

None opened today. No feature/bug issues updated since 2026-05-17.

Active open non-digest issues (blocking or high-priority):

| # | Title | Labels | Days open |
|---|-------|--------|-----------|
| #169 | [subconscious] Moratorium active: 5 pending items, oldest 30 days | nightly-review | 2d |
| #114 | [ops-automation] Migration 118 — ops_automation_v1 schema | p0, ai-ready | 16d |
| #128 | [onboarding-v2] Migration 119 — extend widget_configs + vertical_presets | p0, ai-ready | 16d |
| #129 | [onboarding-v2] Migration 120 — encrypt integrations.access_token | p0, ai-ready | 16d |
| #143 | [self-maintenance] Migration 122 — maintenance_suggestions + crawl_history | p0, ai-ready | 16d |

101 total open issues.

---

## Open PRs Needing Action

| # | Title | Age | Action |
|---|-------|-----|--------|
| #80 | [DRAFT] feat(onboarding-v2): Week 1 foundation | 25d | **SPRINT BLOCKER** — 14+ P0/P1 issues gated — merge or reset |
| #85 | [DRAFT] feat: intent engineering layer | 24d | Stale — review or close |
| #86 | [DRAFT] fix(hooks): 4 missing post-edit checks | 23d | Merge when moratorium exits |
| #65 | bump cross-env 7→10.1.0 | 28d | **Major bump** — review before merge |
| #104 | bump uvicorn 0.34→0.46 | 21d | **12 minor versions** — test backend first |
| #102 | update youtube-transcript-api ≥1.2.4 | 21d | Safe — merge |
| #103 | bump python-multipart 0.0.26→0.0.27 | 21d | Patch — merge |
| #156 | bump eslint 9.39→10.3.0 | 14d | **Major version** — test frontend build first |
| #163 | bump @typescript-eslint/parser 8.58→8.59.3 | 7d | Safe — merge |
| #164 | bump @playwright/test 1.59.1→1.60.0 | 7d | Safe — merge |

**Safe to merge now (no testing needed): #163, #164, #102, #103.**

---

## KB Updates (last 24h)

None. Last compile: 2026-05-05 (13 days stale). 4 slugs pending embedding backfill.
Fix: `python3 scripts/reindex_contextual.py` when `SUPABASE_ACCESS_TOKEN` + `VOYAGE_API_KEY` available.

---

## Subconscious (Run 23 — 2026-05-18)

**Winner: Moratorium Exit Sprint — 4 S-effort items, one branch, one approval decision.**

- Moratorium ACTIVE — `pending_approvals = 9` > threshold 2
- Sprint framing: bundle runs 7 + 8 + 14 + 18/19 into `moratorium-exit-sprint` branch (~50 min total)
  - **Item A** (~5 min): Wire `check_project_invariants.py` into pre-commit as Check 10 — run 8, 23 days pending
  - **Item B** (~15 min): Widget 3-copy sync guard — `scripts/check-widget-sync.sh` + pre-push + CLAUDE.md fix — run 7, 24 days pending
  - **Item C** (~10 min): Encode Moratorium Escalation Protocol in `nightly-commit-review/SKILL.md` — runs 18/19, 2 days pending
  - **Item D** (~20 min): CI eval workflow — `.github/workflows/lead-qualifier-eval.yml` (Monday cron + PR trigger) — run 14, 13 days pending
- Drops pending 9→5. Pending drops further if run 21 GH issue also created.
- First run where sprint PR is the **sole** recommendation (not a footnote). Approval friction drops 4×.
- Full sketches: `subconscious/runs/2026-05-18/winning-concept.md`

---

## Top 3 Priorities Today

1. **Moratorium Exit Sprint** — Execute run 23 winning concept. Create branch `moratorium-exit-sprint`. Implement items A→D (~50 min, all additive, zero blockers). Open draft PR. Drops pending 9→5. Sketch: `subconscious/runs/2026-05-18/winning-concept.md`. This is run 23 day 1 — act now while the implementation window is open.

2. **Merge safe deps** — Merge #163, #164, #102, #103 (4 PRs, no testing needed). Clears 4 stale PRs in <5 min.

3. **Decide PR #80 fate** — DRAFT 25 days, blocking 14+ P0/P1 onboarding-v2 issues. Merge, reset, or document the blocker in writing.

---

*Full moratorium backlog: `ops/routines/logs/nightly-commit-review-2026-05-18.md`*
*Subconscious state: `subconscious/state/governance.json`*
