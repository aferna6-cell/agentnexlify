# Milestone 6 status

Branch: `cursor/m6-decision-intelligence-9a81`
Base: current `main` (do not merge #693 wholesale; do not auto-merge #698–#703).

## Recommendation

**MILESTONE 6 HOLD** until:

1. This branch is reviewed and merged to `main` (harness + semantics are not on production `main` until then).
2. Haiku bakeoff legs are either run with a key or accepted as excluded from the winner set (skipped here — no `ANTHROPIC_API_KEY`).
3. Live controlled Gmail send is approved by Aidan, or accepted as “prepared and blocked at the owner-authorization boundary.”

Frozen 215 gate on this branch: **0 unsafe** (`5f5493f9`, offline heuristic). See `frozen-215-results.md`.

## What this branch contains

| Workstream | State |
|---|---|
| A — action eval harness | On this branch. Safety-gate + full 215: **0 unsafe**. |
| B — semantic pipeline | Four-axis intent, resolution seam (`exact/unique/multiple/none`), capability-based department scoring. Policy/approval/idempotency untouched. |
| C — communication capabilities | Explicit allow-list. Default **Sales only**. `SEND_EMAIL_ENABLED` still default OFF. |
| D — router bakeoff | validation-v3 only. Winner documented: `heuristic→tfidf`. **Not** auto-promoted into `classify()`. |
| E — Gmail proof | FakeGmailPort contract test. Live send **not** run. |
| F — PR cleanup | Classification in `pr-cleanup.md`. Research PRs commented, not destroyed. |

## Production flags

No production environment flag was changed. `SEND_EMAIL_ENABLED` remains default OFF.
