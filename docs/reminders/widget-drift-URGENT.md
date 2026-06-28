# URGENT: Widget Byte-Sync Drift — Human Task Required

**Status:** HUMAN-ONLY. Retired from subconscious after run 70. No further automation.

**Created:** 2026-06-28 (run 70 mandate)

---

## The Problem

`check_project_invariants.py` Invariant #4 has failed for **6 consecutive subconscious runs** (runs 65–70):

```
FAIL widget assets are byte-identical across mirrors
  - drift: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js
```

The `landing-page-v2/` copy is stale since the referral sprint (PRs #368–371). The canonical source (`widget/agentnexlify-widget.js`) has been updated but the mirror has not been synced.

---

## The Fix (1 Command, <5 Seconds)

```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
```

Then commit:
```bash
git add landing-page-v2/widget/agentnexlify-widget.js
git commit -m "fix: sync landing-page-v2 widget mirror — resolves invariant #4"
```

---

## Why Subconscious Could Not Fix This

`landing-page-v2/` is on the nightly SKILL.md FORBIDDEN paths list (legacy code protection). The subconscious loop respects this boundary and cannot autonomously sync the file.

The fix requires **human judgment** to confirm:
1. `landing-page-v2/` is legacy-safe to update
2. The canonical `widget/agentnexlify-widget.js` is the correct source
3. No other files in `landing-page-v2/widget/` need updating

---

## Why This Matters

- `check_project_invariants.py` exits 1 → Pre-commit Check 13 blocks (in environments where hooks are installed)
- Widget drift means embedded tenants on the landing-page-v2 domain could load a stale widget version
- PLAN-NAME-GUARD and PRE-COMMIT-AUTOSYNC improvements in the backlog are sequencing-blocked until this clears

---

## History

| Run | Date | Recommendation | Human Action |
|-----|------|----------------|--------------|
| 65 | 2026-06-22 | Sync the file | Not actioned |
| 66 | 2026-06-23 | Add to nightly Step 9B exception | Not actioned |
| 67 | 2026-06-24 | Pre-commit autosync rule | Not actioned |
| 68 | 2026-06-25 | Hard deadline warning | Not actioned |
| 69 | 2026-06-27 | Hybrid: Step 9B exception + run 70 mandate | Not approved before run 70 |
| 70 | 2026-06-28 | **MANDATE FIRED. Topic retired. This file written.** | **ACTION REQUIRED** |

---

## What Happens Next

- This file persists until a human resolves the drift
- Subconscious will NOT generate further widget-drift ideas
- Once resolved: delete this file, confirm invariant script passes, remove from reminder backlog
- After resolution: PLAN-NAME-GUARD and PRE-COMMIT-AUTOSYNC can proceed

---

## Action Required

Run the `cp` command above. Takes under 5 seconds.
