# Winning Concept — 2026-05-17-pm (Run 22)

## Recommendation

Wire `scripts/check_project_invariants.py` into the pre-commit hook as Check 10 — a 5-minute
atomic action the human can execute RIGHT NOW in this active session, breaking the 12-day
zero-implementation streak with the lowest-friction pending item in the backlog.

---

## Why This, Why Now

**The human is present.** Every prior subconscious run produced recommendations and then the human
was absent for days. This session is different — the human ran the subconscious interactively.
The implementation window is open right now. The recommendation must match: smallest possible
action, zero external dependencies, executable in <5 minutes.

**Run 8 mandate is 22 days stale.** `037865f` (2026-04-25) added `scripts/check_project_invariants.py`.
The script was purpose-built for pre-commit integration, passes all 6 checks as of today, has
no external dependencies, and has been sitting unwired for 22 days. Every production commit since
then runs without the invariant check. One line of integration eliminates the gap.

**Zero blockers.** The em-dash blocker (WizardStepAutoKB.jsx violations) that delayed this in
runs 10-12 was cleared by 8f680e8 on 2026-05-05. Pre-commit has 9 checks — this becomes Check 10.
Script is stdlib-only. No `pip install`. No config. No GH secrets.

**One implementation resets the narrative.** 12 days of zero production commits. 7 items pending.
The moratorium exit condition is pending ≤ 3. This single action takes pending to 6 — not exit,
but it proves the implementation loop is alive. The remaining 3 S-effort items (runs 7+14+19,
~45 min) become the next sprint.

---

## Implementation Sketch

**Time: ~5 minutes.**

### Step 1: Open pre-commit hook

```
scripts/hooks/pre-commit
```

Current Check 9 (JS silent catch guard) ends around line 220-240 (added by 72f8204).
Locate it and add Check 10 immediately after.

### Step 2: Add Check 10 (3 lines)

```bash
# Check 10: Project invariants (client_id, status, areas_of_interest naming)
echo "Running project invariants check..."
python3 scripts/check_project_invariants.py || exit 1
```

### Step 3: Verify

```bash
# Should pass immediately (script passes all 6 checks as of 2026-05-17)
python3 scripts/check_project_invariants.py
# Expected output: all PASS, exit 0

# Make a test commit — hook should not block clean code
git add -A && git commit --allow-empty -m "test: verify Check 10 fires correctly"
```

### Step 4: Done

Commit `scripts/hooks/pre-commit` change as:
```
chore: wire check_project_invariants.py into pre-commit as Check 10 (run 8, closes 22-day gap)
```

---

## What This Replaces

Run 21's AI-to-Human Handoff GH Issue recommendation remains valid and is NOT replaced — it's
in the parking lot. Run 21's winning-concept.md has the full implementation sketch. The human
should create that GH issue independently when time permits (no new recommendation needed from
run 22 on that topic).

Run 22 winner is the most atomic action to re-establish implementation momentum.

---

## After Implementing This

**Immediate next sprint (~45 min) — drops pending 6→3, moratorium exits:**

| Run | Item | Effort | Sketch location |
|-----|------|--------|-----------------|
| 19 | Add Moratorium Escalation Protocol section to nightly-commit-review SKILL.md | ~10 min | `subconscious/runs/2026-05-16/winning-concept.md` §Steps 1-2 |
| 7 | Create scripts/check-widget-sync.sh + wire pre-push + fix CLAUDE.md Invariant #4 | ~15 min | `subconscious/runs/2026-05-15-pm/winning-concept.md` |
| 14 | Create .github/workflows/lead-qualifier-eval.yml (Monday cron + PR trigger) | ~20 min | `subconscious/runs/2026-05-05-pm/winning-concept.md` |

All three have pre-written implementation sketches. Together: ~45 min. Pending drops 6→3.
Moratorium exits. Run 23 is a free-choice run.

**After moratorium exits (Run 23 candidates):**
- AI-to-Human Handoff v1 feature build (M-effort, 1.5 days, CRITICAL)
- Zapier API key plan_status enforcement (GH #107, ROI 2.5, ~2h)
- Email sequences N+1 fix (GH #112, ROI 2.3)

---

## Confidence

**HIGH** — Evidence is unambiguous: script exists, passes all checks, pre-commit is the integration
point, zero external dependencies, em-dash blocker cleared 12 days ago. The only uncertainty is
whether the human acts on it — mitigated by the active session window. Debate: Idea 1 WEAKENED
(loop config unverifiable), Idea 2 SURVIVES → WINNER, Idea 3 WEAKENED (run 21 same-day repeat).
