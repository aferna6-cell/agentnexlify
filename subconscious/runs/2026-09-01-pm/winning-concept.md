# Winning Concept — Run 116 (2026-09-01-pm)

## Recommendation
Add Step 9L to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly connector auth pattern scan that greps `backend/services/*_connector.py` for 401/refresh/retry handling, logs missing files, and files a GH issue (labels: `security, ai-ready`) when violations are found.

## Why This, Why Now
Commit 8a60a59 (2026-08-30) added 101 lines of 401 retry logic to `gmail_connector.py` — evidence a production connector was shipping without auth failure handling. `connector_awareness.py` and `connector_registry.py` have no equivalent handling. The M8 sprint is adding connectors at pace, meaning the gap will recur. Step 9I proved the nightly grep → file issue → issue-to-pr-loop mechanism; Step 9L applies the same mechanism to connector auth. Autonomous-executable (SKILL.md bash block), zero new infrastructure, fires on next nightly run.

## Implementation Sketch
1. Edit `.claude/skills/nightly-commit-review/SKILL.md` — insert Step 9L block after Step 9K's summary line and before "10. Commit report".

**Step 9L block to insert:**
```markdown
### Step 9L — Connector Auth Pattern Scan

1. Find all connector files: `find backend/services -name "*_connector.py" 2>/dev/null`.
2. For each file, check whether it contains any of: `401`, `refresh`, `retry`.
3. Collect `missing_auth` list = files with none of those strings.
4. If `missing_auth` is empty:
   - Log: "Step 9L: all connectors have 401/refresh/retry handling — PASS"
   - Skip remaining steps.
5. If `missing_auth` is non-empty:
   - Log to nightly report: "Step 9L: {len(missing_auth)} connector(s) missing auth handling: {list}"
   - Add warning: "⚠ Step 9L: connector auth gaps — security risk"
   - Check for open GH issue titled "Step 9L: connector auth gaps" via `mcp__github__search_issues` (state:open label:security).
   - If no duplicate: file issue via `mcp__github__issue_write` with title "Step 9L connector auth gap: {filename}", body listing the file + what pattern is missing, labels `security, ai-ready`.
6. Add to nightly report summary: "Step 9L: {total connector count} connectors checked, {len(missing_auth)} flagged"
```

2. **Bonus (same commit):** Add a brief connector auth patterns note to `knowledge-base/raw/` for next KB compile — captures the derived-key + 401 retry pattern from the Gmail sprint.

3. Commit: `feat(nightly): add Step 9L nightly connector auth pattern scan`

## What This Replaces
Active direction: run 114 winner (Step 9K stale subconscious PR audit — IMPLEMENTED and firing correctly). Step 9L is the next governance step.

## Confidence
**HIGH** — production evidence (commit 8a60a59 fixing real auth failure); mechanism proven (Step 9I); zero production code changes; Step 9I/9J/9K all validated the same autonomous-executable SKILL.md channel; grep pattern is conservative (flags absence, not presence of bugs); dedup guard via GH issue search already used in Step 9C/9I.

## Run 117 Mandate
1. Verify Step 9L fires in nightly-2026-09-02: `grep 'Step 9L' ops/routines/logs/nightly-commit-review-2026-09-02.md`
2. How many connectors flagged? Which files?
3. os_tool_executions.py: stable (0 commits 4d+)? If yes: file GH issue for god-class split.
4. GH #684 SUPABASE_ACCESS_TOKEN: set in Railway?
5. M8 OAuth/service_role HOLD resolved? Calendar+CRM deploy progress?
6. Step 9K: stale subconscious PR count — approaching escalation threshold (≥5 or any >60d)?
