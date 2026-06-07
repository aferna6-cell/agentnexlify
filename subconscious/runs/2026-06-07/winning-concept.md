# Winning Concept — 2026-06-07 (Run 52)

## Recommendation

Remove the stale "Blocked 2026-06-01" sentence from `nightly-commit-review SKILL.md:69` — a 1-line deletion that restores the autonomous Check 10 pre-commit wiring path, triggering Item A execution at tonight's 2:37 AM nightly cycle.

## Why This, Why Now

`nightly-commit-review SKILL.md:69` contains the sentence: "Blocked 2026-06-01: script fails on em-dash violations in UI copy." This sentence was accurate on June 1 but became stale when `8db33df` (2026-06-05) fixed all 5 em-dash violations. Nightly review reads this note as a signal to skip Item A entirely — without even running the pre-condition check. Two nightly cycles have now passed (2026-06-05, 2026-06-07) with zero autonomous executions of Item A, despite `check_project_invariants.py` exiting 0. The fix is a 1-line deletion. The result is Item A (wire `check_project_invariants.py` as pre-commit Check 10) firing autonomously tonight — ending a 46-day pending item without any human code change.

## Implementation Sketch

**Time: ~2 min human. Zero code required after the edit.**

### Step 1 — Remove stale blocker sentence (1-line deletion)

Edit `.claude/skills/nightly-commit-review/SKILL.md` line 69.

**Before:**
```
  **Current pending item (Item A):** Wire `check_project_invariants.py` as pre-commit Check 10. Status: `pending_autonomous`. Blocked 2026-06-01: script fails on em-dash violations in UI copy. Execute when script passes clean.
```

**After:**
```
  **Current pending item (Item A):** Wire `check_project_invariants.py` as pre-commit Check 10. Status: `pending_autonomous`. Execute when script passes clean.
```

### Step 2 — Verify pre-condition locally (optional, ~10s)
```bash
python3 scripts/check_project_invariants.py && echo "PASS — Item A will fire tonight"
```
Expected: exit 0, PASS on all 6 checks.

### Step 3 — Commit
```bash
git add .claude/skills/nightly-commit-review/SKILL.md
git commit -m "fix(nightly): remove stale Item A blocker — em-dash cleared 2026-06-05 by 8db33df

Stale note 'Blocked 2026-06-01: script fails on em-dash violations' was preventing
autonomous Check 10 wiring for 2 nightly cycles after the blocker was actually cleared.
check_project_invariants.py exits 0 — Item A fires tonight at 2:37 AM."
```

### Step 4 — Wait for tonight's nightly (2:37 AM)

Nightly will:
1. Read SKILL.md Item A block (no blocker sentence)
2. Run `python3 scripts/check_project_invariants.py`
3. See exit 0
4. Apply the Check 10 patch to `scripts/hooks/pre-commit`
5. Commit: `ci(pre-commit): wire check_project_invariants.py as Check 10`
6. Update governance.json Item A status → implemented

### Bonus A — Add Item B block to SKILL.md (~5 min, same edit session)

While in SKILL.md, add Item B block after Item A block (line 80). Content from run 50 winning-concept.md. Full block:

```markdown
  **Item B (pending_autonomous, AUTONOMOUS-EXECUTABLE):** Create `scripts/check-widget-sync.sh` + wire into `scripts/hooks/pre-push` + fix CLAUDE.md Invariant #4.

  Pre-condition: widget copies currently in sync (health-check.sh widget_sync=OK). Always true — proceed.

  Step 1 — Create `scripts/check-widget-sync.sh`:
  ```bash
  #!/usr/bin/env bash
  # Verify all 3 widget copies are byte-identical
  set -euo pipefail
  W1="widget/agentnexlify-widget.js"
  W2="frontend/public/widget/agentnexlify-widget.js"
  W3="landing-page-v2/widget/agentnexlify-widget.js"
  FAIL=0
  for pair in "$W1:$W2" "$W1:$W3" "$W2:$W3"; do
    a="${pair%%:*}"; b="${pair##*:}"
    if ! diff -q "$a" "$b" >/dev/null 2>&1; then
      echo "❌ Widget sync FAIL: $a ≠ $b"; FAIL=1
    fi
  done
  [ "$FAIL" -eq 0 ] && echo "✅ Widget sync OK" || exit 1
  ```
  chmod +x scripts/check-widget-sync.sh

  Step 2 — Add to `scripts/hooks/pre-push` (before `exit 0`):
  ```bash
  # Widget sync guard
  bash scripts/check-widget-sync.sh || exit 1
  ```

  Step 3 — Fix CLAUDE.md Invariant #4: change "2 copies" → "3 copies" and add `landing-page-v2/widget/` to the list.

  Commit: `ci(widget): add 3-copy sync guard to pre-push hook [auto-nightly-YYYY-MM-DD]`
  After commit: update governance.json run 7 status → implemented.
```

### Bonus B — Fix auth.ts timing-safe comparison (GH #206, ~5 min, human-required)

Nightly already assessed as "requires human approval." Fix in same session:

Edit `agent-service/src/auth.ts`:
```typescript
import * as crypto from 'crypto';

export function isTokenAuthorized(
  provided: string | string[] | undefined,
  expected: string,
): boolean {
  if (!expected) return true;
  const value = Array.isArray(provided) ? provided[0] : (provided ?? '');
  if (value.length !== expected.length) return false;
  return crypto.timingSafeEqual(Buffer.from(value), Buffer.from(expected));
}
```

Update `auth.test.ts` to add test: "rejects token with correct length but wrong value" and "rejects undefined token." Commit. Closes GH #206.

### Bonus C — Open GH issue: verify migration 131 applied in production (~2 min)

Migration 131 (os_routing_decision + os_model_call_log) added by `7a621a1`. No production apply confirmation. GH issue with label `ops + critical`: "Verify migration 131 applied to production Supabase for Agent OS engine."

## What This Replaces

Previous active direction (run 51): Merge PR #183 (billing fix). That recommendation is a critical standing action for the human. This recommendation enables an autonomous action that has been gated for 46 days by a stale note. Both should be done — but the SKILL.md edit fires autonomously while PR #183 requires human PR review.

## Confidence

**HIGH** — Direct textual evidence (SKILL.md:69 stale sentence confirmed in this session). Causal mechanism clear (nightly reads blocker note, skips Item A). Em-dash fix confirmed (`8db33df` 2026-06-05, governance.json run 49 implemented). Pre-condition confirmed (exit 0 in run 50). Zero ambiguity in the fix. Nightly autonomous channel proven (8 prior autonomous implementations). Implementation is a 1-line deletion with no semantic complexity.
