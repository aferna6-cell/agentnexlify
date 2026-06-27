# Idea 01 — Honor Mandate: Calendar Reminder Escalation

**Category:** Workflow Efficiency  
**Evidence anchor:** Run 68 winning-concept.md §RUN 69 MANDATE

## What
Create a calendar reminder (Google Calendar event or cron-based persistent alert) instructing Aidan to run:
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js && python3 scripts/check_project_invariants.py && git add -A && git commit -m "fix: widget drift (run 65 mandate — pre-commit blocked since 2026-06-23)"
```
Mandate fires because `check_project_invariants.py` still exits 1 at run 69 — the 5th consecutive failure.

## Why
Mandates exist because repeated soft-delivery failures exhaust the subconscious loop's toolkit. A mandate is not a suggestion; it is a pre-committed escalation. Honoring it maintains system integrity. If mandates bend when inconvenient, they stop being mandates.

## Delivery mechanism
Subconscious writes a `docs/reminders/widget-drift-fix-REQUIRED.md` + updates governance.json with `mandate_fired: true` + generates a push notification with a high-urgency tone. Human executes the fix next time they check their phone.

## Risk
- Relies on human action (same failure mode as all prior runs)
- Calendar/reminder creation requires human tooling not accessible from subconscious
- Adds noise to human's attention for a 1-line fix

## Verdict signal
Strict mandate adherence. Appropriate if system integrity > delivery speed.
