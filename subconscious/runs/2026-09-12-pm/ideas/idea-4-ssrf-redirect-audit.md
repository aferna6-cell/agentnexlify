# Idea 4: SSRF Redirect Hop Validation Sweep

**Category:** code_health / security
**Effort:** S
**Confidence:** MEDIUM-LOW

## Evidence
- a74b0c4 (2026-09-12): "fix(security): validate prospecting redirect hops (#847)" — 40 lines in backend/services/prospecting.py + 96 test lines.
- prospecting.py fetches prospect business websites. Added redirect hop count validation (max N redirects, private IP range check on each hop).
- Pattern: if prospecting needed it, other outbound HTTP callers may be missing equivalent protection.
- Potential surfaces: KB autopopulate (fetches URLs from raw content), any webhook URL from tenant config, lead enrichment fetches.

## Action
Grep backend/ for `requests.get\|httpx.get\|httpx.AsyncClient` calls that follow redirects. Verify each call site either: (a) uses `allow_redirects=False` + manual redirect logic with hop validation, or (b) is internal (Railway/Supabase internal hostnames, not user-supplied URLs). File issues for gaps.

## Impact
- Closes SSRF redirect-chain attack surface on user-supplied URL endpoints.
- Expected: 2-5 call sites needing validation beyond prospecting.py.

## Weaknesses
- Evidence from ONE commit. May be prospecting-specific, not a class problem.
- Requires reading 5+ service files to find call sites — S not XS effort.
- Other security surfaces (Auth, payments, CORS) take priority over SSRF redirect.
