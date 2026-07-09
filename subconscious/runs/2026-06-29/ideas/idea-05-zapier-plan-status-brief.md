# Idea 05 — Write GH Implementation Brief for Zapier #107 (plan_status Enforcement)

**Category:** code_health (security)  
**Effort:** XS (write issue brief only, no code changes)  
**Moratorium-safe:** YES — no code implementation, creates issue brief for issue-to-pr-loop  
**AUTONOMOUS-EXECUTABLE:** YES — doc write to GH issue  

## Evidence

- GH issue #107 opened 2026-04-30 (60+ days open)
- `docs/dev-knowledge/bug-patterns.md`: "Zapier API key plan_status not enforced (issue #107, TODO)"
- `backend/services/zapier_auth.py::_get_api_key_client` resolves keys without plan_status check
- Cancelled tenants with un-revoked keys bypass tier gate
- Parking lot ROI 2.5, note: "Promote to first non-moratorium winner if #107 still open. Route via issue-to-pr-loop, NOT subconscious winner queue."

## What It Would Build

Write a structured implementation brief as a comment on GH #107:
- Root cause: `_get_api_key_client` in `zapier_auth.py` missing `plan_status IN ('active','trialing')` filter
- Fix: add one SQL filter clause + update return type
- Test: regression test in `backend/tests/test_zapier_auth.py`
- This brief feeds issue-to-pr-loop for Haiku classification → Sonnet implementation

## Assessment

The parking lot explicitly says "Route via issue-to-pr-loop, NOT subconscious winner queue." Writing an implementation brief is the right action, but it's an XS step that doesn't justify being the run 71 winner over KB autopopulate fix (which has 53+ days of documented breakage and an explicit run 71 forecast). Route to parking lot → standing action for issue-to-pr-loop.
