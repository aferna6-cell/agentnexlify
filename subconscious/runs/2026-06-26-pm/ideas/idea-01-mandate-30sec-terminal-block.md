# Idea 01 — Deliver 30-Second Terminal Command Block (Mandate Fires)

**Category:** code_health  
**Confidence:** HIGH  
**Autonomous:** false — REQUIRES HUMAN  
**Effort:** 30 seconds (copy-paste, no decision-making)

## Summary
Run 68 mandate fires. check_project_invariants.py exits 1 for the 4th consecutive subconscious run (65/66/67/68). Pre-commit Check 13 FAIL+BLOCK mode has blocked all git commits since 2026-06-23. Run 67 winning-concept.md §"RUN 68 MANDATE" explicitly states: "provide exact copy-paste terminal commands for human in a code block. Make it so frictionless that running it takes 30 seconds. Last resort before escalating to a calendar reminder."

## Evidence
- check_project_invariants.py live output: 2 failures — widget drift + 10 em-dashes
- 3 prior delivery attempts exhausted: nightly run 65 (scope miss: cp not in scope), nightly run 66 (scope miss: editing existing SKILL.md not in scope), interactive prompt run 67 (human did not execute the ~10-min steps)
- Exact failure lines: ReferralCard.jsx:6, SignupPage.jsx:40/151, AdminFunnelPage.jsx:15/49/87/122/267/315/440
- Widget drift: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js
- Root cause: referral sprint PRs #368-371 (2026-06-22/23) updated frontend/src/ + widget/ without syncing landing-page-v2/widget/

## Proposed Action
Deliver terminal commands as the winning concept. Human pastes into terminal. Done.

```bash
# Fix pre-commit invariant violations — run from repo root (30 seconds):
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
sed -i 's/—/-/g' frontend/src/components/billing/ReferralCard.jsx frontend/src/pages/SignupPage.jsx frontend/src/pages/AdminFunnelPage.jsx
python3 scripts/check_project_invariants.py && git add -A && git commit -m "fix: widget drift + em-dash violations (run 65 mandate — pre-commit blocked since 2026-06-23)"
```

## Why Now
- Mandate fires unconditionally (run 67 winning-concept.md §RUN 68 MANDATE)
- Pre-commit block stops all future commits until resolved
- 4 consecutive runs of same winner = highest-priority item in governance history
- Council sprint (9 commits) landed since run 67 — unblocking pre-commit now matters more, not less
