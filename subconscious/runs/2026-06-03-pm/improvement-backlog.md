# Improvement Backlog — 2026-06-03-pm (Run 49)

## Active

- Extend nightly SKILL.md + apply 5 JSX em-dash patches as AUTONOMOUS-EXECUTABLE (run 49 winner, tonight). Tonight → Check 10 auto-wires tomorrow night.

## Parking Lot (survived debate but not chosen)

- **Item B standalone — create scripts/check-widget-sync.sh** (~15 min, Bonus A): Run 48's Item B. Still valid. If Idea 1 autonomous chain confirms, this is the next human task. Implementation sketch in run 48 winning-concept.md §Step 2 + run 49 winning-concept.md §Bonus A.
- **Items A+B combined human-execute** (run 48 winner): Dominated by Idea 1 for Item A. Remains valid if autonomous path fails in run 50. Human execution is always fastest if present.
- **email_sequences.py god-class split** (run 41 active_direction): 1255L, both skills ready. Prerequisite: GH #181 billing fix first. Next major code-health win after moratorium items close.
- **Zapier API key plan_status enforcement** (GH #107, ROI 2.5, S-effort, ~15 min): Security fix, high ROI. Do alongside moratorium-sprint or first post-moratorium free choice.

## Rejected This Run

- **AI-to-Human Handoff v1 as winner**: 7+ recs without implementation. Moratorium active. No new forcing function. Standing note: POST-MORATORIUM FIRST PRIORITY. Do not re-propose as winner until moratorium exits.

## Questions for Next Run

1. Did nightly (2026-06-04 2:37 AM) fix the 5 JSX em-dashes? Check git log for commit message matching "em-dash violations in JSX UI copy."
2. Did check_project_invariants.py exit 0 after the nightly commit?
3. Did Check 10 auto-wire on 2026-06-05 nightly? Check scripts/hooks/pre-commit for check_project_invariants.py call.
4. Was Item B (scripts/check-widget-sync.sh) created as Bonus A?
5. Was GH #181 billing fix applied as Bonus B?
6. How many pending moratorium items remain? Are we within 2 of exit?
