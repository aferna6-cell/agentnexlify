# Improvement Backlog — 2026-06-01 (Run 44)

## Active

- **Scope check_project_invariants.py em-dash check to skip .jsx/.tsx** — 3-line Python
  fix unblocks Item A autonomous execution; AUTONOMOUS-EXECUTABLE; closes GH #194

## Parking Lot (survived debate, not chosen)

- **Add Item D to AUTONOMOUS-EXECUTABLE scope in nightly SKILL.md** — Item D
  (lead-qualifier-eval.yml) additive CI YAML, propose in run 45 after Item A confirms
- **Merge 5 stale Dependabot PRs (#102, #103, #163, #164, #171)** — ~5 min, independent,
  41+ days stale; valid at any time

## Rejected This Run

- **Fix JSX em-dash violations directly** (Idea 3) — KILLED: changes UI copy
  (`— Not set —` is an intentional UX affordance); scoping the check is correct fix
- **Invoke /god-class-splitter on email_sequences.py** (Idea 5) — KILLED as winner:
  stands as active_direction (run 41); GH #181 billing fix is prerequisite; moratorium
  day 30 makes M-effort human work a low-priority winner vs 3-line scope fix

## Standing Critical Actions (Require Human)

- **GH #181 billing fix** (~15 min) — AMOUNT_TO_PLAN missing 15000+25000; test
  contradictions blocking CI; critical_standing_action since run 35
- **email_sequences.py split** (~2h) — run 41 winner, 1255L, prerequisite: GH #181 first
- **Item B: check-widget-sync.sh** (~15 min) — moratorium sprint item, HUMAN REQUIRED
- **AI-to-Human Handoff v1** (~1 day) — run 38 winner, Agent OS ready, day 46 gap

## Questions for Next Run

1. Did nightly 2026-06-02 execute Item A after the scope fix? (`grep -n "check_project_invariants" scripts/hooks/pre-commit`)
2. Is GH #181 billing fix implemented yet? (Check `billing.py` for 15000+25000 entries)
3. Was Item D added to autonomous scope, and did it execute? (check `.github/workflows/lead-qualifier-eval.yml`)
