# Idea 1: Add localStorage Detection to Post-Edit Hook

## Summary
Add CLAUDE.md invariant #6 (`No localStorage in React`) to `scripts/claude-hooks/post-edit-check.sh` — the final unautomated invariant after this week's hook improvements.

## Evidence
- 3eaf702 (2026-06-23): added 4 invariant checks to post-edit hook (lead_stage, service_interest, widget byte-identical, model IDs)
- c8f1bde: fixed em-dash HTML entity false positives
- CLAUDE.md critical invariant #6: "No `localStorage` in React artifacts — storage isn't available in claude.ai artifact sandbox"
- Post-edit hook currently covers: tenant_id (#1), lead_stage (#2), service_interest (#3), widget sync (#4), model IDs (bonus)
- **Gap**: no automated check for `localStorage` in `frontend/**/*.{jsx,js}` files
- Documented as "storage isn't available in claude.ai artifact sandbox" — a real-world breakage mode, not theoretical

## What "done" looks like
In `post-edit-check.sh`, for edits to `frontend/**/*.{jsx,js}`:
```bash
if grep -qn "localStorage" "$EDITED_FILE"; then
  echo "WARN: localStorage in React file — breaks claude.ai artifact sandbox (CLAUDE.md invariant #6)"
fi
```
Scoped to frontend JSX/JS only (widget already has separate byte-identical check). Warn-only (not blocking) consistent with hook style.

## Impact
- Prevents a class of widget/dashboard breaks that only surface in claude.ai sandbox
- Completes invariant automation: all 6 CLAUDE.md critical invariants now have at least one automated gate
- Extends momentum from this week's invariant improvements

## Effort
LOW — ~8 lines of shell in an existing file. No new dependencies.

## Category
Code quality / automation
