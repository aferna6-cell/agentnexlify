# Winning Concept — 2026-05-28 (Run 37)

## Recommendation

Add billing-constant-guard as pre-commit **Check 11** in `scripts/hooks/pre-commit` — a 10-line bash block that validates `AMOUNT_TO_PLAN` in `billing.py` contains the 4 required current-price keys `{9900, 15000, 25000, 89900}`, emitting a WARNING (not FAIL) on any missing entry.

---

## Why This, Why Now

GH #181 has been open 26 days. Direct inspection confirms `billing.py:263–279` (`AMOUNT_TO_PLAN`) contains legacy entries (`29900`, `49900`, `39900`, `79900`) but is missing the two current-price entries — `15000` (autopilot, $150/mo) and `25000` (professional, $250/mo). A Stripe webhook for either plan will fall through to `_resolve_plan`'s fallback path and return `None`, silently misrouting plan assignment. Five explicit subconscious recommendations to fix GH #181 produced no action; the mechanism was too indirect. Check 11 puts the gap in front of the developer on **every commit**, at the point of action rather than in a weekly review cycle.

Beyond GH #181: `AMOUNT_TO_PLAN` has accumulated 7 legacy entries from 3 prior price changes. Without a guard, every future pricing update risks the same drift. Check 5 (migration duplicate numbers) established the precedent — a WARNING guard that prevents a class of bug without blocking development. Check 11 follows the same pattern.

The ROI is systemic, not just incident-specific. The guard runs on every commit indefinitely, survives GH #181's eventual fix, and catches future billing constant drift at zero ongoing maintenance cost.

---

## Implementation Sketch

### Step 1: Add Check 11 to pre-commit hook

**File:** `scripts/hooks/pre-commit`

Add after the existing Check 9/10 block, before the final `exit 0`:

```bash
# Check 11: Billing constant guard
BILLING_FILE="backend/routers/billing.py"
if [ -f "$BILLING_FILE" ]; then
  REQUIRED_AMOUNTS=(9900 15000 25000 89900)
  MISSING_AMOUNTS=()
  for amt in "${REQUIRED_AMOUNTS[@]}"; do
    if ! grep -qP "^\s+${amt}:" "$BILLING_FILE"; then
      MISSING_AMOUNTS+=("$amt")
    fi
  done
  if [ ${#MISSING_AMOUNTS[@]} -gt 0 ]; then
    echo ""
    echo "WARNING (pre-commit Check 11 — billing constant guard):"
    echo "  AMOUNT_TO_PLAN in $BILLING_FILE missing entries: ${MISSING_AMOUNTS[*]}"
    echo "  Expected: 9900 (growth), 15000 (autopilot), 25000 (professional), 89900 (enterprise)"
    echo "  Fix: backend/routers/billing.py — see GH #181"
    echo ""
  fi
fi
```

Note: WARNING only — does NOT set `exit 1`. Same behavior as Check 5.

### Step 2: Commit

```bash
git add scripts/hooks/pre-commit
git commit -m "guard(billing): add pre-commit Check 11 — billing constant sentinel (WARNING)"
```

### Step 3 (future, not this PR): Wire to CI

After GH #181 is resolved, promote Check 11 to FAIL mode in `.github/workflows/pr-check.yml` by adding a direct `grep` assertion. This is the same two-phase pattern used for migration duplicate guard (Check 5 local WARNING → eventually CI enforced).

---

## Standing Actions (Unchanged)

These remain the highest-priority human-required items:

1. **GH #181 billing fix (~15 min):** `billing.py` add `15000: "autopilot"` + `25000: "professional"` to `AMOUNT_TO_PLAN`; remove `test_billing_amount_to_plan.py:38-44` backwards assertions. Check 11 will immediately suppress its WARNING once this is done.
2. **email_sequences.py split (~2h, run 35 winner):** Invoke `/god-class-splitter email_sequences.py`. Pre-condition: GH #181 fixed first.
3. **Moratorium Sprint Items A/B/D (~40 min):** check_project_invariants pre-commit Check 10, widget sync guard, CI eval workflow.
4. **post-split-test-repair SKILL.md:** Create `.claude/skills/post-split-test-repair/SKILL.md` (full content in `subconscious/runs/2026-05-27/winning-concept.md`). Any session can do this in under 1 minute.

---

## What This Replaces

Previous active direction was post-split-test-repair SKILL.md (run 36 winner — nightly review did not implement it autonomously). That item remains valid and is moved to parking lot in this run's backlog — it is NOT killed, just not the run 37 winner.

---

## Confidence

**HIGH** — Evidence is unambiguous (26-day gap, direct `grep` confirms missing entries, test file certifies broken state). Execution is autonomous (10 lines bash, same class as Check 9 added by `72f8204`). No implementation blockers. WARNING mode removes the only valid dependency argument (FAIL-before-fix). Systemic guard value survives GH #181 fix and extends to all future billing constant changes.
