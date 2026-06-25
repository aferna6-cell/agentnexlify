# Idea 01 — Execute Run 65 Steps + Step 9B in Interactive Human Session

**Category:** code_health + workflow
**Confidence:** HIGH
**Autonomous-executable:** NO (requires human)

## Problem
check_project_invariants.py exits 1 for 2 reasons:
1. widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js (drift)
2. 10 em-dash violations in frontend JSX files

These have been AUTONOMOUS-EXECUTABLE (run 65) since 2026-06-23.
Nightly has not delivered for 2 consecutive cycles (run 65, run 66).
Run 65 mandate fires: "escalate to interactive human execution, no more meta-fix layers."

## Root Cause (confirmed run 67)
Nightly-commit-review SKILL.md autonomous scope covers:
- (a) new .claude/skills/*/SKILL.md creation
- (b) pre-commit bash additions to scripts/hooks/pre-commit
- (c) new .github/workflows/*.yml

Run 65 fix requires: `cp` + 10 text replacements in JSX files → NOT in scope (a/b/c).
Run 66 winner (add Step 9B) requires: editing EXISTING SKILL.md → NOT in scope (a).

Chicken-and-egg: Step 9B can't be added autonomously because existing-SKILL.md edits aren't
in scope. And without Step 9B, general AUTONOMOUS-EXECUTABLE items can't be dispatched.

## Fix (interactive, ~10 minutes)

### Step 1 — Copy widget file
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
```

### Step 2 — Fix em-dashes in 4 JSX files
Files and lines:
- frontend/src/components/billing/ReferralCard.jsx:6
- frontend/src/pages/SignupPage.jsx:40, 151
- frontend/src/pages/AdminFunnelPage.jsx:15, 49, 87, 122, 267, 315, 440

Replace U+2014 (—) with plain hyphen-minus (-) or rewrite phrase to avoid dash entirely.

### Step 3 — Add Step 9B to nightly-commit-review SKILL.md
Between Step 9 (plan-name guard) and the current end of SKILL.md, insert Step 9B block
as specified in subconscious/runs/2026-06-25/winning-concept.md.

### Step 4 — Verify
```bash
python3 scripts/check_project_invariants.py
```
Must exit 0.

### Step 5 — Commit
```bash
git add -A
git commit -m "fix: widget drift + em-dash violations + nightly Step 9B (run 65/66 delivery)"
```

## Why this wins over meta-fix approaches
- Direct. Immediate. Verified.
- Mandated by run 65 (day 3 of same failure → mandate fires)
- No further subconscious layers needed — fix is concrete, 10 minutes, exits 0
- Unblocks moratorium (true_pending will drop when cleanup sprint runs)
- Unblocks run 68 candidate (plan-name invariant guard, AUTONOMOUS-EXECUTABLE)
