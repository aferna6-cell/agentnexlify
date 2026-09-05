# Winning Concept — Run 115 (2026-09-04-pm)

## Recommendation
Add Step 9M to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly AI usage metering coverage sweep that detects Claude API calls in backend router functions lacking a usage guard, and files a `security+ai-ready` GH issue per unguarded call site.

## Naming Note (cross-session collision)
This session (run 115, 2026-09-04-pm) recommends **Step 9M**. A separate session (run 116-predecessor, 2026-09-05-am) pushed onto the same PR branch recommending "Step 9L". These are two distinct recommendations from different runs on the same PR branch — a cross-session governance collision. Run 116 must resolve: confirm Step 9M (this artifact) is the metering sweep; confirm what the 2026-09-05-am session's "Step 9L" actually recommends and assign it its own step number. The PR title "Step 9L" reflects the collision, not this run's intent.

## Why This, Why Now
Two PRs in 3 days added missing `reserve/record/release` metering to `extract_action_items` (widget, #793) and `live-AI respond` (voice, #792) — different subsystems, same miss class. This is identical to the `block_demo_role` recurrence pattern that spawned Step 9I (two issues in 6 days, nightly-2026-08-18 manual sweep found 100+ violations). Each unmetered AI endpoint silently leaks revenue; the reserve/record/release pattern is not enforced by any automated check. Step 9M closes this class permanently using the same autonomous-executable SKILL.md-edit channel that delivered Steps 9F through 9K without human approval delays.

## Implementation Sketch
1. Edit `.claude/skills/nightly-commit-review/SKILL.md` — insert Step 9M block after Step 9K and before the "10. Commit report" step.

**Step 9M block to insert:**
```markdown
### Step 9M — AI Usage Metering Coverage Sweep

**Detector scope: call-site/function level, not file level.**
A file passes only when the SPECIFIC FUNCTION containing the AI call also
contains the usage guard — guard text in a different function does not count.

**Path exclusions** (stored in `.claude/state/step9m_exclusions.json`):
Load exclusions from that file before scanning. Default exclusions:
- `backend/routers/admin/**` — intentionally unguarded internal endpoints (owner: engineering, expires: never)
- `backend/routers/internal/**` — service-to-service routes, no tenant billing context (owner: engineering, expires: never)
Do not hard-code exclusions in this script; read from the JSON so they can be
updated without changing the SKILL.

**Alias/import handling:**
Before scanning, build an alias map from each file's imports:
```bash
grep -n "^\(from\|import\).*\(call_claude_messages\|claude_client\|anthropic_client\|AnthropicClient\)" <file>
```
Treat aliased names as AI call patterns for that file (e.g. `from ... import call_claude_messages as llm_call` → also grep for `llm_call(`).

---

**Algorithm:**

1. Load exclusion list from `.claude/state/step9m_exclusions.json`. Build set of excluded path prefixes.

2. Find router files with AI calls (file-level pre-filter):
   ```bash
   grep -rln "call_claude_messages\|claude_client\.messages\|anthropic_client\|AnthropicClient" backend/routers/
   ```
   Filter out any path matching an excluded prefix.

3. For each candidate file:
   a. Build alias map (step above).
   b. Find all AI call sites with line numbers:
      ```bash
      grep -n "<ai_patterns_including_aliases>" <file>
      ```
   c. For each call site line N:
      - Scan upward from line N to find the nearest enclosing `def` or `async def` — this defines the function start.
      - Scan downward from the function start to find the next `def`/`async def` at the same indentation — this defines the function end.
      - Extract the function body (lines [function_start, function_end)).
      - Check if the function body contains any guard reference:
        ```
        ai_usage_guard|reserve_tokens|check_ai_budget|block_demo_role
        ```
      - If NO guard found in the function body → this call site is UNGUARDED.
   d. Collect all unguarded call sites as `(file, function_name, line_number)` tuples.

4. Dedup: for each unguarded `(file, function_name)` pair, check if an open GH issue
   already references `{filename}::{function_name}` with label `ai-ready`. Skip if yes.

5. For each new unguarded call site: file GH issue with labels `security`, `ai-ready`:
   - Title: `fix(metering): AI usage metering missing in {filename}::{function_name}()`
   - Body:
     - AI call line(s) found in that function
     - Explain reserve/record/release pattern needed
     - Reference `backend/tests/test_widget_extract_action_items_usage_guard.py` as example test
     - Reference `backend/tests/test_step9m_detector.py` for detector regression cases

6. Log to nightly report:
   - `Step 9M: {N} router files scanned, {F} functions checked, {M} unguarded call sites, {K} new issues filed`
   - If 0 unguarded: `Step 9M: All AI router functions have usage metering — PASS`
```

2. Add `.claude/state/step9m_exclusions.json` (new file):
```json
{
  "_comment": "Exclusions for Step 9M AI usage metering coverage sweep. Each entry requires owner and expires.",
  "exclusions": [
    {
      "path_prefix": "backend/routers/admin/",
      "reason": "Intentionally unguarded internal endpoints — no tenant billing context",
      "owner": "engineering",
      "expires": null
    },
    {
      "path_prefix": "backend/routers/internal/",
      "reason": "Service-to-service routes — no tenant billing context",
      "owner": "engineering",
      "expires": null
    }
  ]
}
```

3. Add `backend/tests/test_step9m_detector.py` (regression fixtures):

Critical test cases the detector implementation MUST pass:

| Case | Description | Expected result |
|------|-------------|-----------------|
| `test_unrelated_guard_same_file` | File has a usage guard in function A and an unguarded AI call in function B | Function B flagged as UNGUARDED (guard in A does NOT protect B) |
| `test_guarded_call_same_function` | AI call and guard both in same function | Function NOT flagged |
| `test_admin_route_excluded` | File under `backend/routers/admin/` | File skipped entirely |
| `test_alias_resolved` | File imports `call_claude_messages as llm_call`, function uses `llm_call(` | AI call detected, guard check proceeds |
| `test_delegated_service_call` | Router function calls a service method that itself calls Claude | Router function flagged (delegate does not inherit guard from service layer) |
| `test_no_enclosing_function` | AI call at module scope (outside any def) | Call site flagged as UNGUARDED (no function to check) |

4. Commit: `feat(nightly): add Step 9M AI usage metering coverage sweep`

## What This Replaces
Active direction: Step 9K (implemented run 114). Step 9M is the next step in the Step 9x series addressing systematic code-health gaps via nightly automation.

## Confidence
**HIGH** — identical pattern to Step 9I (block_demo_role sweep), which was approved and implemented at 1st carry-forward (run 107). Two metering incidents in 3 days provides stronger frequency signal than Step 9I's two incidents in 6 days. Call-site/function granularity eliminates false-positives from same-file unrelated guard text. Alias map handles import renaming. Exclusion JSON with owner+expires prevents orphaned exceptions. Regression fixtures (test_step9m_detector.py) catch detector regressions before they produce false-pass results. Zero architectural risk — SKILL.md edit + two new support files, no production code changes, no migrations.

## Run 116 Mandate
1. Resolve Step 9L/9M naming collision: confirm this session's recommendation is Step 9M (metering sweep); identify the 2026-09-05-am session's recommendation and assign it a non-colliding step number.
2. Verify Step 9M present in .claude/skills/nightly-commit-review/SKILL.md: `grep 'Step 9M'` — SHOULD PASS if human approves winner.
3. If Step 9M absent on run 116: escalate directly per autonomous-executable governance precedent (3rd-carry-forward → implement directly; 1st-carry-forward → implement in run 116 if SKILL.md edit is safe).
4. First nightly after Step 9M: does log contain 'Step 9M:' line? How many unguarded call sites found?
5. Step 9L (migration alerter, parking lot): has PR #788 (check_schema_log_migrations.py) been merged? If yes: Step 9L is unblocked for run 116.
6. os_tool_executions.py: now 4+ days stable. Re-evaluate god class split as run 116 candidate.
7. GH #684 SUPABASE_ACCESS_TOKEN: resolved? Brain connector health?
