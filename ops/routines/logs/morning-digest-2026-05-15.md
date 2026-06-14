# Morning Digest — 2026-05-15

Generated: 2026-05-15 UTC

---

## Commits (last 24h)

- `2b69da7` subconscious: run 2026-05-15 — Widget 3-Copy Sync Guard (run 17, moratorium day 21)
- `dc09dbc` ops: nightly-commit-review 2026-05-15

**2 commits. Automated only. No manual feature work. Moratorium day 22.**

---

## Issues Opened/Updated (last 24h)

- `#167` Morning digest 2026-05-14 — OPEN (digest) — automated only

No new feature/bug issues in last 24h. Zero manual dev activity signal.

Notable open non-digest issues (active epics):
- `#114` [ops-automation] Migration 118 — auto-ready, p0
- `#128` [onboarding-v2] Migration 119 — auto-ready, p0
- `#129` [onboarding-v2] Migration 120 — auto-ready, p0
- `#143` [self-maintenance] Migration 122 — auto-ready, p0
- `#138` [onboarding-v2] Wizard v2 frontend — p0, no auto label

---

## Open PRs Needing Action

| # | Title | Age | Action |
|---|-------|-----|--------|
| #164 | bump @playwright/test 1.59→1.60 | 4d | Safe — merge |
| #163 | bump @typescript-eslint/parser 8.58→8.59 | 4d | Safe — merge |
| #156 | bump eslint 9.39→10.3.0 | 11d | **Major version** — test frontend build first |
| #104 | bump uvicorn 0.34→0.46 | 18d | 12 minor versions — test backend |
| #103 | bump python-multipart 0.0.26→0.0.27 | 18d | Patch — merge |
| #102 | bump youtube-transcript-api | 18d | Low risk — merge |
| #86 | fix(hooks): 4 missing post-edit checks | 20d | DRAFT — small, merge when moratorium exits |
| #85 | feat: intent engineering layer | 21d | DRAFT — stale, review or close |
| #80 | feat(onboarding-v2): Week 1 foundation | 22d | DRAFT — **sprint blocker**, 14+ issues gated — merge or reset |
| #65 | bump cross-env 7→10.1.0 | 25d | **Major bump** — review before merge |

Safe to merge now without testing: #163, #164, #102, #103.

---

## KB Updates (last 24h)

None. Last compile: 2026-05-05 (10 days stale).
4 slugs pending embedding backfill (`SUPABASE_ACCESS_TOKEN` + `VOYAGE_API_KEY` missing in cron).
Fix: `python3 scripts/reindex_contextual.py` when tokens available.

---

## Subconscious (Run 17 — 2026-05-15)

**Winner: Widget 3-Copy Sync Guard** (run 7, moratorium day 21)

- Moratorium ACTIVE — `pending_approvals = 4` (runs 4, 7, 8, 14) > threshold 3
- 40-min sprint drops pending 4→1:
  - Bonus A: wire `check_project_invariants.py` into pre-commit (~5 min) — run 8
  - Bonus B: wire lead qualifier eval to CI (~20 min) — run 14
  - Winner: create `scripts/check-widget-sync.sh` + pre-push hook wire (~15 min) — run 7
- **Run 18 escalation boundary**: if still unimplemented, winner MUST switch to Automated Moratorium Escalation Hook (4-consecutive-run threshold)
- Widget copies confirmed IN SYNC as of May 15 — guard is preventative

---

## Top 3 Priorities Today

1. **40-min moratorium sprint** — implement Widget 3-Copy Sync Guard (run 7) + Bonus A (run 8) + Bonus B (run 14). Drops pending 4→1. Implementation sketch is complete in `subconscious/runs/2026-05-15/winning-concept.md`. Zero blockers.

2. **Merge safe deps** — merge #163, #164, #102, #103. Four quick merges, no testing needed. Clears PR queue.

3. **Decide #80 fate** — onboarding-v2 Week 1 DRAFT is 22 days old and blocking 14+ dependent issues. Merge it or reset the epic with a new branch. Leaving it in DRAFT limbo blocks the entire sprint.

---

*Next: moratorium exit unblocks Zapier API key fix (issue #107, security, 15 days open) → route via issue-to-pr-loop.*
