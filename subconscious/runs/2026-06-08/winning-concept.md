# Winning Concept — 2026-06-08 (Run 52)

## Recommendation

Verify PR #183 diff targets backend/routers/billing.py with both AMOUNT_TO_PLAN entries (15000→autopilot, 25000→professional) and corrected test assertions, then merge it — closing GH #181 after 51 days and unblocking the email_sequences.py god-class split.

## Why This, Why Now

PR #183 is 15 days old (drafted while this item was GH #181 critical standing action). The developer just shipped 5 production PRs in 3 days — Agent OS phase-3 polish (d20284f), auth hardening (abccdc3), v2 response rendering (617b667), widget isolation fix (2287f6b), and orchestration core (7a621a1). That sprint is now wrapping. Execution probability for a 10-minute billing fix is the highest it has been since GH #181 was filed on 2026-05-23. The billing gap is not getting worse but every day without it: (a) Check 11 WARNING fires on every commit, (b) email_sequences.py split remains blocked, (c) tenant pricing lookups return incorrect plan names for $150 and $250 subscriptions.

## Implementation Sketch

**Time: ~10 min. Risk: LOW (CI gate prevents incorrect merge).**

### Step 1 — Read PR #183 diff (mandatory before merge)

Verify the diff contains exactly:
1. **File: `backend/routers/billing.py`** (NOT services/billing.py)
   - AMOUNT_TO_PLAN dict near line 263
   - `15000: "autopilot"` entry present
   - `25000: "professional"` entry present
2. **File: `backend/tests/test_billing_amount_to_plan.py`**
   - Lines 38-44 backwards assertions (`test_no_wrong_15000_mapping` / `test_no_wrong_25000_mapping`) removed or inverted
   - Corrected assertions for current prices: 15000 ($150/mo autopilot) + 25000 ($250/mo professional)
   - `test_all_four_current_tiers_present` updated to use `{9900, 15000, 25000, 89900}`

If either file is wrong → do NOT merge. Create new GH issue with correct patch sketch and label `critical` + `ai-ready`.

### Step 2 — Confirm CI green on PR #183

If CI is red only because of the backwards test assertions (test_no_wrong_15000_mapping / test_no_wrong_25000_mapping), PR may be incomplete — flag to human before merging.

### Step 3 — Merge

```bash
gh pr ready 183 && gh pr merge 183 --squash
```

### Step 4 — Verify post-merge

```bash
# Confirm entries exist
grep -n "15000\|25000" backend/routers/billing.py | head -5

# Run billing tests
python3 -m pytest backend/tests/test_billing_amount_to_plan.py -v 2>&1 | tail -10
# Expected: all pass, no backwards assertions present
```

### Step 5 — Update governance

Mark GH #181 critical_standing_action → status `implemented` in governance.json.

## What This Replaces

Same as run 51 active direction: "Verify and merge PR #183 — close GH #181." No change in winner. New evidence: developer is active (5 production PRs in 3 days since run 51 was written). Execution probability is materially higher.

## Confidence

**MEDIUM-HIGH** — Evidence: billing.py confirmed missing entries (live grep run 52). Test file confirmed backwards assertions (lines 38-44 live grep run 52). Developer velocity confirms execution mode. Risk: PR #183 diff may still need path verification (Step 1 is mandatory). CI gate prevents incorrect merge.

## Bonus Actions

**Bonus A — Wire check_project_invariants.py into pre-commit as Check 10 (~5 min, do immediately)**

Item A: 41 days pending (run 8). Pre-condition met (exits 0 since 8db33df). Pre-commit currently has Check 11 but no Check 10. Add 3 lines to `scripts/hooks/pre-commit`:

```bash
# Check 10: Project invariants (schema naming, em-dash in Python)
echo -n "Check 10: Project invariants... "
python3 scripts/check_project_invariants.py && echo "PASS" || { echo "FAIL"; exit 1; }
```

**Bonus B — email_sequences.py god-class split (~2h, schedule next session)**

After PR #183 merges: GH #181 prerequisite cleared. Invoke `/god-class-splitter` on `backend/routers/email_sequences.py`. Split into `email_crud.py + email_enrollment.py + email_processor.py`. Run 41 winner (9+ days). All tooling ready: god-class-splitter SKILL.md (e848b87), post-split-test-repair SKILL.md (d481799).

**Bonus C — Agent OS isolation test coverage (~30 min, parking lot)**

Read `backend/tests/test_os_inbound_bridge.py`. If parametric coverage for `os_enabled=False` tenants across all request contexts is absent, add it. 2287f6b (2026-06-07) proved this bug class is real.
