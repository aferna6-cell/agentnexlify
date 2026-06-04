# Winning Concept — 2026-06-04 (Run 49)

## Recommendation

Fix exactly 5 JSX em-dash violations — a ~2-min string substitution across 5 UI files — allowing `check_project_invariants.py` to exit 0 and the nightly autonomous chain to wire Check 10 at 2:37 AM tonight.

## Why This, Why Now

Run 48 combined Items A+B into a ~25-min commit. Zero implementation in 24h. The pattern across 34 moratorium days is stark: items requiring >15 minutes human commitment go undone; items with sub-5-minute activation energy succeed (e.g., Check 11 bash block wired by nightly 061582c, SKILL.md extension wired by nightly 4226ef4). The 5 em-dash violations are UI string literals — no logic, no tests, no risk. Each is a 1-character change. Nightly 2026-06-03 explicitly wrote: "Fix em dashes in 5 UI files → unblocks Item A." The autonomous chain from run 43 (4226ef4) is already primed: once `check_project_invariants.py` exits 0, the nightly review at 2:37 AM adds Check 10 to `scripts/hooks/pre-commit` automatically. Widget copies are currently in sync (invariants PASS), so Item B's absence causes no active harm while this runs.

## Implementation Sketch

**Time: ~2 min. Files: 5. Risk: zero.**

### Step 1 — Fix the 5 em-dashes

Open each file and replace `—` (em dash, U+2014) with `-` (hyphen) or appropriate punctuation:

**`frontend/src/pages/IntegrationsPage.jsx:1018`**
Find the line containing `—` in UI copy and replace with `-` or remove.

**`frontend/src/pages/SettingsInboundChannels.jsx:220`**
Find the line containing `—` in UI copy and replace with `-` or remove.

**`frontend/src/pages/SettingsInboundChannels.jsx:221`**
Find the line containing `—` in UI copy and replace with `-` or remove.

**`frontend/src/pages/settings/MessagingSettingsCards.jsx:263`**
Find the line containing `—` in UI copy and replace with `-` or remove.

**`frontend/src/pages/settings/MessagingSettingsCards.jsx:276`**
Find the line containing `—` in UI copy and replace with `-` or remove.

### Step 2 — Verify

```bash
python3 scripts/check_project_invariants.py
# Expected: all 6 checks PASS, exit 0
```

### Step 3 — Commit

```bash
git add frontend/src/pages/IntegrationsPage.jsx \
        frontend/src/pages/SettingsInboundChannels.jsx \
        frontend/src/pages/settings/MessagingSettingsCards.jsx
git commit -m "fix: replace em dashes with hyphens in UI copy (personality.md rule)

Fixes 5 em-dash violations in JSX UI strings so check_project_invariants.py
exits 0. Unblocks autonomous Check 10 wiring (nightly 2026-06-04 at 2:37 AM).

Files: IntegrationsPage.jsx:1018, SettingsInboundChannels.jsx:220-221,
MessagingSettingsCards.jsx:263/276."
```

### Step 4 — What happens tonight (autonomous)

At 2:37 AM the nightly-commit-review runs. It will:
1. Verify `check_project_invariants.py` exits 0 (your commit clears the blocker)
2. Add Check 10 to `scripts/hooks/pre-commit` (the 3-line bash block)
3. Commit and push

Item A closes automatically without further human action.

## Bonus Actions (after the commit, in order of effort)

**Bonus A — Item B: create widget sync guard (~15 min)**
```bash
# Create scripts/check-widget-sync.sh
# Wire into scripts/hooks/pre-push
# Fix CLAUDE.md Invariant #4: 2 copies → 3 copies
```
Script template in `subconscious/runs/2026-06-03/winning-concept.md §Step 2`.

**Bonus B — GH #181 billing fix (~15 min, path now confirmed)**
File: `backend/routers/billing.py:263`
Add to AMOUNT_TO_PLAN dict:
```python
15000: "autopilot",    # $150/mo
25000: "professional", # $250/mo
```
Update `backend/tests/test_billing_amount_to_plan.py`: remove backwards assertions (lines 38-44), add current-price assertions, update `test_all_four_current_tiers_present` to use `{9900, 15000, 25000, 89900}`. Silences Check 11 WARNING. Closes GH #181.

## What This Replaces

Run 48 active direction: "Fix 5 JSX em-dash violations + create scripts/check-widget-sync.sh in single commit (Items A+B combined)." Run 49 de-couples A from B — same Item A action, no longer bundled with B. The ~25-min commitment was the barrier. Item B remains valid as Bonus A.

## Confidence

**HIGH** — Evidence: exact file:line violations confirmed by direct invariants run this session; nightly log 2026-06-03 confirms the autonomous chain is primed; personality.md rule is clear (em-dashes banned); fix is 5 string literals with zero logic risk; autonomous Check 10 wiring has been verified as a working path (4226ef4 extended scope, 2:37 AM cadence confirmed).
