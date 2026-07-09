# Run 67 Winning Concept

**Run:** 2026-06-25-pm
**Run number:** 67
**Date:** 2026-06-25
**Category:** code_health
**Confidence:** HIGH
**Autonomous-executable:** false
**Requires human:** true
**Estimated effort:** S (10 minutes)
**Mandate-driven:** true (run 65 mandate fires)

---

## Title
Execute Run 65 Steps + Step 9B in Interactive Human Session

## Problem Statement
`check_project_invariants.py` has exited 1 for 3+ consecutive subconscious runs:
- FAIL: widget drift (widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js)
- FAIL: 10 em-dash violations in frontend JSX files (ReferralCard.jsx:6, SignupPage.jsx:40/151, AdminFunnelPage.jsx:15/49/87/122/267/315/440)

Run 65 labeled the fix AUTONOMOUS-EXECUTABLE. Nightly didn't deliver (scope mismatch).
Run 66 tried to fix the delivery channel by adding Step 9B to nightly SKILL.md.
Nightly didn't deliver that either (editing existing SKILL.md not in scope).

Run 65 mandate fires: "escalate to interactive human execution — no more meta-fix layers."

## Root Cause
Nightly-commit-review SKILL.md autonomous scope only covers 3 action types:
1. New .claude/skills/*/SKILL.md creation
2. Bash additions to scripts/hooks/pre-commit
3. New .github/workflows/*.yml

Run 65 fix (cp + text replacement) matches none of the 3.
Run 66 fix (edit existing SKILL.md) matches none of the 3.

The chicken-and-egg cannot be resolved by adding another subconscious layer.
The only resolution is direct human execution.

## Implementation Steps (human executes in interactive session)

### 1. Fix widget drift
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
```

### 2. Fix em-dashes — 4 files, 10 locations

**frontend/src/components/billing/ReferralCard.jsx:6**
Replace U+2014 (—) with hyphen or rewrite phrase.

**frontend/src/pages/SignupPage.jsx:40, 151**
Same — replace em-dash with hyphen-minus.

**frontend/src/pages/AdminFunnelPage.jsx:15, 49, 87, 122, 267, 315, 440**
Same — 7 occurrences.

### 3. Add Step 9B to .claude/skills/nightly-commit-review/SKILL.md

Insert after current Step 9 (plan-name guard), before the end of the file:

```
## Step 9B — AUTONOMOUS-EXECUTABLE governance dispatch

Read `subconscious/state/governance.json`. If `active_directions[0]` has:
- `autonomous_executable: true`
- `status: "pending_approval"`

Then:
1. Read `subconscious/runs/<run-dir>/winning-concept.md` for implementation steps
2. Execute the described steps (file copies, text replacements, edits)
3. Run `python3 scripts/check_project_invariants.py`
4. If exits 0: `git add -A && git commit -m "nightly: auto-deliver <title>"`
5. Update `active_directions[0].status` to `"implemented"` in governance.json

Process only `active_directions[0]`. Do not process multiple items per nightly run.
If check exits 1 after implementation: revert, log failure, do not commit.
```

### 4. Verify
```bash
python3 scripts/check_project_invariants.py
# Must print: "0 invariant(s) failed."
```

### 5. Commit
```bash
git add -A
git commit -m "fix: widget drift + em-dash violations + nightly Step 9B (run 65/66 delivery)"
```

---

## Success Criteria
- check_project_invariants.py exits 0
- No em-dash violations in frontend JSX
- widget/agentnexlify-widget.js byte-identical to landing-page-v2/widget/agentnexlify-widget.js
- Step 9B block present in nightly-commit-review SKILL.md
- Commit pushed

## Post-Implementation Cascade
Once check exits 0:
- Run 65 winner status → `implemented`
- Run 66 winner status → `implemented`
- true_pending decrements (2 items cleared from active_directions)
- When cleanup sprint runs (runs 20/21/29/42/50, ~1h), true_pending drops to ~1
- moratorium exits (pending_approvals < max_pending_approvals = 2)
- Run 68 candidate: Plan-name invariant guard (Check 7) — AUTONOMOUS-EXECUTABLE

---

## RUN 68 MANDATE
If check_project_invariants.py still exits 1 in run 68 (run 65 fix still unimplemented):
Provide exact copy-paste terminal commands for human in a code block.
Make it so frictionless that running it takes 30 seconds.
Last resort before escalating to a calendar reminder.
