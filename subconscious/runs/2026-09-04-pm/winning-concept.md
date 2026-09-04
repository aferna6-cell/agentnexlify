# Winning Concept — Run 115 (2026-09-04-pm)

## Recommendation
Add Step 9M to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly AI usage metering coverage sweep that greps for Claude API calls in backend routers lacking a usage guard, and files a `security+ai-ready` GH issue per unguarded file.

## Why This, Why Now
Two PRs in 3 days added missing `reserve/record/release` metering to `extract_action_items` (widget, #793) and `live-AI respond` (voice, #792) — different subsystems, same miss class. This is identical to the `block_demo_role` recurrence pattern that spawned Step 9I (two issues in 6 days, nightly-2026-08-18 manual sweep found 100+ violations). Each unmetered AI endpoint silently leaks revenue; the reserve/record/release pattern is not enforced by any automated check. Step 9M closes this class permanently using the same autonomous-executable SKILL.md-edit channel that delivered Steps 9F through 9K without human approval delays.

## Implementation Sketch
1. Edit `.claude/skills/nightly-commit-review/SKILL.md` — insert Step 9M block after Step 9K and before the "10. Commit report" step.

**Step 9M block to insert:**
```markdown
### Step 9M — AI Usage Metering Coverage Sweep

1. Find router files with AI calls:
   ```bash
   grep -rln "call_claude_messages\|claude_client\.messages\|anthropic_client\|AnthropicClient" backend/routers/
   ```
2. For each file found, check if usage guard is present:
   ```bash
   grep -l "ai_usage_guard\|reserve_tokens\|check_ai_budget\|block_demo_role" <file>
   ```
   A file passes if it imports OR calls any of the guard patterns. Skip files under `backend/routers/admin/` (intentionally unguarded internal endpoints).
3. Collect files that have AI calls but NO usage guard reference.
4. Dedup: for each unguarded file, check if an open GH issue already references the filename with label `ai-ready`. Skip if yes.
5. For each new unguarded file: file GH issue with labels `security`, `ai-ready`:
   - Title: `fix(metering): AI usage metering missing in {filename}`
   - Body: List AI call lines found, explain reserve/record/release pattern needed, reference backend/tests/test_widget_extract_action_items_usage_guard.py as example test.
6. Log to nightly report:
   - `Step 9M: {N} AI-router files checked, {M} unguarded, {K} new issues filed`
   - If 0 unguarded: `Step 9M: All AI router files have usage metering — PASS`
```

2. Commit: `feat(nightly): add Step 9M AI usage metering coverage sweep`

## What This Replaces
Active direction: Step 9K (implemented run 114). Step 9M is the next step in the Step 9x series addressing systematic code-health gaps via nightly automation.

## Confidence
**HIGH** — identical pattern to Step 9I (block_demo_role sweep), which was approved and implemented at 1st carry-forward (run 107). Two metering incidents in 3 days provides stronger frequency signal than Step 9I's two incidents in 6 days. Grep-based approach with dedup guard proven across Steps 9I, 9J, 9K. Zero architectural risk — SKILL.md edit only, no code changes, no migrations. Admin route exclusion prevents false positives on intentionally unguarded internal paths. Test file reference (test_widget_extract_action_items_usage_guard.py) gives implementers a concrete example to follow.

## Run 116 Mandate
1. Verify Step 9M present in .claude/skills/nightly-commit-review/SKILL.md: `grep 'Step 9M'` — SHOULD PASS if human approves winner.
2. If Step 9M absent on run 116: escalate directly per autonomous-executable governance precedent (3rd-carry-forward → implement directly; 1st-carry-forward → implement in run 116 if SKILL.md edit is safe).
3. First nightly after Step 9M: does log contain 'Step 9M:' line? How many unguarded files found?
4. Step 9L (migration alerter, parking lot): has PR #788 (check_schema_log_migrations.py) been merged? If yes: Step 9L is unblocked for run 116.
5. os_tool_executions.py: now 4+ days stable. Re-evaluate god class split as run 116 candidate.
6. GH #684 SUPABASE_ACCESS_TOKEN: resolved? Brain connector health?
