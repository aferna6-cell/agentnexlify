---
name: prd-to-plan
effort: high
description: Convert a PRD into a phased implementation plan using tracer-bullet vertical slices. Output ordered phases that reduce integration risk. Load when user says "plan from PRD", "phase this spec", "vertical slice plan", "implementation plan for spec".
origin: https://github.com/mattpocock/skills/tree/main/prd-to-plan
version: 1.0.0
triggers:
  - plan from PRD
  - phase this spec
  - vertical slice plan
  - implementation plan
  - sequence the work
  - PRD to plan
---

# PRD → Plan — Vertical Slice Sequencing

Difference vs `prd-to-issues`: a plan is **ordered + staged**; issues are independent. Plan reduces integration risk by shipping thin end-to-end slices.

## When to Use
- PRD approved, ready to implement
- Feature crosses backend + frontend + widget layers
- Migration + endpoint + UI need synchronized rollout
- High-risk change needing reversibility checkpoints

## When NOT to Use
- Single-file change
- PRD not approved
- Pure refactor with no new behavior (use `request-refactor-plan` style)
- One-layer change (just backend, just frontend) — direct execution

## Tracer Bullet Principle
Build the thinnest possible end-to-end slice first. Each phase ships a working vertical from DB → API → UI → user. Subsequent phases thicken the slice.

**Bad:** finish all backend → finish all frontend → integrate (big-bang risk)
**Good:** ship 1 happy-path flow end-to-end → add edge cases → add admin view → add metrics

## Process
1. **Read PRD** at `specs/<feature>_spec.md`
2. **Identify the smallest user-visible win** — that's Phase 1
3. **Walk back from win** — what minimum DB + API + UI is required?
4. **Define phases** — each phase ships a working slice end-to-end
5. **Define gates** — what test/metric proves each phase done?
6. **Output plan** to `plans/<feature>_plan.md`
7. **Hand off** to `compound-engineering` skill or `feature-build` skill per phase

## Plan Template
```markdown
# [Feature Name] — Implementation Plan

**Source spec:** specs/<feature>_spec.md
**Estimated phases:** N
**Reversibility:** each phase commits behind feature flag (default off)

## Phase 1 — Tracer Bullet (happy path)
**Goal:** smallest user-visible win
**DB:** migration NNN_name.sql (additive only)
**API:** 1 endpoint, happy path, no edge cases
**UI:** minimum render, no polish
**Gate:** 1 manual test passes end-to-end
**Rollback:** disable feature flag

## Phase 2 — Edge Cases
**Goal:** harden Phase 1 against bad input
**Changes:** validation, error messages, empty states
**Gate:** test suite covers 3+ edge cases

## Phase 3 — Admin/Internal Views
**Goal:** support team can debug
**Changes:** admin dashboard, audit log
**Gate:** support can answer "why didn't X happen for tenant Y"

## Phase 4 — Metrics + Polish
**Goal:** measure success
**Changes:** event tracking, success metric SQL, polish
**Gate:** success metric query returns data

## Phase 5 — GA + Flag Removal
**Goal:** default on for all tenants
**Changes:** remove feature flag, update docs
**Gate:** 7 days zero-incident on staging tenants

## Cross-Phase Concerns
- Schema migrations: applied once, never split
- Widget JS sync: every phase touching widget MUST sync `widget/` + `frontend/public/widget/`
- Tenant scope: every query in every phase carries `client_id`
- Test gates: backend tests + frontend build + manual happy-path
```

## Phase sizing rules
- Each phase fits one PR
- Each phase deployable independently
- Each phase reversible via flag or revert
- No phase >5 days work
- If a phase would touch >10 files → split

## Output naming
- File: `plans/<kebab-feature>_plan.md`
- Example: `plans/lead-scoring-v2_plan.md`

## Cross-refs
- Companion: `write-prd`, `prd-to-issues`, `compound-engineering`, `feature-build`
- `.claude/rules/user-rules.md` Rule 8 — no half migrations (rule for cross-phase schema discipline)
- `CLAUDE.md` — workflows section
- `PROMPTLIBRARY.md` — REASON Implementation Plan
