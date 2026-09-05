# Winning Concept — Run 115 (2026-09-04-pm)

## Recommendation
Add **Step 9L** to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly AI provider-call metering coverage sweep that detects unguarded provider calls in shipped backend modules and files a `security+ai-ready` GH issue per unguarded call site.

## Canonical Identifier
**Step 9L** is the canonical name for this recommendation, as designated by the engineering owner. This session (run 115, 2026-09-04-pm) originally proposed "Step 9M"; the EM resolved the cross-session naming collision by designating Step 9L. All references in this artifact and in governance state use Step 9L.

## Why This, Why Now
Three PRs in recent days added missing `reserve/record/release` metering to `extract_action_items` (widget, #793), `live-AI respond` (voice, #792), and `appointment_brief` (services, #791) — all merged. Same miss class across different subsystems. Identical to the `block_demo_role` recurrence pattern that spawned Step 9I (two issues in 6 days, nightly sweep found 100+ violations). Each unmetered AI endpoint silently leaks revenue; the reserve/record/release pattern is not enforced by any automated check. Step 9L closes this class permanently via the autonomous-executable SKILL.md-edit channel.

## Implementation Sketch
1. Edit `.claude/skills/nightly-commit-review/SKILL.md` — insert Step 9L block after Step 9K and before the "10. Commit report" step.

**Step 9L block to insert:**
```markdown
### Step 9L — AI Provider-Call Metering Coverage Sweep

**Scope:** All shipped backend modules under `backend/` (routers, services, tasks,
scheduled jobs). Not restricted to router filenames — delegated provider calls in
service modules are in scope and must be metered where they execute.

**Detector granularity:** provider-call/enclosing-function level. A call site
passes when the SPECIFIC FUNCTION containing the provider call either (a) contains
a usage guard in its own function body, OR (b) delegates exclusively to a
recognized canonical metered wrapper (see Metered Wrapper List below).

**Recognized Canonical Metered Wrappers** (stored in `.claude/state/step9l_metered_wrappers.json`):
Functions in this list are themselves metered — callers that only call these
functions do NOT need their own guard. Load from file before scanning.
Default list includes any function decorated with `@metered_ai_call` or that
calls `reserve_tokens` + `record_usage` + `release_tokens` in its own body.
Update this file (with owner+reason) when a new canonical metered wrapper ships.

**Explicit Exclusions** (stored in `.claude/state/step9l_exclusions.json`):
Load exclusions before scanning. Files matching any exclusion path are skipped.
Default exclusions (each requires owner+reason+expires):
- `backend/tests/**` — test fixtures (owner: engineering, expires: never)
- `backend/**/test_*.py` — test files by name pattern
- `docs/**` — documentation (owner: engineering, expires: never)
- `scripts/**` — offline/dev scripts (owner: engineering, expires: never)
- `backend/routers/admin/**` — intentionally unguarded internal endpoints
- `backend/routers/internal/**` — service-to-service routes, no tenant billing context

**Alias/import handling:**
Before scanning each file, build an alias map from its imports:
```python
# Detect: from X import call_claude_messages as llm_call
grep -n "^\(from\|import\).*\(call_claude_messages\|claude_client\|anthropic_client\|AnthropicClient\|messages\.create\)" <file>
```
Include aliased names as AI call patterns for that file.

**Emit identifiers only:**
GH issue bodies MUST contain only: file paths, function names, line numbers, and
the provider call pattern matched. No prompt text, no customer data, no secret
values, no log content. If a line containing the provider call also contains
potentially sensitive content, emit the line number only, not the line content.

---

**Algorithm:**

1. Load exclusion list from `.claude/state/step9l_exclusions.json`. Load metered
   wrapper list from `.claude/state/step9l_metered_wrappers.json`.

2. Find candidate files with provider calls (file-level pre-filter):
   ```bash
   grep -rln "call_claude_messages\|claude_client\.messages\|anthropic_client\|AnthropicClient\|messages\.create" backend/
   ```
   Filter out any path matching an exclusion.

3. For each candidate file:
   a. Build alias map from imports.
   b. Find all provider call sites with line numbers (`grep -n`), including aliases.
   c. For each call site line N:
      - Scan upward from N to find the nearest enclosing `def` or `async def`
        (same or lesser indentation). This defines the function start.
      - Scan downward from the function start to find the next `def`/`async def`
        at the same indentation — this defines the function end.
      - Extract the function body (lines [function_start, function_end)).
      - **Metered wrapper check first:** if the function body calls ONLY functions
        in the metered wrapper list (no bare provider call with no wrapper), the
        call site PASSES — skip guard check.
      - **Guard check:** if guard not passed via wrapper, check function body for:
        `ai_usage_guard|reserve_tokens|check_ai_budget|block_demo_role`
      - If neither guard nor recognized wrapper found → call site is UNGUARDED.
   d. Collect all unguarded call sites as `(file, function_name, line_number)` tuples.

4. Dedup: for each unguarded `(file, function_name)` pair, check if an open GH
   issue already references `{filename}::{function_name}` with label `ai-ready`.
   Skip if yes.

5. For each new unguarded call site: file GH issue with labels `security`, `ai-ready`:
   - Title: `fix(metering): AI usage metering missing in {filename}::{function_name}()`
   - Body (identifiers only — no prompt/customer/secret content):
     - File path and function name
     - Line number(s) of provider call(s)
     - Provider call pattern matched
     - Explain reserve/record/release pattern needed
     - Reference `backend/tests/test_widget_extract_action_items_usage_guard.py`
       and `backend/tests/test_appointment_brief_usage_guard.py` as example tests
     - Reference `backend/tests/test_step9l_detector.py` for detector regression cases

6. Log to nightly report:
   - `Step 9L: {N} backend files scanned, {F} functions checked, {M} unguarded call sites, {K} new issues filed`
   - If 0 unguarded: `Step 9L: All AI provider calls in backend have usage metering — PASS`
```

2. Add `.claude/state/step9l_exclusions.json` (new file):
```json
{
  "_comment": "Exclusions for Step 9L AI provider-call metering sweep. Each entry requires owner and expires.",
  "exclusions": [
    {"path_prefix": "backend/tests/", "reason": "Test fixtures", "owner": "engineering", "expires": null},
    {"path_pattern": "**/test_*.py", "reason": "Test files by name", "owner": "engineering", "expires": null},
    {"path_prefix": "docs/", "reason": "Documentation", "owner": "engineering", "expires": null},
    {"path_prefix": "scripts/", "reason": "Offline/dev scripts", "owner": "engineering", "expires": null},
    {"path_prefix": "backend/routers/admin/", "reason": "Intentionally unguarded internal endpoints — no tenant billing context", "owner": "engineering", "expires": null},
    {"path_prefix": "backend/routers/internal/", "reason": "Service-to-service routes — no tenant billing context", "owner": "engineering", "expires": null}
  ]
}
```

3. Add `.claude/state/step9l_metered_wrappers.json` (new file):
```json
{
  "_comment": "Canonical metered wrappers for Step 9L. Callers that exclusively call these are considered metered.",
  "wrappers": [
    {"function": "call_claude_messages_metered", "reason": "Wraps call_claude_messages with reserve/record/release", "owner": "engineering"},
    {"decorator": "@metered_ai_call", "reason": "Decorator enforces reserve/record/release", "owner": "engineering"}
  ],
  "positive_inventory": [
    {"file": "backend/services/widget_service.py", "function": "extract_action_items", "pr": 793, "note": "Fixed #793"},
    {"file": "backend/routers/voice.py", "function": "live_ai_respond", "pr": 792, "note": "Fixed #792"},
    {"file": "backend/services/appointment_service.py", "function": "appointment_brief", "pr": 791, "note": "Fixed #791 — merged, use as positive fixture"}
  ]
}
```

4. Add `backend/tests/test_step9l_detector.py` (regression fixtures).

Required design fixtures (all 6 must pass):

| # | Case | Description | Expected result |
|---|------|-------------|-----------------|
| 1 | `test_delegated_unmetered_service_flagged` | Router function delegates to service function; service function makes provider call with no guard and is NOT a recognized metered wrapper | Service function flagged as UNGUARDED |
| 2 | `test_direct_metered_call_passes` | Function contains provider call AND `reserve_tokens` guard in same function body | Function NOT flagged |
| 3 | `test_recognized_metered_wrapper_passes` | Function calls only `call_claude_messages_metered()` (canonical wrapper) — no bare provider call | Function NOT flagged (wrapper check passes) |
| 4 | `test_unrelated_same_file_metering_no_mask` | File has guard in function A; function B has provider call with no guard | Function B flagged as UNGUARDED (A's guard does NOT protect B) |
| 5 | `test_alias_detected` | File imports `call_claude_messages as llm_call`; function calls `llm_call(` with no guard | Alias resolved; function flagged as UNGUARDED |
| 6 | `test_exclusions_explicit` | Files under `backend/tests/`, `docs/`, `scripts/`, `backend/routers/admin/` | All skipped entirely — not flagged, not counted |
| + | `test_appointment_brief_positive_fixture` | `appointment_brief` function post-#791 | Passes metering check — confirms positive inventory is accurate |

5. Commit: `feat(nightly): add Step 9L AI provider-call metering coverage sweep`

## What This Replaces
Active direction: Step 9K (implemented run 114). Step 9L is the next step in the Step 9x series addressing systematic code-health gaps via nightly automation.

## Confidence
**HIGH** — identical pattern to Step 9I (block_demo_role sweep), approved + implemented at 1st carry-forward (run 107). Three metering incidents in recent days provides strong frequency signal. Provider-call/function granularity eliminates false-positives from same-file unrelated guard text. Canonical metered wrapper recognition handles indirection patterns. Alias map handles import renaming. Exclusion JSON (test/docs/offline/admin/internal) with owner+reason+expires prevents orphaned exceptions. Emit-identifiers-only prevents secret leakage in GH issues. Positive inventory tracks confirmed-metered functions for fixture validation. Zero architectural risk — SKILL.md edit + support config files, no production code changes, no migrations.

## Run 116 Mandate
1. Verify Step 9L present in `.claude/skills/nightly-commit-review/SKILL.md`: `grep 'Step 9L'` — SHOULD PASS if EM approves.
2. If Step 9L absent on run 116: escalate per autonomous-executable governance precedent (1st carry-forward → implement in run 116 if SKILL.md edit is safe).
3. First nightly after Step 9L: does log contain 'Step 9L:' line? How many unguarded call sites found?
4. `appointment_brief` (#791 merged): confirm it appears in `step9l_metered_wrappers.json` positive inventory, not as an open violation.
5. os_tool_executions.py: re-evaluate god class split as run 116 candidate if 4d+ stable.
6. GH #684 SUPABASE_ACCESS_TOKEN: resolved? Brain connector health?
