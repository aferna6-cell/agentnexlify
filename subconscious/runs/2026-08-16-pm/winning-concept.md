# Winning Concept — 2026-08-16-pm

## Recommendation
Fix `backend/routers/scoring_config.py` by adding `block_demo_role` to the router-level dependencies, closing GH #661 and eliminating the confirmed demo-tenant mutation hole in scoring configuration.

## Why This, Why Now
GH #661 was filed this morning by the nightly review confirming that 4 mutating endpoints in `scoring_config.py` (PUT `/api/v1/scoring/factors/{id}`, POST `/api/v1/scoring/factors`, DELETE `/api/v1/scoring/factors/{id}`, POST `/api/v1/scoring/reset`) expose write access to demo tenants. This is the same class of vulnerability as appointment_briefs.py, which run 106 fixed — meaning the pattern, the fix, and the SKILL.md guide to execute it all already exist. The route-security-guard-audit SKILL.md (commit 60d132f, run 107 branch) was written precisely to guide this type of fix. Waiting compounds the exposure: demo tenants can currently corrupt scoring factor weights, create spurious factors, and reset scoring to defaults — actions that affect lead qualification quality for the tenant if they were to convert to a paying account.

## Implementation Sketch
1. Open `backend/routers/scoring_config.py`
2. Add `block_demo_role` to the existing import from `backend.dependencies`:
   `from backend.dependencies import _get_current_tenant, block_demo_role`
3. Add `dependencies=[Depends(block_demo_role)]` to the router-level `APIRouter(...)` constructor (same line as existing `require_role` deps, or add separately per endpoint as needed)
4. Run `ast.parse` smoke check: `python3 -c "import ast; ast.parse(open('backend/routers/scoring_config.py').read()); print('OK')"`
5. Verify the 4 mutating endpoints now return 403 for demo tenant fixture in test
6. Commit: `fix(security): add block_demo_role to scoring_config router — closes #661`

Reference: `backend/routers/appointment_briefs.py` for exact import + dependency pattern.
Reference: `.claude/skills/route-security-guard-audit/SKILL.md` for full 6-step guide.

## What This Replaces
Previous active direction was "write route-security-guard-audit SKILL.md" (completed run 105/107). New active direction: apply that skill to close GH #661 (scoring_config.py), then schedule a broader router audit to find any remaining missing guards.

## Confidence
HIGH — confirmed bug (GH #661), proven fix pattern (appointment_briefs.py run 106), implementation guide exists (SKILL.md), single-file change with zero blast radius for non-demo tenants.
