# Idea 5 — Home.jsx God-Class Split (1006L → 3 modules)

**Category:** Code Health
**Effort:** M (2-3 hours — refactor only, no feature change)
**Moratorium impact:** AUTONOMOUS-EXECUTABLE candidate (code health, no schema change)
**Evidence:**

- `frontend/src/pages/Home.jsx` — 1006 lines (god-class threshold: 600L per user-rules.md Rule 9)
- `backend/routers/email_sequences.py` — 1143 lines (also a god-class, run 41 parked)
- User Rule 12: "Default to new file. Only extend existing files when new code serves SAME concern."
- User Rule 9: "File >600L and adding new code → factor first."

## Proposed Split

Home.jsx likely contains: widget config, lead stats, appointment stats, recent activity, onboarding state. These are 3-4 distinct concerns.

Proposed modules:
- `frontend/src/components/home/LeadStats.jsx`
- `frontend/src/components/home/AppointmentStats.jsx`
- `frontend/src/components/home/RecentActivity.jsx`
- `frontend/src/pages/Home.jsx` — orchestrates, under 200L

## Why Parked This Run

- Moratorium: even though AUTONOMOUS-EXECUTABLE, this is M-effort refactor. Risk of introducing regressions if not carefully tested.
- SMS Dashboard ships value; god-class split ships nothing user-visible
- Better to ship customer value first, then clean up
- File hasn't grown in weeks — no immediate pressure

## Re-evaluate When

SMS Dashboard shipped. Email_sequences.py also needs same treatment (1143L, run 41 parked). Could batch both in one refactor session.
