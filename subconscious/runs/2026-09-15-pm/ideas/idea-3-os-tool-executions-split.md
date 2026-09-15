# Idea 3 — os_tool_executions.py God Class Split (783 lines)

**Category:** code_health / technical_debt
**Effort:** M (multi-file refactor, 3-5 hours)
**Confidence:** MEDIUM-HIGH
**Status:** PARKING LOT (modified 2026-09-11, defer 1 more run)

---

## Problem

`os_tool_executions.py` is 783 lines. CLAUDE.md Rule 9: files >600 lines → factor before adding more. This file handles multiple concerns that should be separate modules.

Evidence:
- Run 116 first flagged this (7 days stable at that point)
- Run 117: still 8d+ stable
- Run 118: still parked (no recent modifications)
- Run 120: file modified 2026-09-11 (today at time of run 120) — deferred 1 more run

---

## Why This Matters

God classes are where bugs compound. Every additional concern added to this file:
- Increases blast radius for any single change
- Creates merge conflicts in concurrent development
- Hides dead code
- Makes each new concern harder to test in isolation

The file is on the critical path for `os_tool_executions` — any bug in it affects all tool execution flows.

---

## Proposed Split

Without reading the full file, the likely split based on file name and size:

1. `os_tool_execution_core.py` — base execution logic, routing
2. `os_tool_execution_handlers.py` — per-tool handlers (likely the bulk)
3. `os_tool_execution_validators.py` — input validation, schema enforcement

---

## Why PARKING LOT

- Was modified 2026-09-11 (same day as run 120) — might be in the middle of active development
- Splitting an actively-modified file creates risk of divergence
- Low urgency: no bugs attributed to this file recently
- Step 9E credential escalation has higher urgency (expiry risk for autonomous loop)

---

## Recommendation

Revisit at run 122 or 123. If file has stabilized (>7 days no modifications), elevate to full candidate.
