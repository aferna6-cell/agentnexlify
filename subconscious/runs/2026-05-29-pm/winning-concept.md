# Winning Concept — 2026-05-29-pm (Run 40)

## Recommendation

Update `.claude/skills/nightly-commit-review/SKILL.md` to explicitly include creating new `.claude/skills/*/SKILL.md` files as a LOW-risk autonomous action when `subconscious/winning-concept.md` contains the `AUTONOMOUS-EXECUTABLE` label — fixing the root cause of why post-split-test-repair SKILL.md has been skipped for 2 consecutive nightly cycles.

---

## Why This, Why Now

Nightly review `dc5ef8e` (2026-05-28) explicitly logged "run 36 winner: Create post-split-test-repair SKILL.md — **docs only, skipped**" — direct behavioral evidence that the nightly review classifies `.md` file creation as outside its autonomous scope, even when the winning-concept.md carries the `AUTONOMOUS-EXECUTABLE` label. Code changes (Check 11 bash block, 72f8204 JS silent catch) succeed 100% via nightly. Pure `.md` creation fails 100% across 2 cycles. This is a scope rule, not a timing gap. Fixing one line in nightly-commit-review SKILL.md propagates to all 54 remaining god-class splits — each will need a SKILL.md-level guide — versus creating one .md file manually which solves only the current instance.

---

## Implementation Sketch

### Step 1: Read the current nightly-commit-review SKILL.md
```bash
cat .claude/skills/nightly-commit-review/SKILL.md
```
Locate the section defining "LOW-risk scope" or "what nightly may execute autonomously."

### Step 2: Add explicit rule for SKILL.md creation
In the LOW-risk autonomous scope section, add:

```markdown
**SKILL.md creation rule:** When `subconscious/winning-concept.md` (or the most recent
winning-concept.md in `subconscious/runs/`) contains the text `AUTONOMOUS-EXECUTABLE`,
creating a new `.claude/skills/<name>/SKILL.md` file is LOW-risk and within autonomous
scope. Execute directly — do not label as "docs only" and skip.

Example: if winning-concept.md says "AUTONOMOUS-EXECUTABLE: create
`.claude/skills/post-split-test-repair/SKILL.md`", create the file using the content
from the winning-concept.md §Implementation Sketch section.
```

### Step 3: Verify the change
```bash
grep -A 8 "SKILL.md creation rule" .claude/skills/nightly-commit-review/SKILL.md
```

### Step 4: Bonus Action — create post-split-test-repair SKILL.md now (5 min, human-present)
Human is present in this session. Content is pre-written in `subconscious/runs/2026-05-29/winning-concept.md §Implementation Sketch`. Do not wait for the nightly cycle to prove the fix works — create it now.

```bash
mkdir -p .claude/skills/post-split-test-repair
# Copy content from subconscious/runs/2026-05-29/winning-concept.md lines 22-93
```

### Step 5: Commit both changes
```bash
git add .claude/skills/nightly-commit-review/SKILL.md .claude/skills/post-split-test-repair/SKILL.md
git commit -m "fix(nightly): scope SKILL.md creation as autonomous LOW-risk + add post-split-test-repair skill"
```

---

## What This Replaces

Previous active direction was "Create post-split-test-repair SKILL.md (run 39 winner, AUTONOMOUS-EXECUTABLE)" — that recommendation identified the WHAT but not the WHY it failed twice. This run's winner identifies the root cause (nightly scope classification) and fixes it systemically. The post-split-test-repair SKILL.md creation is now a Bonus Action captured in Step 4.

---

## Standing Actions (Unchanged)

In priority order:

1. **GH #181 billing fix (~15 min, HUMAN REQUIRED):** `billing.py` add `15000: "autopilot"`, `25000: "professional"` to `AMOUNT_TO_PLAN`; remove backwards test assertions `test_billing_amount_to_plan.py:38-44`. Check 11 fires WARNING on every commit as reminder.
2. **AI-to-Human Handoff v1 (~1 day):** run 38 winner, 43+ days. Agent OS plumbing ready (`os_outbound_mirror.py`, PR #188 merged).
3. **Invoke /moratorium-sprint (~40 min):** Items A (check_project_invariants), B (widget sync guard), D (CI eval). Day 25+. Tool ready (`7985fbb`).
4. **email_sequences.py split (~2h):** After post-split-test-repair SKILL.md exists.

---

## Confidence

**HIGH** — direct behavioral evidence from `dc5ef8e` nightly log ("docs only, skipped") confirms root cause. Fix is a small additive edit to one SKILL.md (LOW-risk). The 2-cycle failure pattern (runs 36+39) provides strong signal. Bonus Action (Step 4) is a 5-min fallback that works regardless of whether the channel fix takes effect tonight.
