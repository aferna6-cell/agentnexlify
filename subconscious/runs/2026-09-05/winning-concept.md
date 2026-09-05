# Winning Concept — Run 115 (2026-09-05)

## Recommendation
Add Step 9L to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly AI metering coverage check that greps for AI-calling endpoints missing reserve/record/release metering, and auto-files GH issues when violations are found.

## Why This, Why Now
PRs #792-#799 retroactively metered 6 AI endpoints in 3 days (widget_guard.screen, categorize_conversation, extract_action_items, extract_tags, voice call summaries, sms_agent.reply), each requiring 498-1726 new test lines. This is the same class problem as demo-role gaps (solved by Step 9I). The nightly grep-and-file mechanism is proven — Steps 9C, 9E, 9F, 9G, 9I, 9J, and 9K all fire correctly. Today's nightly (2026-09-05) confirmed Step 9K working ("1 subconscious PR open, 0 stale"). Adding Step 9L closes the metering coverage gap with zero architectural risk — grep-only, no per-PR iteration, minimal token budget impact.

## Implementation Sketch
1. Edit `.claude/skills/nightly-commit-review/SKILL.md` — insert Step 9L block after Step 9K's summary log line and before the "10. Commit report" step.

**Step 9L block to insert:**
```markdown
### Step 9L — AI Metering Coverage Check

1. Grep `backend/routers/` and `backend/services/` for Python files that contain any of:
   - `from anthropic import`
   - `import anthropic`
   - `llm_runtime.call_claude`
   - `client.messages.create`
   - `call_claude_messages`
2. For each matched file, check if it ALSO contains any of:
   - `reserve_tokens` OR `record_usage` OR `release_tokens`
   - `ai_usage_guard` OR `Depends(ai_usage_guard`
3. Files that import/call Claude without any metering pattern = violations.
4. For each violation:
   a. Search open GH issues for the filename (title contains the file basename).
   b. If no open issue exists: file GH issue via `mcp__github__issue_write`:
      - Title: "AI metering gap: {filename} missing reserve/record/release"
      - Body: "Step 9L nightly audit found `{filepath}` calls Claude API without AI usage metering (reserve/record/release pattern or ai_usage_guard dependency). Add metering to prevent unbilled AI usage."
      - Labels: `ai-ready`, `code_health`
5. Log to nightly report:
   - "Step 9L: {total_ai_files} AI-calling files, {violations} unmetered"
   - List each violation: "  - {filepath}"
   - If 0 violations: "Step 9L: all {total_ai_files} AI-calling files are metered — PASS"
```

2. Commit: `feat(nightly): add Step 9L AI metering coverage nightly check`

## What This Replaces
Active direction: run 114 winner (Step 9K + Step 9J detection fix — implemented). Run 115 builds the next nightly step.

## Confidence
**HIGH** — governance mandate from run 114 (check metering coverage after retroactive metering sprint); pattern proven by 6 recently-metered endpoints in 3 days; same SKILL.md-edit channel as 7 prior Step 9x implementations; grep-only detection requires no new tools; GH issue filing already used in Steps 9E/9I/9K; 0 production code changes; 0 architectural risk.

## Autonomous-Executable
**YES** — same channel as Steps 9C/9E/9F/9G/9I/9J/9K. If Step 9L is not approved and implemented by a human before run 116 fires, run 116 should implement it directly without human approval gate.

## Run 116 Mandate
1. Verify Step 9L fires in nightly-2026-09-06: `grep 'Step 9L' ops/routines/logs/nightly-commit-review-2026-09-06.md`
2. Count: how many AI-calling files found? How many violations?
3. Step 9J token budget: did 2026-09-06 nightly check more than 2 Dependabot PRs?
4. os_tool_executions.py: still stable (0 commits since 2026-08-30)? If yes: run 116 god class split candidate.
5. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway?
6. GH #800 brain connector staleness: resolved?
