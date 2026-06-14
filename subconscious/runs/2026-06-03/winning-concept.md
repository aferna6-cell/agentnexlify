# Winning Concept — 2026-06-03 (Run 48)

## Recommendation

Fix 5 JSX em-dash violations AND create `scripts/check-widget-sync.sh` in a single ~25-minute human commit, closing Items A and B simultaneously.

## Why This, Why Now

Item D was implemented autonomously tonight (nightly 42992fa) — the 4-run autonomous infrastructure chain (runs 42→43→44→47) fully delivered. That same autonomous channel is **primed and ready** for Item A the moment `check_project_invariants.py` exits 0. The only thing standing between "Item A still blocked" and "Item A auto-wires at 2:37 AM tonight" is 5 lines of JSX copy. The em-dash fix is not the workaround (scoping the Python script) — it is the correct fix per CLAUDE.md personality rules. Item B (widget sync guard) pairs naturally: same ~15 min effort, same pre-push/pre-commit guard category, same commit. Together they close 2 moratorium items in one session and activate an autonomous chain for a third.

## Implementation Sketch

### Step 1 — Fix 5 JSX em-dashes (~10 min)
Replace em-dashes (`—`) with hyphens (`-`) in:
- `frontend/src/pages/IntegrationsPage.jsx:1018`
- `frontend/src/pages/SettingsInboundChannels.jsx:220`
- `frontend/src/pages/SettingsInboundChannels.jsx:221`
- `frontend/src/pages/settings/MessagingSettingsCards.jsx:263`
- `frontend/src/pages/settings/MessagingSettingsCards.jsx:276`

Verify: `python3 scripts/check_project_invariants.py` → exits 0 (all 6 checks PASS).

### Step 2 — Create widget sync guard (~15 min)
Create `scripts/check-widget-sync.sh`:
```bash
#!/usr/bin/env bash
# Fail if any of the 3 widget copies diverge from the canonical source
set -e
CANONICAL="widget/agentnexlify-widget.js"
COPY1="frontend/public/widget/agentnexlify-widget.js"
COPY2="landing-page-v2/widget/agentnexlify-widget.js"

fail=0
for copy in "$COPY1" "$COPY2"; do
    if ! diff -q "$CANONICAL" "$copy" > /dev/null 2>&1; then
        echo "FAIL widget sync: $copy differs from $CANONICAL"
        fail=1
    fi
done
[ $fail -eq 0 ] && echo "PASS widget copies in sync" || exit 1
```

Wire into `scripts/hooks/pre-push`:
```bash
bash scripts/check-widget-sync.sh || exit 1
```

### Step 3 — Fix CLAUDE.md Invariant #4 (~1 min)
Change: `Widget JS byte-identical in widget/ AND frontend/public/widget/`
To: `Widget JS byte-identical in widget/ AND frontend/public/widget/ AND landing-page-v2/widget/`

### Step 4 — Commit
```bash
git add frontend/src/pages/IntegrationsPage.jsx \
        frontend/src/pages/SettingsInboundChannels.jsx \
        frontend/src/pages/settings/MessagingSettingsCards.jsx \
        scripts/check-widget-sync.sh \
        scripts/hooks/pre-push \
        CLAUDE.md
git commit -m "fix: resolve em-dash violations + add widget 3-copy sync guard (Items A+B)

- Replace 5 em-dashes in JSX UI copy (personality.md rule)
- check_project_invariants.py now exits 0 → nightly auto-wires Check 10
- Add scripts/check-widget-sync.sh (diff 3 widget copies, FAIL on diverge)
- Wire widget sync into scripts/hooks/pre-push
- Fix CLAUDE.md Invariant #4: 2 copies → 3 copies

Closes Items A and B. Triggers autonomous Check 10 wiring (nightly 2026-06-04)."
```

## Bonus Actions (do if time permits after the commit)

**Bonus A — GH #181 billing fix (~15 min):**
Add to `backend/routers/billing.py:263` AMOUNT_TO_PLAN dict:
```python
15000: "autopilot",    # $150/mo
25000: "professional", # $250/mo
```
Update `backend/tests/test_billing_amount_to_plan.py`: remove backwards assertions, add current-price assertions. Silences Check 11 Warning. Closes GH #181. PR #183 update path reference to `backend/routers/billing.py`.

**Bonus B — moratorium-sprint for remaining items (~40 min):**
After Items A+B committed: invoke `/moratorium-sprint` to execute any remaining S-effort items. With A+B done, sprint is much lighter.

## What This Replaces

Previous active direction was run 47: "Item D AUTONOMOUS-EXECUTABLE — extend nightly scope to CI YAML creation." Item D is now implemented (nightly 42992fa). Run 48 advances to the next most-progressed pending items (A and B).

## Confidence

**HIGH** — Evidence: exact file:line violations known (nightly log); em-dash ban is documented CLAUDE.md rule; widget sync guard script is straightforward bash; prior guard scripts (Check 9, Check 11) confirm the pattern works; both items are <15 min each; autonomous channel for Check 10 is primed (4226ef4).

## Governance Corrections Applied This Run

- Run 47 / Item D: status `pending_autonomous` → `implemented` (nightly 42992fa, 2026-06-03)
- `runs_implemented`: 12 → 13
- `implementation_lag_warning.runs_pending_approval`: 16 → 15
