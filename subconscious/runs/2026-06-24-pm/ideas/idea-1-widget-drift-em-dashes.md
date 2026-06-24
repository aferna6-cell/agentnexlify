# Idea 1: Fix Widget Drift + Em-Dash Violations (AUTONOMOUS-EXECUTABLE)

**Category**: code_health  
**Confidence**: HIGH  
**Effort**: S (~5 min, 2 operations)  
**Autonomous**: YES — same fix class as runs 49, 55, 57 (all delivered by nightly review)  
**Urgency**: CRITICAL — check_project_invariants.py exits 1, blocking all git commits via Check 13

## What is broken

check_project_invariants.py (run by pre-commit Check 13, FAIL+BLOCK mode) currently exits 1 due to two violation classes introduced by referral sprint PRs #368-371 (2026-06-22/23):

### 1. Widget drift
`widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js`

PRs #368-371 updated `widget/` and `frontend/public/widget/` but did NOT sync `landing-page-v2/widget/`. Three-copy invariant (CLAUDE.md Critical Invariant #4) violated.

### 2. Em-dash violations (10 instances)
New JSX UI copy introduced `—` (em-dash U+2014) characters that the em-dash check in check_project_invariants.py flags:

- `frontend/src/components/billing/ReferralCard.jsx:6` — 1 instance
- `frontend/src/pages/SignupPage.jsx:40` — 1 instance
- `frontend/src/pages/SignupPage.jsx:151` — 1 instance  
- `frontend/src/pages/AdminFunnelPage.jsx` — ~6 instances (approx lines 15, 49, 87, 122, 267, 315/440)

Total: 10 em-dash violations across 3 files.

## Fix

**Step 1: Sync widget** (1 command, ~5 seconds)
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
```

**Step 2: Fix em-dashes** (sed or direct edit, ~2 min)
Replace `—` (em-dash) with ` - ` (space-hyphen-space) in all flagged locations:
- ReferralCard.jsx:6
- SignupPage.jsx:40, 151
- AdminFunnelPage.jsx (6 instances, scan lines 15-440)

**Step 3: Verify**
```bash
python3 scripts/check_project_invariants.py
# Expected: all 6 checks PASS, exit 0
```

## Why this wins

- Unblocks pre-commit for ALL developers — every single commit is currently blocked
- AUTONOMOUS-EXECUTABLE: nightly review has implemented this exact class 3 times (runs 49/55/57)
- Zero product decisions required
- Prerequisite for Idea 2 (plan-name guard addition) — check_project_invariants.py must pass before extending it
- 5-minute fix with proven delivery channel

## Historical precedent

| Run | Fix class | Delivered by |
|-----|-----------|--------------|
| Run 49 | 5 JSX em-dash fixes | nightly review 8db33df (2026-06-05) |
| Run 55 | 10 em-dash + from __future__ | nightly 3234597 (2026-06-13) |
| Run 57 | widget sync cp | nightly 3234597 (2026-06-13) |

Exact same pattern. Zero unknowns.

## Run 66 mandate
If not implemented by run 66 (next cycle): explicit nightly review trigger instruction in winning-concept.md. AUTONOMOUS-EXECUTABLE items have been implemented within 1-2 days historically; no mandate expected.
