# Winning Concept — 2026-06-07-pm (Run 52)

## Recommendation

Fix the timing-safe token comparison in `agent-service/src/auth.ts` — replace `===` with `crypto.timingSafeEqual` to close the timing side-channel vulnerability in the Agent OS v2 auth gate (GH #206).

## Why This, Why Now

Agent OS v2 shipped this week (7a621a1, 7,640 insertions) with a new shared-secret auth layer between FastAPI and the agent-service orchestration core. Nightly review 2026-06-07 filed GH #206: `isTokenAuthorized` uses `value === expected` — JavaScript string comparison is not constant-time, exposing a timing side-channel. DEPLOY.md (added in the same commit) signals public deployment is being planned. The widget hijack bug (2287f6b, same week) proves that Agent OS changes produce regressions. Fixing a 2-line auth vulnerability in fresh code costs 2 minutes now vs. months after an incident. This is the only recommendation in 52 runs that addresses a security finding in the new agent-service TypeScript layer.

## Implementation Sketch

**Time: ~5 min. Risk: LOW (additive change, covered by existing auth tests).**

### Step 1 — Edit agent-service/src/auth.ts

```typescript
import * as crypto from "crypto";  // add at top (may already be imported)

export function isTokenAuthorized(
  provided: string | string[] | undefined,
  expected: string,
): boolean {
  if (!expected) return true;
  const value = Array.isArray(provided) ? provided[0] : provided;
  if (!value || value.length !== expected.length) return false;
  return crypto.timingSafeEqual(Buffer.from(value), Buffer.from(expected));
}
```

Key changes:
- Add `import * as crypto from "crypto"` (Node.js builtin, no new deps)
- Guard: `if (!value || value.length !== expected.length) return false;` — prevents `timingSafeEqual` throw on undefined or mismatched lengths
- Replace `return value === expected;` with `crypto.timingSafeEqual(...)`

### Step 2 — Run existing auth tests

```bash
cd agent-service && npm test -- --testPathPattern=auth
```

Expected: all existing tests pass. If `isTokenAuthorized` tests assert on undefined/mismatched cases, they may need minor updates (add explicit false assertions for undefined input).

### Step 3 — Close GH #206

Comment on GH #206: "Fixed in <commit>. `crypto.timingSafeEqual` with equal-length guard. Tests pass."

---

## AUTONOMOUS-EXECUTABLE — Item A: Wire Check 10 to Pre-Commit (Nightly 2026-06-08)

**Pre-condition check:** Run `python3 scripts/check_project_invariants.py` — must exit 0. (Pre-condition confirmed met: 8db33df em-dash fix 2026-06-05.)

**Governance entry:** `active_directions` entry "Wire check_project_invariants.py into pre-commit as Check 10" — status `pending_autonomous`, `autonomous_executable: true`.

**Patch (apply verbatim before `exit 0` in `scripts/hooks/pre-commit`):**
```bash
# Check 10 — project invariants (client_id, status, areas_of_interest)
if python3 scripts/check_project_invariants.py > /dev/null 2>&1; then
  python3 scripts/check_project_invariants.py || { echo "❌ Pre-commit: check_project_invariants.py failed"; exit 1; }
fi
```

**Commit:** `ci(pre-commit): wire check_project_invariants.py as Check 10 [auto-nightly-YYYY-MM-DD]`

**After commit:** Update `governance.json` entry "Wire check_project_invariants.py into pre-commit as Check 10" → status `implemented`.

---

## Bonus Action A — Merge PR #183 (GH #181 Billing Fix, ~10 min, human)

1. Read PR #183 diff — verify file is `backend/routers/billing.py` (NOT services/billing.py), contains `15000: "autopilot"` and `25000: "professional"` in AMOUNT_TO_PLAN, test file removes backwards assertions
2. Check CI green
3. `gh pr ready 183 && gh pr merge 183 --squash`
4. `grep -n "15000\|25000" backend/routers/billing.py` — verify entries present
5. Update governance.json GH #181 critical_standing_action → status `implemented`

## Bonus Action B — Create GH Issue for Migration 131 Production Apply (~2 min)

Nightly 2026-06-07 flagged: migration 131 (os_routing_decision, os_model_call_log) must be applied to production Supabase. Create issue with label `operational`, `ai-ready`:

"ops: verify/apply migration 131 to production Supabase — required for Agent OS v2 (adds os_routing_decision, os_model_call_log tables; already has RLS + client_id scoping). Check if applied: `SELECT tablename FROM pg_tables WHERE tablename IN ('os_routing_decision', 'os_model_call_log');`"

## What This Replaces

Previous active direction (run 51): "Verify and merge PR #183" — that remains the most important Bonus Action. The primary recommendation shifts to the new GH #206 security finding from this cycle's evidence window. Embedded AUTONOMOUS-EXECUTABLE directive for Item A restores the nightly trigger broken by run 51's non-AUTONOMOUS winning concept.

## Confidence

**HIGH** — GH #206 filed yesterday by nightly review from direct code inspection. Fix is a known Node.js cryptographic best practice with zero ambiguity. 2-line change. Existing test suite covers the auth function. Evidence: nightly log 2026-06-07, auth.ts read directly this run (line 14: `return value === expected;`).
