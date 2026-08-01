# Improvement Backlog — 2026-08-01-pm (Run 101)

## Active (Winner)
- **Step 9G: KB autopopulate self-healing trigger** — add `gh workflow run kb-autopopulate.yml` to nightly SKILL.md when `DAYS_STALE > 7`. Sleep 30s, check conclusion, comment diagnostic on GH #403 if failed. ~30 lines bash after Step 9F block. Carry-forward from run 100.

## Parking Lot (survived debate, not chosen this run)

| Item | Reason parked | Revisit trigger |
|------|--------------|-----------------|
| prospecting.py god-class split (536L) | Below 600L CLAUDE.md Rule 9 threshold; PR #619 only 2 days old; /god-class-splitter requires human session | File hits 600L or first bug traced to mixed concerns |
| GH #399 specific rotation steps comment | Valid but lower leverage than Step 9G; alert-only posture | Bonus Action if Step 9G still absent in run 102 |
| connector_registry.py interface contract ADR | Pre-emptive; 314L, 4 connector types | 5th connector type wired OR file hits 400L |
| PWA push on appointment_completed | ~15 lines, high LTV impact | Available as bonus action any cycle; ~1 sprint effort |

## Frozen (never propose)
- ai_human_handoff

## Mandate for Run 102
1. Step 9G confirmed present in `.claude/skills/nightly-commit-review/SKILL.md`?
2. KB fresher than 2026-07-23? (`knowledge-base/log.md` last entry date)
3. Step 9G output visible in nightly log (`docs/dev-knowledge/nightly-reviews/`)? Did it trigger? Succeed or fail?
4. GH #403 — did Step 9G post a comment (success or diagnostic)?
5. If Step 9G STILL absent → direct implementation via subconscious (same as run 99 did for Step 9F)
