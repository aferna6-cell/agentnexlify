---
name: moratorium-sprint
description: Execute all pending S-effort subconscious recommendations in one session. Reads governance.json, loads implementation sketches, runs items sequentially, opens draft PR. Use when moratorium active and human says "do the sprint", "moratorium sprint", "execute pending", "clear the backlog", or invokes /moratorium-sprint.
version: 1.0.0
triggers:
  - moratorium sprint
  - do the sprint
  - execute pending
  - clear the backlog
  - exit moratorium
effort: xhigh
---

# Moratorium Sprint — Execute S-Effort Backlog

Execute all pending S-effort subconscious recommendations in one session.

## When to Use
- `moratorium_config.moratorium_active: true` in `subconscious/state/governance.json`
- Human says "do the sprint", "moratorium sprint", "execute pending", "/moratorium-sprint"
- After verifying human is present and has implicitly approved via session context

## When NOT to Use
- Moratorium not active (use free-choice run instead)
- Items have not been approved by human review
- Sprint items are M/L effort (require separate planning session)

## Steps

### Phase 1: Load State (2 min)

1. Read `subconscious/state/governance.json`
2. Extract `active_directions` where `status: "pending_approval"`
3. Filter to S-effort items — items with note containing "~5 min", "~10 min", "~15 min", "~20 min", "S-effort", or "30 min"
4. For each item, find its run date (from `date` field) → locate `subconscious/runs/{date}/winning-concept.md`
5. Read the "Implementation Sketch" section from each winning-concept.md
6. Report: "Found N S-effort items. Executing in order: [list]"

### Phase 2: Create Branch (1 min)

```bash
git checkout -b moratorium-exit-sprint
```

If branch already exists:
```bash
git checkout moratorium-exit-sprint
git pull origin moratorium-exit-sprint 2>/dev/null || true
```

### Phase 3: Execute Items Sequentially

For each S-effort item (shortest first to build momentum):

1. Read the implementation sketch verbatim from `winning-concept.md`
2. Make exactly the edits described — no scope creep
3. Verify: run the verification command from the sketch (e.g. `python3 scripts/check_project_invariants.py`)
4. Commit with the exact message from the sketch
5. Report: "✓ Item complete: [title] — [commit SHA]"

**Current 4 items (as of run 23, 2026-05-18):**

| Item | Source | Effort | Verification |
|------|--------|--------|--------------|
| A: Wire check_project_invariants.py into pre-commit as Check 10 | runs/2026-05-18/winning-concept.md §Step 1 | ~5 min | `python3 scripts/check_project_invariants.py` |
| B: Widget 3-Copy Sync Guard (check-widget-sync.sh + pre-push + CLAUDE.md fix) | runs/2026-05-18/winning-concept.md §Step 2 | ~15 min | `bash scripts/check-widget-sync.sh` |
| C: Moratorium Escalation Protocol in nightly-commit-review SKILL.md | runs/2026-05-18/winning-concept.md §Step 3 | ~10 min | grep confirmation |
| D: Lead Qualifier Eval CI Workflow (.github/workflows/lead-qualifier-eval.yml) | runs/2026-05-18/winning-concept.md §Step 4 | ~20 min | `cat .github/workflows/lead-qualifier-eval.yml` |

### Phase 4: Open Draft PR (2 min)

Push branch:
```bash
git push -u origin moratorium-exit-sprint
```

Use `mcp__github__create_pull_request` (draft=true):
- Title: "Moratorium Exit Sprint — [N] S-effort guards"
- Body: summary table with item, commit SHA, run reference
- Base: main

### Phase 5: Update Governance

After PR opened:
1. Count items completed
2. Add note to `subconscious/state/governance.json` under each completed direction:
   - `status: "pending_approval"` → `status: "sprint_pr_open"`
   - Add field `sprint_pr: "#<PR number>"`
3. Report: "Sprint PR #<N> open. Pending [before] → [after] when merged."

## Success Criteria
- All S-effort items have commits on `moratorium-exit-sprint`
- Draft PR is open against main
- Each item has been verified (exit 0 on verification command)
- No M/L-effort items touched

## Anti-patterns
- Never execute M/L effort items (AI-to-Human Handoff, Zapier fix) — require separate planning
- Never skip verification step between items
- Never implement items not in the S-effort filtered list
- Never close governance.json moratorium until PR is merged (not opened)
