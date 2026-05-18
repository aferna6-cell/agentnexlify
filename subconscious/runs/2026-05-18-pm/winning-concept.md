# Winning Concept — 2026-05-18-pm (Run 24)

## Recommendation

Create `.claude/skills/moratorium-sprint/SKILL.md` — a slash command that reads `governance.json`, loads implementation sketches from `winning-concept.md` files, and executes all pending S-effort items in one session, ending with a draft PR.

---

## Why This, Why Now

**The bottleneck is execution friction, not knowledge.** Nine consecutive moratorium runs have described the same 4 implementation sketches in increasing detail. Every run loads ~15-20 min of context before any execution begins, then stops. The 65-min total execution effort is not the barrier — the per-session context-loading overhead is. A single slash command that reads `governance.json` → locates sketches → executes → opens PR converts 65 min of multi-session effort into one coherent session.

**Skill discovery validated this directly.** The 2026-05-18 skill discovery report (generated from 17 automated commits over 7 days) proposed `moratorium-sprint` as its top skill — the system's first self-generated proposal to automate sprint execution. Evidence: "Without this skill, each session re-reads all the context (governance.json, 4+ winning-concept.md files, improvement-backlog.md) before doing work — ~15 min of context loading per attempt."

**This run's mechanism change is tooling, not framing.** Runs 15–23 changed the framing each time (re-escalation → escalation hook → SKILL.md encoding → governance mandate → GH milestone → AI-to-Human pivot → atomic item → sprint PR). All were recommendation-layer changes. This run creates the execution layer — a tool that converts approved recommendations into code.

**One S-effort file creation unlocks recurring value.** The moratorium has triggered twice (runs 1-13, runs 15+). A reusable skill is a 20-min investment against a recurring 65-min cost.

---

## Implementation Sketch

**Estimated time: ~20 minutes. One new file.**

### Step 1: Create skill directory

```bash
mkdir -p .claude/skills/moratorium-sprint
```

### Step 2: Create SKILL.md

Create `.claude/skills/moratorium-sprint/SKILL.md` with the following content:

```markdown
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
```

### Step 3: Verify skill is loadable

```bash
ls .claude/skills/moratorium-sprint/SKILL.md
head -5 .claude/skills/moratorium-sprint/SKILL.md
```

Verify frontmatter parses correctly.

### Step 4: Test the trigger

In the same session, invoke: `moratorium sprint` → confirm skill loads and begins Phase 1.

### Step 5: Commit

```bash
git add .claude/skills/moratorium-sprint/SKILL.md
git commit -m "feat: add moratorium-sprint skill — execute S-effort backlog in one session (run 24)"
```

---

## What This Replaces

Run 23's winner ("Moratorium Exit Sprint PR — 4 S-effort items in one branch") remains valid and is NOT replaced. This skill is the *execution vehicle* for run 23's recommendation. After the skill exists, invoking `/moratorium-sprint` in the next session executes the run 23 sprint plan directly.

Run 21's AI-to-Human Handoff GH Issue remains in the parking lot — M-effort, requires separate session.

---

## What Comes After

After skill created (this run, ~20 min):

**Immediate next session:** Invoke `/moratorium-sprint` → executes all 4 S-effort items → opens draft PR → pending 10→6 when merged.

**After sprint PR merged (pending 6):**
- Remaining: run 4 (AI-to-Human Handoff, M-effort), run 21 (GH issue, S-effort), plus governance resolutions
- Effective pending after resolutions: ~3-4
- Moratorium exit condition: pending ≤ 2

**Run 25 candidates (if moratorium exits):**
- AI-to-Human Handoff v1 feature build (M-effort, CRITICAL, oldest=33 days)
- Zapier API key plan_status enforcement (ROI 2.5, GH #107, security)
- Email sequences N+1 fix (ROI 2.3, GH #112)

**Bonus (non-winner):**
- Merge safe dep PRs #163, #164, #102, #103 (independent of moratorium, morning-routine action)

---

## Confidence

**HIGH** — Skill discovery provided direct evidence (first time external validation of this exact idea). The skill template above is complete and executable. Only uncertainty: whether the trigger word in the next session fires the skill correctly (verify frontmatter triggers list). Debate outcome: Idea 1 SURVIVES (3 rounds), Idea 2 WEAKENED → parking lot, Idea 3 KILLED (10th repetition, mechanism change mandated).
