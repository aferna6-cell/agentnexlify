---
name: prd-to-issues
effort: medium
description: Break a PRD into independently grabbable GitHub issues with vertical slices, blocking relationships, and labels. Output via gh issue create. Load when user says "issues from PRD", "backlog from spec", "gh issues for feature", "create tickets from PRD".
origin: https://github.com/mattpocock/skills/tree/main/prd-to-issues
version: 1.0.0
triggers:
  - issues from PRD
  - backlog from spec
  - gh issues for feature
  - create tickets from PRD
  - file issues for
  - PRD to issues
---

# PRD → GitHub Issues — Independent Backlog

Difference vs `prd-to-plan`: issues are **independent**, plan is **ordered**. Use both when PRD is large.

## When to Use
- PRD approved, multiple devs/sessions can grab work in parallel
- Feature work suitable for `issue-to-pr-loop` autonomous loop
- Need labeled backlog visible in GitHub
- Want to track who/what is in flight via project board

## When NOT to Use
- Solo dev, sequential execution → use `prd-to-plan` instead
- Single-issue feature
- PRD not approved
- Issues already exist for the feature

## Process
1. **Read PRD** at `specs/<feature>_spec.md`
2. **Decompose** into vertical slices (DB + API + UI per slice)
3. **State blockers** explicitly — Issue B blocks on Issue A
4. **Group by epic** — meta-issue tracks all children
5. **Label** by layer (backend/frontend/widget/migrations/docs) and priority (P0/P1/P2)
6. **File** via `gh issue create` per child
7. **Tag** issues `ai-ready` if `issue-to-pr-loop` should grab them

## Issue Template
```markdown
## Title
[<epic>] <slice description, imperative>

## Context
Source spec: specs/<feature>_spec.md (link to specific section)

## Acceptance Criteria
- [ ] DB: migration NNN_name.sql created + applied
- [ ] API: endpoint <method> <path> returns expected shape
- [ ] UI: page/component renders + handles loading/error/empty
- [ ] Test: <specific test> passes
- [ ] Tenant scope: all queries carry `client_id`

## Blockers
- Blocked by: #<issue> (must merge first)
- Blocks: #<issue> (downstream waits on this)

## Labels
- layer/<backend|frontend|widget|migrations|docs>
- priority/<p0|p1|p2>
- ai-ready (if claude-runnable)
- epic/<feature-name>

## Out-of-scope
- <thing> — see #<other-issue>

## Notes
- Constraint: <e.g. no `from __future__ import annotations`>
- Reference: <related code path>
```

## Decomposition pattern
For most AgentNexLiFy features:
```
Epic: <feature>
├─ Issue 1: Migration + RLS                   (no blockers, P0, layer/migrations)
├─ Issue 2: Backend endpoint                  (blocked by 1, P0, layer/backend)
├─ Issue 3: Frontend page (read-only)         (blocked by 2, P1, layer/frontend)
├─ Issue 4: Widget event/UI                   (blocked by 2, P1, layer/widget)
├─ Issue 5: Frontend page (write/mutate)      (blocked by 3, P2, layer/frontend)
├─ Issue 6: Admin dashboard slice             (blocked by 2, P2, layer/frontend)
├─ Issue 7: Metrics + success measurement     (blocked by 2, P2, layer/backend)
└─ Issue 8: Docs + KB article                 (blocked by 1-7, P2, layer/docs)
```

## Filing commands
```bash
# Single issue
gh issue create --title "[<epic>] <slice>" --body-file issue-body.md \
  --label "layer/backend,priority/p0,ai-ready,epic/<feature>"

# Bulk: write all bodies to /tmp/issues/, loop with gh issue create
```

## ai-ready tag
Issues tagged `ai-ready` get picked up by `.claude/skills/issue-to-pr-loop/SKILL.md` (15-min poll). Only tag issues that:
- Have crisp acceptance criteria (no ambiguity)
- Touch ≤5 files
- Don't require new architectural decisions
- Have all blockers resolved

## Cross-refs
- Companion: `write-prd`, `prd-to-plan`, `issue-to-pr-loop`
- `.claude/skills/issue-to-pr-loop/SKILL.md` — autonomous loop consumes ai-ready issues
- `.claude/skills/autopilot-loop/SKILL.md` — legacy loop (kept for reference)
- `CLAUDE.md` — issue-to-PR loop config
