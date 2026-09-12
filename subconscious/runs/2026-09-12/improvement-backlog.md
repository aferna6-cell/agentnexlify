# Improvement Backlog — Run 121 (2026-09-12)

## Active

- **Step 9G trigger-path replacement candidate**: The current `gh workflow run` / `gh run list` mechanism is not viable in the cloud-hosted nightly CCR environment. A GitHub Actions MCP trigger/list path is the leading candidate, but the required actions and exact schemas are **not yet verified in the actual nightly CCR execution surface**. Verify those capabilities end to end first; only then implement the Step 9G replacement in nightly-commit-review SKILL.md. Keep GH #403 separate: a working trigger does not fix the workflow's missing `ANTHROPIC_API_KEY` prerequisite. XS effort after verification, MEDIUM confidence until verified.

## Parking Lot (survived debate but not chosen)

- **Step 9E unknown-date credentials**: Extend the pending Step 9E implementation so credentials with `last_rotated = "unknown"` are surfaced for human verification using credential-identity dedup. Reuse an existing ops/human-action tracker when one already covers that credential; do not automatically file a duplicate issue. SUPABASE_ACCESS_TOKEN rotation date is still unknown.
- **Step 9M — os_tool_executions.py god-class monitor**: Add `wc -l` check + alert at 500L in nightly SKILL.md if evidence strengthens. File was 436L after 2 rapid fixes; reconsider if it reaches 480L+.
- **Step 9N — credential countdown log**: After Step 9E is actually implemented, consider logging known credentials' days-since-rotation, warning-threshold distance, and recorded due date. Unknown-date credentials must remain explicitly unknown rather than receiving fabricated countdowns.

## Rejected This Run

- None explicitly killed — Ideas 3 and 4 were weakened to parking-lot items, not killed.

## Questions for Next Run (Run 122)

1. Are the required GitHub Actions MCP trigger/list capabilities and exact schemas verified end to end in the actual nightly CCR execution surface? If yes, implement Step 9G; if not, keep the candidate unimplemented.
2. Is GH #403 still blocking `kb-autopopulate.yml` because `ANTHROPIC_API_KEY` is missing? Treat this separately from Step 9G trigger-path work.
3. Has the pending Step 9E credential escalation actually been implemented with credential-identity dedup and correct warning-vs-due-date semantics? If not, keep it pending.
4. Is SUPABASE_ACCESS_TOKEN's rotation date still unknown? If yes, surface it through the identity-deduplicated Step 9E contract rather than filing an automatic duplicate tracker.
5. Is os_tool_executions.py trending toward 480L+? If yes, reconsider promoting Step 9M.
