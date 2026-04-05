# Plan: End-to-End Codebase Test
## Agent 2 Output — 2026-04-05

## Architecture
Hybrid approach: fast inline checks for mechanical verification, parallel agents for deep analysis across 6 verticals. No code changes — audit only.

## Execution Plan

### Task 1: Backend Integrity (Parallel Agent A)
- Verify all 61 routers are registered in main.py
- Check for dangerous imports (from __future__ import annotations)
- Verify Pydantic models use correct column names (client_id, status)
- Scan for bare except blocks
- Check all routers have auth dependencies

### Task 2: Frontend Health (Parallel Agent B)
- Run npm run build — must pass
- Check for stale API endpoint references
- Verify no localStorage usage in artifacts
- Scan for missing imports

### Task 3: Widget Sync (Inline — fast)
- diff widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js

### Task 4: Schema Consistency (Parallel Agent C)
- Cross-reference Pydantic models against schema-log.md
- Check migration file numbering for conflicts
- Verify client_id vs tenant_id usage in leads queries
- Check for status vs lead_stage usage

### Task 5: Security Scan (Parallel Agent D)
- Scan for hardcoded secrets
- Check for eval/exec/os.system
- Verify tenant isolation on all query paths
- Check CORS configuration

### Task 6: Integration Check (Inline — fast)
- Compare router count vs include_router count
- Verify frontend API paths match backend routes

## Dependency Order
- Tasks 1, 2, 4, 5 can run in parallel (independent domains)
- Task 3 and 6 run inline (fast, no agent needed)
- All tasks independent — no ordering constraints
