# Winning Concept — Run 69 (2026-06-27)

## Title
Hybrid: Step 9B Widget Byte-Sync + Hard Run 70 Deadline

## Category
Workflow Efficiency

## Problem Statement
`check_project_invariants.py` has exited 1 for 5 consecutive subconscious runs (runs 65-69). Pre-commit Check 13 has blocked all git commits since 2026-06-23. The sole remaining failure: `widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js`. The fix is 1 cp command. The subconscious has recommended it 5 times; it has never been executed.

## New Evidence (Run 69)
Nightly commit 2026-06-27 (ffefe61) proved the autonomous delivery mechanism works: 10 em-dash violations across 7 JSX/JS files were fixed via Step 9B text replacement operations. The only reason widget cp was not included: landing-page-v2/ is on nightly's FORBIDDEN paths list. That list was written to prevent code edits to legacy landing page logic — not to prevent a deterministic file-sync required by an invariant check.

## Recommendation

### Part A: Add Widget Byte-Sync Exception to Nightly Step 9B
Amend `.claude/skills/nightly-commit-review/SKILL.md` Step 9B as follows:

Add after the existing AUTONOMOUS-EXECUTABLE items:

```markdown
### AUTONOMOUS-EXECUTABLE: Widget byte-sync (if invariant check shows drift)
1. Run: `python3 scripts/check_project_invariants.py 2>&1 | grep -q "FAIL widget"`
2. If drift detected:
   `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
3. Re-run check. If clean: `git add landing-page-v2/widget/agentnexlify-widget.js && git commit -m "fix: widget drift byte-sync (invariant enforcement)"`
4. NOTE: landing-page-v2/ is otherwise FORBIDDEN for code edits. This cp-only exception is pre-approved by subconscious run 69 and is a file-sync operation, not a code change.
```

**Human approval required before nightly runs tonight (before 2:37 AM 2026-06-28).**

### Part B: Hard Run 70 Mandate (No Further Extensions)
Update `governance.json`:
```json
"run_70_mandate": "If check_project_invariants.py still exits 1 at run 70: calendar reminder fires. No extensions. No further subconscious recommendations on this item."
```

If nightly 2026-06-28 delivers the cp and check passes: mandate is satisfied, pre-commit unblocks, this line item closes.
If check still exits 1 at run 70: push notification with URGENT tone, docs/reminders/widget-drift-URGENT.md written, and the subconscious loop exits this topic permanently — it becomes a human task only.

## Rationale
1. The run 68 mandate's premise ("autonomous stack exhausted") is falsified by ffefe61. Step 9B works.
2. Deferring the mandate one run to use the proven mechanism is adaptation, not drift — because a hard stop exists at run 70.
3. Calendar reminder now would be disproportionate: 1 cp command, proven delivery path available, only the SKILL.md scope needs expanding.
4. The run 70 deadline is non-negotiable. No further extensions under any circumstances.

## Success Criteria
- `check_project_invariants.py` exits 0 at run 70
- Pre-commit Check 13 unblocks
- `git commit` works again
- Run 70 winning concept can address a non-widget topic for the first time since run 64

## Implementation Steps (Human)
1. Approve this winning concept
2. Add the Step 9B widget-sync exception to `.claude/skills/nightly-commit-review/SKILL.md`
3. Nightly runs at 2:37 AM 2026-06-28 → executes cp → commits → pre-commit passes
4. Alternatively: execute `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js` manually in terminal now (30 seconds)

## Bonus A — After Widget Drift Resolves
**Plan-Name Invariant Guard (Check 7 expansion):** Add `foundation` and `operations` (retired plan names) to `check_project_invariants.py` Invariant #3 check alongside `lead_stage` and `service_interest`. Currently checks retired schema fields; should also check retired billing tier names. Low-effort, sequencing-blocked until Check 13 unblocks.

## Bonus B — Next Sprint After Unblocking
**SMS Compliance Dashboard:** Backend + frontend page surfacing TCPA opt-out rates, compliance scores, and blocked-contacts list per tenant. Council fix #1 (2026-06-24) added the backend TCPA enforcement; the dashboard makes it legible to business owners. See `docs/dev-knowledge/customer-gaps.md`.

---

## RUN 70 MANDATE

**If `check_project_invariants.py` still exits 1 in run 70: the subconscious loop writes docs/reminders/widget-drift-URGENT.md, sends a push notification with URGENT flag, and retires this topic from the subconscious permanently. The fix becomes a human-only task. No extensions, no new ideas, no further debate. This is the final autonomous attempt.**
