# Idea 1: Run 68 Mandate — 30-Second Terminal Fix

**Category:** code_health
**Impact:** HIGH
**Effort:** S (~30 seconds of human execution)
**Autonomous-executable:** false (HUMAN-REQUIRED)

## Evidence
- `check_project_invariants.py` confirmed exits 1 (live run, 2026-06-26):
  - FAIL: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js
  - FAIL: 10 em-dash violations (ReferralCard.jsx:6, SignupPage.jsx:40/151, AdminFunnelPage.jsx:15/49/87/122/267/315/440)
- 4 consecutive runs (65/66/67/68) with check failing
- Pre-commit Check 13 blocks ALL commits — no developer can ship anything
- Run 67 winning-concept.md lines 114-118 mandates: "provide exact copy-paste terminal commands for human in code block — 30-second execution. Last resort before calendar reminder."
- Meta-fix approaches (runs 65/66/67) exhausted — nightly scope cannot cover cp + text replacement + existing SKILL.md edits

## Action
Write winning-concept.md with verbatim copy-paste bash commands covering:
1. `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
2. sed/Python one-liners to replace 10 em-dash chars across 4 files
3. Add Step 9B block to nightly-commit-review SKILL.md
4. Verify exits 0
5. Commit

## Expected Impact
- Unblocks ALL developer commits immediately
- Clears run 65 + run 66 from active_directions (pending → implemented)
- true_pending: ~6 → ~4
- Moratorium exit 2 items closer
- Run 69 candidate: Plan-name invariant guard Check 7 (AUTONOMOUS-EXECUTABLE, finally unblocked)
