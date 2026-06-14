# Winning Concept — 2026-05-16-pm (Run 20)

## Recommendation
Implement the governance mandate from run 19: update governance.json to reduce max_pending_approvals
from 3 to 2, AND create a GH milestone "Moratorium Exit Sprint" with four S-effort issues
(runs 19/8/7/14), providing a human-actionable, time-boxed exit path that doesn't require
understanding the subconscious/ directory.

## Why This, Why Now

**Run 19 binding governance condition fires.** Run 19 winning-concept.md §"After SKILL.md Updated —
Next Run (Run 20)" explicitly states: "If SKILL.md NOT updated by run 20 — Governance action: reduce
max_pending_approvals 3→2 + create GH milestone." SKILL.md update was NOT applied — confirmed by
direct read (no "## Moratorium Escalation Protocol" section present). Condition fires unconditionally.

**Three consecutive meta-fix recommendations without implementation demand a new escalation mechanism.**
Runs 18 and 19 both recommended SKILL.md encoding of the moratorium hook. Neither was implemented. A
third SKILL.md-repeat produces zero new force. The GH milestone creates a qualitatively different
mechanism: GitHub-native sprint board that makes the exit path actionable without subconscious/
knowledge. Human sees 4 issues with time estimates in GitHub — no context required.

**Threshold reduction prevents recurrence.** The current moratorium accumulated 5 items over 30 days
before the system produced maximal escalation pressure. Lowering max_pending_approvals from 3 to 2
means moratorium fires 1 run earlier next cycle — escalation before backlog becomes unmanageable.
One configuration line; no code risk.

**Milestone fills the missing human interface.** GH #169 tells the human "moratorium active." A
milestone tells the human "here are 4 specific issues, estimated 50 min total, do them in this order,
sketches pre-written." These are different cognitive loads. The milestone reduces the barrier from
"understand governance.json" to "work down a GitHub sprint list."

## Implementation Sketch

### Bonus Step 0: SKILL.md update (run 18/19 recommendation — still valid, ~10 min)

Update `.claude/skills/nightly-commit-review/SKILL.md` per the pre-written sketch in
`subconscious/runs/2026-05-15-pm/winning-concept.md` §Steps 1-2:
- Add "## Moratorium Escalation Protocol" section after `## Output Artifacts` block
- Add step 9A to Scheduled Task Prompt

This is NOT the primary winner but should be done first/alongside — it's the prerequisite for
the daily escalation loop to work mechanically.

### Step 1: Update governance.json (~2 min)

Change `config.max_pending_approvals` from 3 to 2:
```json
"max_pending_approvals": 2
```

Add note to `moratorium_config.trigger_reason` (append):
```
"Run 20 (2026-05-16-pm): max_pending_approvals lowered 3→2 per run 19 governance mandate."
```

### Step 2: Create GH milestone via mcp__github__ (~5 min)

**Title:** `Moratorium Exit Sprint`

**Description:**
```
Subconscious moratorium: 5 recommendations pending (oldest: 30 days). Exit requires 4 S-effort
items (~50 min total). Implements run 19 governance mandate.

Priority order:
1. Run 19: SKILL.md Moratorium Escalation Protocol (~10 min)
2. Run 8: Wire check_project_invariants.py to pre-commit (~5 min)
3. Run 7: Widget 3-Copy Sync Guard (scripts/check-widget-sync.sh) (~15 min)
4. Run 14: Wire lead qualifier eval to CI (~20 min)

Implementation sketches: subconscious/runs/2026-05-15-pm/winning-concept.md
After all 4: pending drops 5→1 (only run 4 AI-to-Human Handoff remains, M-effort).
```

**Due date:** 2026-05-30 (2-week window)

### Step 3: Create 4 GH issues linked to milestone (~15 min)

**Issue A: [Moratorium] SKILL.md Moratorium Escalation Protocol (~10 min)**
- Body: Add "## Moratorium Escalation Protocol" section + step 9A to
  `.claude/skills/nightly-commit-review/SKILL.md`. Full sketch in
  `subconscious/runs/2026-05-15-pm/winning-concept.md` §Steps 1-2.
  Converts one-time GH event to daily sustained escalation loop.
- Labels: `subconscious`, `moratorium`, `s-effort`
- Milestone: Moratorium Exit Sprint

**Issue B: [Moratorium] Wire check_project_invariants.py into pre-commit (~5 min)**
- Body: Add call block to `scripts/hooks/pre-commit` after existing final check.
  Script at `scripts/check_project_invariants.py` passes 6/6 checks (as of run 14 verification).
  Blocks commits with client_id/status/areas_of_interest naming violations.
- Labels: `code-health`, `moratorium`, `s-effort`
- Milestone: Moratorium Exit Sprint

**Issue C: [Moratorium] Widget 3-Copy Sync Guard (scripts/check-widget-sync.sh) (~15 min)**
- Body: Create `scripts/check-widget-sync.sh` that diffs widget/, frontend/public/widget/,
  and landing-page-v2/widget/. Exit 1 on diverge. Wire to `scripts/hooks/pre-push`.
  Fix CLAUDE.md Invariant #4: "2 copies" → "3 copies (widget/, frontend/public/widget/,
  landing-page-v2/widget/)". Full sketch in `subconscious/runs/2026-05-08/winning-concept.md`.
- Labels: `code-health`, `moratorium`, `s-effort`
- Milestone: Moratorium Exit Sprint

**Issue D: [Moratorium] Wire lead qualifier eval harness to CI (~20 min)**
- Body: Create `.github/workflows/lead-qualifier-eval.yml` with Monday cron + PR trigger.
  Add LEAD_QUALIFIER_AGENT_ID as GH Secret. Harness already passes locally:
  `backend/tests/evals/test_lead_qualifier_golden.py` + `lead_qualifier_golden.json` (7854ede).
  Closes Issue #110.
- Labels: `testing`, `moratorium`, `s-effort`
- Milestone: Moratorium Exit Sprint

### Total effort: ~32 min (Steps 1-3 + 4 issues, excluding Bonus Step 0)

---

## What This Replaces

Run 19's recommendation to formally encode Moratorium Escalation Protocol in SKILL.md (2026-05-16).
That recommendation remains valid and is preserved as Bonus Step 0, but is no longer the primary
winner. The governance mandate supersedes it: run 19 explicitly wrote that SKILL.md not updated by
run 20 triggers governance escalation, not a third SKILL.md recommendation.

---

## After Run 20 Implemented — Next Run (Run 21)

**If GH milestone created + any S-effort item implemented:**
- Count pending: if ≤3, moratorium exits and free-choice runs resume
- Run 21 winner: first post-moratorium item (Zapier API key fix, ROI 2.5 — highest security ROI)
- OR: promote ai-ready issues (Idea 4) if issue-to-pr-loop confirmed running

**If run 20 NOT implemented by run 21:**
- Moratorium stalled at governance mandate layer (meta of meta)
- Governance action: open a P0 GH issue "Subconscious backlog unactioned 30+ days — sprint required"
  with explicit escalation to product blocker

**Run 4 parallel track:**
- AI-to-Human Handoff (30+ days) needs sprint allocation regardless of moratorium status
- Run 21 should create dedicated sprint-allocation issue for run 4 if not started

---

## Confidence

**HIGH** — Evidence: (1) Run 19 governance condition fires unconditionally (SKILL.md not updated,
confirmed by direct read); (2) Debate: Idea 1 SURVIVES, Idea 2 KILLED (mechanism unchanged, freeze
risk), Idea 4 WEAKENED (loop uncertainty); (3) Milestone is qualitatively new mechanism vs GH #169;
(4) Threshold reduction is a config change with zero code risk; (5) All 4 S-effort items have
pre-written implementation sketches; (6) Implementation effort ~32 min (Steps 1-3).
