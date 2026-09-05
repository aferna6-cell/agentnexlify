### Idea 3: Split os_tool_executions.py God Class (783 lines, 6d stable)

**Evidence:**
os_tool_executions.py: 783 lines (threshold: 600). Last commit: 2026-08-30 (6 days ago — stability
condition met: 3d+ with 0 commits). Run 114 mandate explicitly deferred this as "run 115 candidate
when stable." Run 115 mandate item 5: "os_tool_executions.py: stable (0 commits 4d+)? If yes: run
115 god class split candidate." Condition confirmed today. CLAUDE.md Rule 9: "if a file is already
>600 lines and I'm about to add more, stop. Factor existing code into modules first."
File handles AI tool execution dispatch — mixing orchestration, execution, error handling, and
tool-specific logic across multiple concerns.

**Action:**
Recommend god-class split of `backend/services/os_tool_executions.py` into:
- `os_tool_executions.py` — orchestration + dispatch only (~150 lines)
- `os_tool_execution_types.py` — type definitions, schemas, enums (~100 lines)
- `os_tool_handlers/` — per-tool-type handler modules (~100-150 lines each)
- `os_tool_error_handling.py` — shared error/retry logic (~100 lines)
Human approves module boundary proposal. Implementation via compound-engineering pipeline.
Prerequisite: read current file to map actual module boundaries before final proposal.

**Impact:**
Blast radius of future AI tool additions shrinks from "touch 783-line file" to "add new handler file."
Consistent with CLAUDE.md Rule 9 + Rule 12. Reduces merge conflicts and code review surface.
Category: code_health
Effort: M (read file to map, propose split, human approves, compound-engineering implements)
