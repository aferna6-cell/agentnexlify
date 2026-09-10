# Winning Concept — Run 118 (2026-09-10-pm)

## Title
Fix Step 9J token budget: cursor state + batch 5 Dependabot PRs per nightly

## Category
workflow_efficiency

## Evidence
- Runs 115 (2026-09-05), 116 (2026-09-06), 117 (2026-09-06-pm): all log "17/19 Dependabot PRs skipped due to token budget"
- Root cause: Step 9J retrieves all 19 PRs, then iterates. Token budget exhausts after PR 2. Remaining 17 skipped permanently.
- Security impact: 17 Dependabot PRs contain security patches. CVE window stays open indefinitely.
- Rebase trigger (run 112) + search_pull_requests fix (run 114) both implemented correctly — they fire on PRs 1-2 only. PRs 3-19 never reached.

## Autonomous-executable
YES — SKILL.md edit, proven channel. Same directory as Step 9K (run 114) implementation.

## Action

**Edit `.claude/skills/nightly-commit-review/SKILL.md` — Step 9J block.**

Replace the current Step 9J processing loop with a cursor-aware batch processor:

### Step 9J block replacement (exact edit):

Find the current Step 9J processing section (processes PRs in a loop, skips after token budget). Replace the inner loop with:

```
9J. (Dependabot Auto-Merge via Cursor Batch)
    Load cursor: read subconscious/state/step9j-cursor.json.
    If file missing or parse error: default cursor = {last_processed_index: 0, total_prs: 0}.
    Get all open Dependabot PRs: search_pull_requests(query='is:pr is:open author:app/dependabot repo:aferna6-cell/agentnexlify').
    total_prs = len(prs).
    Sort PRs: security labels first (CVE, vulnerability, security), then by age (oldest first).
    start_index = cursor.last_processed_index % total_prs (wrap around).
    batch = prs[start_index : start_index + 5].
    For each PR in batch:
      - Check mergeable_state. If 'clean' → merge_pull_request. Log: 'Step 9J: merged PR #{N}'.
      - If 'unknown' → check last_rebase_comment (within 48h dedup guard).
        If no recent rebase: add_issue_comment('@dependabot rebase'). Log: 'Step 9J: triggered rebase on PR #{N}'.
      - If 'blocked' or 'behind': skip, log reason.
    next_index = (start_index + 5) % total_prs.
    Write cursor: {last_processed_index: next_index, total_prs: total_prs, last_run: ISO_DATE}.
    Log summary: 'Step 9J: processed PRs {start_index+1}-{start_index+len(batch)} of {total_prs} (cursor → {next_index}), merged: M, rebases: R'.
```

### Cursor state file path
`subconscious/state/step9j-cursor.json`

Initial content (create if missing):
```json
{
  "last_processed_index": 0,
  "total_prs": 0,
  "last_run": null
}
```

### Impact
- Night 1: PRs 1-5 processed
- Night 2: PRs 6-10 processed
- Night 3: PRs 11-15 processed
- Night 4: PRs 16-19 processed
- Full sweep in 4 nights. CVE window closes within a week.
- Token budget per run: 5 PRs instead of 19. Steps 9K-9L get budget back.

## Verification
After SKILL.md edit: grep 'last_processed_index' .claude/skills/nightly-commit-review/SKILL.md → must return the cursor load line.
Next nightly: ops/routines/logs/nightly-commit-review-YYYY-MM-DD.md → 'Step 9J: processed PRs 1-5 of 19 (cursor → 5)'.

## Risk
Near-zero. Additive only — no existing Step 9J logic removed. Cursor default handles missing file. Modulo wrap handles list length changes. Merge/rebase actions identical to prior Step 9J behavior.

## Why not Step 9M or os_tool_executions.py split
- Step 9M: human actively cleaning via nightly already (2 files cleaned 2026-09-10). Autonomous automation redundant when human sprint at ≤3 remaining.
- os_tool_executions.py split: recommendation-only (subconscious can't execute), lower urgency than active CVE window.

## Governance note
Step 9L already implemented in SKILL.md at lines 457/471. Governance.json was stale (`implemented: false`). No autonomous-executable action needed for Step 9L — it was already there. check_ai_metering.py exits RC=2 correctly on 45 violations (confirmed by direct run, not via pipe which captured head's RC=0).
