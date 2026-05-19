# Winning Concept — 2026-05-19-pm (Run 26)

## Recommendation

Invoke `/moratorium-sprint` now, in this same interactive session, to execute the 4 pre-written S-effort items and open a draft PR.

---

## Why This, Why Now

**Three conditions align for the first time in 26 runs.** (1) moratorium-sprint SKILL.md is fully built and documented (7985fbb, today). (2) User is in an active interactive session — they just ran the subconscious manually. (3) All 4 implementation sketches are pre-written with exact file paths and code blocks in runs/2026-05-18/winning-concept.md. In every prior run, at least one of these was missing. Today all three are true simultaneously.

**The tool was built; now it just needs invocation.** Run 24 recommended creating the moratorium-sprint skill. Run 25 recommended invoking it. Nightly review created the skill (7985fbb). This run's only job is to trigger what's already built. The verb shifts from "create" to "say."

**Run 25 governance mandate fires.** "If not invoked by run 26: escalate to nightly-commit-review automatic trigger." We're at run 26. The sprint hasn't run. The mandate fires — honored in Phase 6 governance update regardless of whether the sprint is invoked today.

**Zero activation energy.** After reading this output, the user types "moratorium sprint" or "clear the backlog" and the skill runs. ~50 min, zero new files to create, zero new context to load.

---

## Implementation Sketch

**Estimated time: ~50 min. Invoke the skill, let it run.**

### Step 1: Invoke the skill (0 min)

In this same Claude Code session, say one of:
- "moratorium sprint"
- "clear the backlog"
- "execute pending"
- "exit moratorium"
- `/moratorium-sprint`

The skill will auto-load from `.claude/skills/moratorium-sprint/SKILL.md`.

### Step 2: Let the skill run (~50 min)

The skill will:
1. Read governance.json → extract 4 S-effort pending items
2. Create branch `moratorium-exit-sprint`
3. Execute items in order (shortest first):

| Item | Effort | Source |
|------|--------|--------|
| A: Wire check_project_invariants.py into pre-commit as Check 10 | ~5 min | runs/2026-05-18/winning-concept.md §Step 1 |
| B: Widget 3-Copy Sync Guard (check-widget-sync.sh + pre-push + CLAUDE.md fix) | ~15 min | runs/2026-05-18/winning-concept.md §Step 2 |
| C: Moratorium Escalation Protocol in nightly-commit-review SKILL.md | ~10 min | runs/2026-05-18/winning-concept.md §Step 3 |
| D: Lead Qualifier Eval CI Workflow (.github/workflows/lead-qualifier-eval.yml) | ~20 min | runs/2026-05-18/winning-concept.md §Step 4 |

4. Open draft PR via mcp__github__create_pull_request (draft=true)

### Step 3: Review and merge draft PR

Human reviews PR, merges to main. Pending 11→7 (items A–D resolved).

### Bonus: Merge 4 safe dependency PRs (~5 min)

After or alongside sprint — independent action, no moratorium conflict:
```
mcp__github__merge_pull_request for #163, #164, #102, #103
```

---

## What This Replaces

Run 25 winner: "Invoke /moratorium-sprint — execute 4 S-effort items in one session." This is the same direction — the change is that now the tool is fully built AND the user is present. The recommendation transitions from "approve and invoke" to "invoke right now."

---

## Governance Action (Phase 6)

Per run 25 mandate, REGARDLESS of sprint invocation outcome, honor the escalation by updating governance.json to flag nightly-commit-review auto-trigger as the fallback. This is a governance action, not the winner — but it must be executed this run.

---

## Confidence

**HIGH**

Evidence: three first-time conditions aligned (tool built + user present + sketches ready). Debate: SURVIVES 3 rounds. Primary challenge (same as run 25) defeated by new evidence (tool now exists + user now present). Governance mandate independently validates urgency.
