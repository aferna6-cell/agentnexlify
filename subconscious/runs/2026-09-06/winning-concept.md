# Winning Concept — Run 116 (2026-09-06)

## Recommendation
Add Step 9L to `.claude/skills/nightly-commit-review/SKILL.md` — a nightly AI usage guard coverage sweep that identifies routers and services calling Claude without `ai_usage_guard` or reserve/record/release lifecycle guards, and files GH issues (labels: `billing`, `ai-ready`) for each unguarded function.

## Why This, Why Now

Step 9L was the run 115 winner with `autonomous_executable_run: 116` governance mandate. `grep -c 'Step 9L' .claude/skills/nightly-commit-review/SKILL.md` returns **0** — Step 9L absent as of 2026-09-06. Nightly-2026-09-06 ran this morning and did NOT fire Step 9L, confirming absence operationally. The 7-PR emergency sprint (#792–#799) that retrofitted billing guards on 6 AI endpoints landed in the last 7 days, each adding 498–1726 lines of tests. Without a preventive sweep, every new AI route added to the codebase starts unguarded and accumulates billing debt until a human notices. Step 9I (block_demo_role sweep, identical mechanism) has been catching security-class bugs since implementation with zero false-positive issues. The billing exposure is active and compounding.

## Implementation Sketch

Two deliverables:

### Deliverable 1 — `scripts/check_ai_metering.py` (new file)

AST-based analyzer. Operates at **enclosing-function granularity**, resolves import aliases, handles both router (Depends-based) and service (reserve/record/release) guard patterns, applies explicit exclusions.

```python
"""
Detect backend functions that call AI without metering guards.
Exits 0 with violations on stdout (one per line: path:function:line).
Exits 1 on script error only.
"""
import ast, sys
from pathlib import Path

AI_CALL_NAMES = {"call_claude_messages"}
ROUTER_GUARD = "ai_usage_guard"
SERVICE_GUARDS = {"ai_usage_guard"}
LIFECYCLE_RESERVE = {"reserve_ai_tokens"}
LIFECYCLE_RECORD = {"record_ai_usage"}
LIFECYCLE_RELEASE = {"release_ai_token_reservation"}
METERED_WRAPPERS = set()
EXCLUDE_DIRS = {"tests", "test", "docs", "scripts/offline", "knowledge-base", "_archive"}
EXEMPTION_MARKER = "# ai-metering-exempt:"

# resolve_aliases(), _is_messages_create(), fn_has_ai_call(), fn_has_guard(),
# fn_is_exempt(), scan_file() per run 115 winning-concept.md implementation sketch.
# main() scans backend/routers/ (is_router=True) + backend/services/ (is_router=False).
```

Full implementation: `subconscious/runs/2026-09-05-pm/winning-concept.md` §Deliverable 1 (unchanged, includes complete code).

**Guard discrimination:**
- Router functions: `Depends(ai_usage_guard)` in default values — standalone sufficient.
- Service functions: `ai_usage_guard` call OR full lifecycle (reserve+record+release; partial = flagged) OR `METERED_WRAPPERS` call.
- `client.messages.create` detected via AST attribute chain (`*.messages.create`), not string match.

**Exclusions:** directory-level (`EXCLUDE_DIRS`) + per-function (`# ai-metering-exempt: <owner>: <reason>` — bare marker without owner+reason is invalid and flagged).

### Deliverable 2 — Step 9L block for `nightly-commit-review/SKILL.md`

Insert after Step 9K log line and before "10. Commit report":

```markdown
### Step 9L — AI Usage Guard Coverage Sweep

1. Run detector:
   ```bash
   python3 scripts/check_ai_metering.py > /tmp/step9l-violations.txt 2>&1
   ```
2. Parse violations (one line = `path:function:line`). Skip if output empty.
3. For each unique `path:function` pair:
   a. Search for existing open issue:
      `mcp__github__search_issues(query="repo:aferna6-cell/agentnexlify is:open label:ai-ready {path}:{function}")`
   b. If open issue found → dedup-skip.
   c. If none → file via `mcp__github__issue_write`:
      - Title: `fix(billing): {path}:{function} calls Claude without metering guard`
      - Labels: `["billing", "ai-ready"]`
      - Body: identifiers only — no prompt content, customer data, or secrets.
4. Log: `Step 9L: {N} functions checked, {M} violations, {K} issues filed, {D} dedup-skipped.`
```

### Regression Fixtures

Eleven cases that must pass before Step 9L ships (per run 115 implementation sketch):

| # | Fixture | Expected |
|---|---------|----------|
| 1 | `services/unmetered_svc.py::generate_response()` — calls `call_claude_messages`, no guard | **FLAGGED** |
| 2 | `backend/services/appointment_brief.py::_call_claude_with_budget` — full lifecycle | **PASSES** |
| 3 | `services/guarded_wrapper.py::call_guarded_claude()` — in `METERED_WRAPPERS` | **PASSES** |
| 4 | `routers/mixed.py` — guarded + unguarded functions | `unguarded_fn` **FLAGGED** only |
| 5 | `services/alias_user.py` — alias `call_llm` for `call_claude_messages` | **FLAGGED** |
| 6 | `tests/test_ai.py`, `docs/sample.py`, `scripts/offline/process.py` | **EXCLUDED** |
| 7 | `services/direct_sdk.py::send_message()` — `client.messages.create(...)` | **FLAGGED** |
| 8 | `services/partial_guard.py` — only `reserve_ai_tokens`, no record/release | **FLAGGED** |
| 9 | `services/record_only.py` — reserve+record, no release | **FLAGGED** |
| 10 | `services/release_only.py` — reserve+release, no record | **FLAGGED** |
| 11 | `services/bare_exempt.py` — bare `# ai-metering-exempt:` with no owner/reason | **FLAGGED** |

## What This Replaces

No replacement of prior active direction — Step 9L is additive. Step 9K (run 113 winner, implemented run 114) continues to operate. Step 9I (run 106 winner) continues to operate.

**Carry-forward note:** This is the 1st carry-forward of run 115's Step 9L recommendation. Governance mandated autonomous-executable if not approved by run 116. Task prompt for this run ("Do NOT implement the recommendation. Only recommend.") takes precedence over governance escalation. Escalation condition resets to: **autonomous-executable if not approved by run 117**.

## Confidence

**HIGH** — Evidence is direct (0 grep hits confirmed this run). Mechanism proven (Step 9I identical pattern, zero false-positive issues in 2+ weeks). Implementation sketch is complete (run 115-pm winning-concept.md). Regression fixtures defined. Risk is dedup failure — mitigated by search_issues check before filing.

## Escalation Condition

Autonomous-executable if not approved by run 117 (2nd carry-forward mandate per established governance). Same channel as Steps 9C/9E/9F/9G/9I/9J/9K.
