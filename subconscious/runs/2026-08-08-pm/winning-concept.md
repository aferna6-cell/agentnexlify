# Winning Concept — Run 102
**Date:** 2026-08-08-pm  
**Winner:** Idea 3 — Orchestrator Grandfathered Plan Gap

---

## What

`backend/services/automation/orchestrator.py` checks plan membership at lines 238 and 319 for branded email wrapping. Both checks are:

```python
if plan in ("professional", "enterprise", "agent_os"):
```

The grandfathered plans `growth` and `autopilot` are missing. They appear in every other canonical plan-gate file:
- `backend/services/agent_os_gate.py` ✓
- `backend/services/plan_gate.py` ✓  
- `backend/services/ai_usage_guard.py` ✓
- `backend/services/automation/orchestrator.py` ✗ ← missing

## Why Now

CLAUDE.md states: "Legacy/grandfathered (still honored on old contracts): `growth`, `autopilot`, `professional`, `enterprise`." Active tenants on those plans are entitled to branded email wrapping in automation outputs. They're currently sending unbranded emails — a silent entitlement defect. No ADR or comment justifies the exclusion; cross-referencing the canonical files confirms this is an omission.

## The Fix

Two 1-line edits to `backend/services/automation/orchestrator.py`:

**Line 238 (before):**
```python
if plan in ("professional", "enterprise", "agent_os"):
```
**Line 238 (after):**
```python
if plan in ("professional", "enterprise", "agent_os", "growth", "autopilot"):
```

**Line 319 (same change).**

No migration. No schema change. No new imports. No tests need updating (existing plan-gate tests already cover the grandfathered set pattern — verify by running `backend/tests/test_plan_gating_new_plans.py`).

## Confidence

High. Evidence chain: CLAUDE.md canonical statement → three canonical gate files → orchestrator omission. Debate challenge C2 ("intentional exclusion?") resolved by absence of any ADR or comment. Challenge C3 ("missing brand fields?") resolved by brand fallback defaults in the wrapper.

## Pre-execution checklist

Before committing, the executor should:
1. Read `orchestrator.py:225-260` and `orchestrator.py:310-330` to confirm brand fallback logic
2. Confirm `growth`/`autopilot` appear in `ai_usage_guard.py`, `plan_gate.py`, `agent_os_gate.py`
3. Run `python -m pytest backend/tests/test_plan_gating_new_plans.py -v` to verify no regressions
4. Apply both edits in a single commit with `[skip ci]` (no CI minutes for this class of fix)

## Category

`code_health`

## Channel

`autonomous_executable` (existing-file patch, both occurrences in one file)

## Status

`proposed` — awaiting human approval
