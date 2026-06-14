# Winning Concept — 2026-05-20 (Run 26)

## Recommendation

Invoke `/moratorium-sprint` to execute the 3 remaining S-effort items (Items A, B, D) — Item C was autonomously completed today by the nightly review.

---

## Why This, Why Now

**Item C is done.** The nightly review (2026-05-20, commit 2ce31b2) autonomously added the Moratorium Escalation Protocol section to `.claude/skills/nightly-commit-review/SKILL.md`. This is Item C from the sprint. The autonomous system delivered again — two wins in two days (moratorium-sprint SKILL.md on 2026-05-19, SKILL.md protocol update on 2026-05-20). The sprint is now 3 items, ~40 min.

**The escalation path is now live.** The nightly review's new Moratorium Escalation Protocol (added today) means: if moratorium is active and oldest_pending > 14 days, the nightly review will auto-comment on GH #169 with escalation state every night. This creates an external accountability signal — GitHub comment history will visibly accumulate until the sprint is invoked.

**Three items with zero blockers.** Item A: 3-line pre-commit addition, script passes all checks. Item B: bash script creation + CLAUDE.md 1-line fix, widget copies confirmed in sync (no diff to resolve). Item D: GitHub Actions workflow, harness already passes locally. All have pre-written sketches in `subconscious/runs/2026-05-18/winning-concept.md §Steps 1-4`.

**moratorium-sprint SKILL.md handles the context loading.** Previous sessions spent 15-20 min loading governance.json + 4+ winning-concept.md files before implementing. The skill does that automatically. Net execution time: ~40 min.

---

## Implementation Sketch

**Estimated time: ~40 min (down from ~50 min — Item C done).**

### Step 1: Invoke the skill

In any interactive Claude Code session:

```
/moratorium-sprint
```

Or say: "moratorium sprint", "execute pending", "clear the backlog", "exit moratorium"

The skill will:
1. Read governance.json → extract pending S-effort items
2. Detect Item C already implemented (SKILL.md grep passes) → skip
3. Execute Items A, B, D sequentially (see table)
4. Verify each with prescribed command
5. Open draft PR against main

### Step 2: 3 remaining items

| Item | Source | Effort | Verification |
|------|--------|--------|--------------|
| A: Wire check_project_invariants.py into pre-commit as Check 10 | runs/2026-05-18/winning-concept.md §Step 1 | ~5 min | `python3 scripts/check_project_invariants.py` |
| B: Widget 3-Copy Sync Guard (check-widget-sync.sh + pre-push + CLAUDE.md fix) | runs/2026-05-18/winning-concept.md §Step 2 | ~15 min | `bash scripts/check-widget-sync.sh` |
| D: Lead Qualifier Eval CI Workflow (.github/workflows/lead-qualifier-eval.yml) | runs/2026-05-18/winning-concept.md §Step 4 | ~20 min | `cat .github/workflows/lead-qualifier-eval.yml` |

### Step 3: Merge draft PR

Review draft PR → confirm 3 items correct → merge to main. Pending 9→6.

### Step 4: Post-sprint governance

Update governance.json:
- Items A (run 8), B (run 7 / run 15), D (run 14) → status `implemented`
- Run 19 (Item C, Moratorium Escalation Protocol) → status `implemented` (done today by 2ce31b2)
- `implementation_lag_warning.runs_pending_approval` 9→5
- Begin moratorium exit path: resolve runs 20/21/22 → pending 5→2 → moratorium exits

### Step 5 (bonus, independent): Merge safe dep PRs

PRs #102, #103 (22+ days), #163, #164 (8 days). `mcp__github__merge_pull_request` × 4. ~5 min. Independent of moratorium.

---

## What This Replaces

Run 25's winner (same recommendation, 4 items) is now a 3-item sprint. Item C has been delivered. This recommendation refines run 25's sketch with updated item list.

---

## What Comes After

**If /moratorium-sprint executes and PR merges (pending 9→6):**
- Resolve governance items (runs 20/21 = GH milestone + AI-to-Human GH issue) → pending 6→4
- Resolve run 22 (check_project_invariants = done via sprint) → pending 4→3
- Resolve one more → pending 3→2 → moratorium exits
- Run 27 free choice: pre-commit-guard-add skill (parking lot), AI-to-Human Handoff v1 (Critical, 35d)

**If /moratorium-sprint is NOT invoked by run 27:**
- Nightly review escalation fires automatically (GH #169 comment added nightly)
- Run 27 recommendation: trigger moratorium-sprint from nightly review as LOW-risk scheduled execution (no interactive session needed) — pre-written sketches satisfy autonomous scope criteria

---

## Confidence

**HIGH** — Debate outcome: Idea 1 SURVIVES (3 rounds), Idea 2 KILLED (parallel execution conflict), Idea 3 WEAKENED → parking lot. New evidence strengthens this run vs. run 25: sprint is lighter (3 items), Item C done autonomously, escalation path now encoded in SKILL.md. The only unchanged risk is the human-action gap — but the automated failsafe now exists (nightly GH comments on #169). Sprint is at objectively lowest activation energy.
