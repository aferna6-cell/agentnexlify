# Winning Concept — 2026-04-25-pm

## Recommendation
Wire `scripts/check_project_invariants.py` into `scripts/hooks/pre-commit` as a new check that blocks commits containing naming-invariant violations (wrong field names, forbidden patterns defined in CLAUDE.md Critical Invariants).

## Why This, Why Now
Commit `037865f` (today) added `scripts/check_project_invariants.py` — a stdlib-only, zero-dependency invariant checker explicitly described as "safe for CI and for agents." The script sits unwired. CLAUDE.md lists naming violations (`tenant_id` vs `client_id`, `lead_stage` vs `status`, `service_interest` vs `areas_of_interest`) as a recurring bug class with 3+ production incidents. The pre-commit hook already runs Python checks (`__future__` annotations, bare-except); adding one call to `check_project_invariants.py` closes the gap between documenting invariants and enforcing them at commit time. S-effort. Zero new infrastructure. The script was designed for exactly this use case.

## Implementation Sketch
1. **Verify standalone behavior** — `python3 scripts/check_project_invariants.py` from repo root. Confirm it exits 0 on current clean codebase.
2. **Add to `scripts/hooks/pre-commit`** after existing Python checks:
   ```bash
   # Check N: Project invariants (client_id, status, areas_of_interest naming)
   if ! python3 scripts/check_project_invariants.py 2>&1; then
     echo "BLOCKED: project invariant violation detected."
     echo "Run: python3 scripts/check_project_invariants.py for details."
     exit 1
   fi
   ```
3. **Test the hook** — make a synthetic violation (use `tenant_id` where `client_id` expected), commit, confirm BLOCKED. Revert.
4. **Update `CLAUDE.md`** — note invariant check is now pre-commit enforced (under Automation section).
5. **Verify** — `bash scripts/hooks/pre-commit` passes on clean HEAD.

## What This Replaces
No previous active direction displaced. Complements run 6 (migration duplicate guard) — both are pre-commit guard additions, but different concern layers: run 6 checked file naming, this checks code content.

## Confidence
**HIGH** — Evidence triple-backed: (1) script added today and explicitly designed for CI/agent use, (2) invariant violations are documented recurring bug class (3+ production incidents in CLAUDE.md), (3) pre-commit hook already has Python checks as precedent. Debate: survived all 5 challenges. Ideas 2 and 3 weakened into parking lot.

## Implementation Lag Note
Five subconscious winners remain unimplemented. This is run 8. Per run 7 mandate, the moratorium threshold is met. This run adds `moratorium_config` to governance.json. The human should implement at least 2 pending winners before run 9 to lift moratorium status.
