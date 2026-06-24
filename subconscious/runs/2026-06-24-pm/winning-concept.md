# Winning Concept — Run 65 (2026-06-24-pm)

## Title
Fix Widget Drift + Em-Dash Violations (AUTONOMOUS-EXECUTABLE)

## Category
code_health

## Confidence
HIGH

## Effort
S (~5 min, 2 operations)

## Autonomous
YES — AUTONOMOUS-EXECUTABLE. Same fix class as runs 49, 55, 57. Nightly review delivery channel proven.

## Urgency
CRITICAL — check_project_invariants.py exits 1, pre-commit Check 13 in FAIL+BLOCK mode. Every git commit is blocked.

## Background

Referral sprint (PRs #368-371, 2026-06-22/23) introduced two violation classes:

1. **Widget drift**: PRs updated `widget/` and `frontend/public/widget/` but skipped `landing-page-v2/widget/`. Three-copy invariant broken (CLAUDE.md Critical Invariant #4).

2. **Em-dash violations**: 10 em-dash characters (`—`, U+2014) in new JSX marketing copy across 3 files.

check_project_invariants.py (wired as pre-commit Check 13 via run 58, 2026-06-17) runs on every `git commit` in FAIL+BLOCK mode. Exits 1 since PRs #368-371 merged.

## Implementation

### Step 1: Sync widget (30 seconds)
```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
```

### Step 2: Fix em-dashes in ReferralCard.jsx
File: `frontend/src/components/billing/ReferralCard.jsx`
Line 6: Replace `—` with ` - ` (or appropriate hyphen based on context)

### Step 3: Fix em-dashes in SignupPage.jsx
File: `frontend/src/pages/SignupPage.jsx`
Line 40: Replace `—` with ` - `
Line 151: Replace `—` with ` - `

### Step 4: Fix em-dashes in AdminFunnelPage.jsx
File: `frontend/src/pages/AdminFunnelPage.jsx`
Scan lines 15, 49, 87, 122, 267, 315-440 area. Replace all `—` with ` - `.
Expected: ~6 instances.

### Step 5: Verify
```bash
python3 scripts/check_project_invariants.py
# Expected output:
# PASS: client_id discipline
# PASS: lead status field (status, not lead_stage)
# PASS: areas_of_interest (not service_interest)
# PASS: widget byte-sync (widget/ == frontend/public/widget/ == landing-page-v2/widget/)
# PASS: no from __future__ import annotations in FastAPI files
# PASS: no em-dash characters in JSX/TSX files
# Exit code: 0
```

### Step 6: Commit
```bash
git add landing-page-v2/widget/agentnexlify-widget.js \
    frontend/src/components/billing/ReferralCard.jsx \
    frontend/src/pages/SignupPage.jsx \
    frontend/src/pages/AdminFunnelPage.jsx
git commit -m "fix(invariants): sync widget drift + clear 10 em-dash violations from referral sprint

PRs #368-371 updated widget/ and frontend/public/widget/ but skipped landing-page-v2/widget/.
10 em-dash violations introduced in ReferralCard.jsx, SignupPage.jsx, AdminFunnelPage.jsx.
Unblocks pre-commit Check 13 (check_project_invariants.py exits 0 again).

AUTONOMOUS-EXECUTABLE — nightly review authorized."
```

## Bonus A: Plan-Name Invariant Guard (run 66 candidate)

After this fix lands and check_project_invariants.py exits 0, add Check 7:

Scan `backend/services/` for retired plan name strings in plan-comparison logic:
- Retired (never use): `foundation`, `operations`
- Warn-level: `growth`, `autopilot`, `professional` in new service files
- Verify: `chatbot` and `agent_os` present in `_UNLIMITED_PLANS`, `_ALLOWED_PLANS`, `_PLAN_BASELINE_AI_TOKENS`

Implementation sketch: `subconscious/runs/2026-06-20-pm/winning-concept.md §Bonus B` (canonical from run 64).

AUTONOMOUS-EXECUTABLE. Run 66 candidate.

## Bonus B: AI-to-Human Handoff v1 (standing action, Bonus A escalating)

Run 4, 69 days pending. M-effort (~1 day). Full sketch: `subconscious/runs/2026-05-28-pm/winning-concept.md`.

Trigger detection → handoff_requests table → owner SMS/email via os_outbound_mirror.py → lead status `needs_follow_up`.

Requires human implementation. Run 66-68 candidate for winner slot once autonomous queue clears.

## Run 66 mandate

No mandate set — AUTONOMOUS-EXECUTABLE items are implemented by nightly review within 1-2 days historically. If not implemented by run 66: add explicit nightly trigger instruction ("nightly review: implement run 65 winning-concept.md, AUTONOMOUS-EXECUTABLE label confirmed") and escalate to explicit winner again.

## Why this run

Run 65 is the first free-choice run in 6 cycles (runs 59-64 consumed by alternating mandate mechanism for GH #308 / GH #292/#293, both now implemented 2026-06-23). Free choice → highest-ROI recommendation. Pre-commit blocked = every commit friction for every developer. 5-minute autonomous fix. Zero product decisions. Clear implementation path. Proven delivery channel (nightly review).
