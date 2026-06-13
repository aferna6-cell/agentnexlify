# Winning Concept — 2026-06-13

**AUTONOMOUS-EXECUTABLE**

## Recommendation
Copy `widget/agentnexlify-widget.js` to `landing-page-v2/widget/agentnexlify-widget.js` to fix the live widget sync drift introduced by PR #254.

## Why This, Why Now
PR #254 (3f79d7f, 2026-06-13) updated `widget/agentnexlify-widget.js` (+202 lines, Spanish translation + web push) and `frontend/public/widget/agentnexlify-widget.js` (+202 lines) but did NOT update `landing-page-v2/widget/agentnexlify-widget.js`. `check_project_invariants.py` confirms the drift live: `drift: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js`. CLAUDE.md Critical Invariant #4 requires all three copies to be byte-identical. This is the first run where widget drift is a confirmed CURRENT bug rather than a future risk. Fixing it eliminates one of three check_project_invariants failures and moves the system one step closer to Check 10 auto-wiring (exits 0 requires all 3 failures cleared). Implementation is a single `cp` command — same class as em-dash substitutions executed autonomously by nightly 8db33df.

## Implementation Sketch

```bash
# In the repo root:
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
```

Steps:
1. Read `widget/agentnexlify-widget.js` to confirm it is the updated version (should contain Spanish translation strings and push notification logic from PR #254)
2. Copy: `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js`
3. Verify: run `check_project_invariants.py` — widget drift failure should clear (2 remaining: from __future__ + em-dashes)
4. Commit: `git add landing-page-v2/widget/agentnexlify-widget.js && git commit -m "fix(widget): sync landing-page-v2 widget copy after PR #254 — clears Critical Invariant #4"`
5. Update governance.json: add run 57 to active_directions with `pending_autonomous: true`, `autonomous_executable: true`

**AUTONOMOUS-EXECUTABLE**: Nightly review (2:37 AM) reads governance.json, sees pending_autonomous winner, executes cp command. Same risk class as file substitutions (em-dash fixes executed by 8db33df). No code logic changed — pure file copy.

## What This Replaces
Complements rather than replaces active_directions. Run 55 (em-dash + from __future__ fix) and run 56 (Check 13) remain pending_autonomous. This run adds the widget copy as a third autonomous item. Together, runs 55+57 clear 2 of 3 check_project_invariants failures; from __future__ fix (run 55 covers this) clears the third → exits 0 → Check 10 auto-wires.

## Confidence
HIGH — evidence is concrete (check_project_invariants.py output + git stat), fix is trivial (single file copy), autonomous execution is well-precedented (nightly file operations), and the failure is a confirmed live invariant violation not a hypothetical risk.
