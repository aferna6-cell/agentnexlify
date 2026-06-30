# Idea 2: Plan-Name Guard — Check 7 in check_project_invariants.py

**Run:** 73 | **Date:** 2026-06-30

## One-line
Add Check 7 to `scripts/check_project_invariants.py`: enforce `chatbot` / `agent_os` in billing plan-name constants; fail pre-commit on retired names.

## Background
- Proposed in run 67. GH #292 / #293 (plan-name sprawl) fixed 2026-06-23 — unblocked since then.
- `CLAUDE.md` states plan names: `chatbot` ($19.99) · `agent_os` ($99.99). Legacy: `growth`, `autopilot`, `professional`, `enterprise`. Retired (never use): `foundation`, `operations`.
- `check_project_invariants.py` has 6 checks (invariants). Check 7 would scan billing constants for retired names.
- `backend/services/stripe_service.py` + `ai_usage_guard.PLAN_BASELINE_TOKENS` are canonical. If a dev typos `foundation` there, it fails silently.

## Evidence
- `docs/dev-knowledge/bug-patterns.md` line 1: Zapier API key lookup without `plan_status` enforcement → similar category of silent billing logic error.
- GH #292 PR description confirms plan-name confusion existed in multiple files.
- `check_project_invariants.py` Check 6 (added run 64): already validates em-dash in Python strings. Check 7 would follow identical pattern.

## What it involves
1. Add `check_plan_name_constants()` function to `scripts/check_project_invariants.py`.
2. Grep `backend/services/stripe_service.py` and `backend/services/ai_usage_guard.py` for `PLAN_BASELINE_TOKENS` dict keys + Stripe price IDs.
3. Fail if any key matches retired names: `foundation`, `operations`, or unrecognized names not in allowed set.
4. Wire as CHECK 7 in the `main()` runner.

## Effort
- S (Small) — 1–2 hours. Python script addition following existing Check 6 pattern.
- Files: `scripts/check_project_invariants.py` only.

## Risk
- LOW on content; MEDIUM on nightly-scope question.
- Python file edits are NOT in nightly-commit-review autonomous scope (per run 44 decision: "nightly scope = SKILL.md / pre-commit bash / CI YAMLs only"). Requires human session.
- False positive risk: must handle `LEGACY_PLANS` list alongside retired names.

## Autonomy assessment
- NOT AUTONOMOUS-EXECUTABLE.
- Cannot be shipped by nightly-commit-review.
- Requires human-approval session to edit `check_project_invariants.py`.

## Why this loses to Idea 1
- Same S-effort bracket but lower customer value (systemic prevention vs TCPA liability).
- Not executable without human session anyway — human already has to approve it.
- SMS Dashboard is already in the queue at `pending_approval` since run 70 (older claim).
- Moratorium: adding a new pending item while 4-6 already waiting is borderline.

## Recommendation
Parking lot. Revisit run 74 if SMS Dashboard shipped.
