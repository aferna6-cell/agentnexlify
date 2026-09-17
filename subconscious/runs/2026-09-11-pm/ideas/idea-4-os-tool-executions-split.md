# Idea 4: Split os_tool_executions.py god class (783L)

**Evidence:**
- os_tool_executions.py: 783L (threshold 600L — Rule 9).
- 4 consecutive subconscious runs (116, 117, 118, 119) flagged as god class split candidate.
- BUT: commit adb31f9 (2026-09-11, today) modified the file — send_email approval failures fix.
- Stability window broken. File actively changing.

**Action:**
Split into: os_tool_exec_core.py (~200L, orchestration), os_tool_exec_email.py (email/send), os_tool_exec_crm.py (CRM/calendar), os_tool_exec_misc.py (remaining). Update imports in routers.

**Weakness:**
File modified today. Not in stable window. Split now would conflict with active development. Human review required given scope (6+ routers import this service).

**Category:** code_health

**Effort:** L (multi-file refactor, blast radius unknown without gitnexus_impact)

**Confidence:** MEDIUM but DEFERRED — file not stable, require 5+ days with no changes before split.
