# URGENT: Widget Byte-Sync Drift — Run 70 Mandate

**Status:** BLOCKING pre-commit Check 13 since 2026-06-23 (4+ days)
**Retired from subconscious:** run 70 (2026-06-27-pm) — no further debate, no extensions
**Delivery attempts exhausted:** 6 consecutive subconscious runs, 3 nightly review attempts

## Fix (30 seconds)

```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
python3 scripts/check_project_invariants.py
```

If check exits 0, commit the sync:
```bash
git add landing-page-v2/widget/agentnexlify-widget.js
git commit -m "fix: sync widget to landing-page-v2 mirror (widget drift, run 70 mandate)"
```

## Why This Got Stuck

`landing-page-v2/` is on the FORBIDDEN paths list for nightly-commit-review (legacy code protection).
The fix is a file-sync operation, not a code change — the protection is correct for code edits,
but blocks this 1-file cp. Run 70 mandate retires the topic; only human can execute.

## What Was Drifted

`widget/agentnexlify-widget.js` != `landing-page-v2/widget/agentnexlify-widget.js`

The `frontend/public/widget/` mirror is already in sync. Only `landing-page-v2/widget/` needs updating.

## Invariant Rule (CLAUDE.md)

Widget JS must be byte-identical in:
- `widget/agentnexlify-widget.js` (source of truth)
- `frontend/public/widget/agentnexlify-widget.js` (already synced)
- `landing-page-v2/widget/agentnexlify-widget.js` (needs cp above)

## After the Fix

Once check exits 0, pre-commit unblocks and the following queue opens:
1. Plan-name invariant guard Check 7 (AUTONOMOUS-EXECUTABLE, nightly can deliver)
2. AI-to-Human Handoff v1 sprint (run 70 winner, human required)
3. Moratorium exit sprint (true_pending drops toward ≤2 threshold)

## Retirement

Widget drift is permanently retired from the subconscious improvement loop as of run 70.
This file is the permanent reminder. Subconscious will not recommend this again.
