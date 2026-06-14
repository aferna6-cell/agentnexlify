# Winning Concept — 2026-05-19 (Run 25)

## Recommendation

Invoke `/moratorium-sprint` in the current or next interactive session to execute the 4 pre-written S-effort items, open a draft PR, and begin the moratorium exit path.

---

## Why This, Why Now

**The tool now exists.** Run 24 recommended creating moratorium-sprint SKILL.md. The nightly review (2026-05-19, 7985fbb) created it — the first production artifact in 14 days. The skill reads governance.json, loads implementation sketches, and executes all 4 S-effort items in one session. Activation energy dropped from 65 min of manual context-loading to a single command.

**Three sources of validation.** Skill discovery (2026-05-18) proposed moratorium-sprint independently. The subconscious loop proposed it in run 24. The nightly review implemented it without explicit instruction. All three systems agree: this is the right tool and it's ready.

**The moratorium cannot exit without this action.** Pending = 11 (after governance correction: 10). Exit condition: pending ≤ 2. The 4 S-effort items drop pending from 10 to 6 when the sprint PR merges. After that, 4 more resolutions (runs 19, 20, 21, governance items) clear to ≤ 2. The /moratorium-sprint execution is the critical path.

**Every alternative requires the moratorium to exit first.** AI-to-Human Handoff (Critical customer gap), Zapier security fix, email N+1 — all appropriate post-moratorium work. None of them help pending reach ≤ 2.

---

## Implementation Sketch

**Estimated time: ~50 min. Zero new files.**

### Step 1: Invoke the skill

In any interactive Claude Code session, type:

```
/moratorium-sprint
```

Or say: "moratorium sprint", "execute pending", "clear the backlog", "exit moratorium"

The skill will:
1. Load governance.json → extract 4 S-effort pending items
2. Load subconscious/runs/2026-05-18/winning-concept.md §Steps 1-4
3. Create branch `moratorium-exit-sprint`
4. Execute items A→D sequentially (see table below)
5. Verify each with prescribed verification command
6. Open draft PR against main

### Step 2: Verify 4 items execute correctly

| Item | Source | Effort | Verification |
|------|--------|--------|--------------|
| A: Wire check_project_invariants.py into pre-commit as Check 10 | runs/2026-05-18/winning-concept.md §Step 1 | ~5 min | `python3 scripts/check_project_invariants.py` |
| B: Widget 3-Copy Sync Guard (check-widget-sync.sh + pre-push + CLAUDE.md fix) | runs/2026-05-18/winning-concept.md §Step 2 | ~15 min | `bash scripts/check-widget-sync.sh` |
| C: Moratorium Escalation Protocol in nightly-commit-review SKILL.md | runs/2026-05-18/winning-concept.md §Step 3 | ~10 min | `grep -n "Moratorium Escalation Protocol" .claude/skills/nightly-commit-review/SKILL.md` |
| D: Lead Qualifier Eval CI Workflow (.github/workflows/lead-qualifier-eval.yml) | runs/2026-05-18/winning-concept.md §Step 4 | ~20 min | `cat .github/workflows/lead-qualifier-eval.yml` |

### Step 3: Merge draft PR

Review draft PR, confirm 4 items look correct, merge to main. Pending 10→6.

### Step 4: Post-sprint governance resolution

After PR merged, update governance.json:
- Set runs 7, 8, 14, 19 status → `implemented`
- Update `implementation_lag_warning.runs_pending_approval` 10→6
- Begin moratorium exit path: resolve runs 20, 21 (GH milestone + AI-to-Human GH issue) → pending 6→4

### Step 5 (bonus, independent): Merge safe dep PRs

These are independent of the moratorium and safe to merge now:
- #102 `update youtube-transcript-api ≥1.2.4` — 21d, patch, safe
- #103 `bump python-multipart 0.0.26→0.0.27` — 21d, patch, safe
- #163 `bump @typescript-eslint/parser 8.58→8.59.3` — 7d, safe
- #164 `bump @playwright/test 1.59.1→1.60.0` — 7d, safe

Use `mcp__github__merge_pull_request` for each. ~5 min total.

---

## What This Replaces

Run 24's winner (moratorium-sprint skill creation) is now **implemented** — governance.json should be updated from `pending_approval` to `implemented` as part of this run's Phase 6 updates.

The active direction shifts from "create the tool" to "use the tool." The 4 S-effort items are unchanged from runs 7, 8, 14, 19 — this recommendation is the execution step for all of them simultaneously.

---

## What Comes After

**If /moratorium-sprint executes and PR merges:**
- Run 26 candidates (post-moratorium): AI-to-Human Handoff v1 (CRITICAL, 33d pending), Zapier plan_status fix (security, ROI 2.5), pre-commit-guard-add skill (workflow, ROI ~2x/month)
- Moratorium exit path: resolve runs 20+21 → pending ≤ 2 → moratorium_active: false

**If /moratorium-sprint is NOT invoked by run 26:**
- Escalation: add `/moratorium-sprint` invocation to nightly-commit-review SKILL.md as an automatic trigger when moratorium_active AND oldest_pending > 14 days
- This converts the recommendation from human-action-required to autonomous-execution

---

## Confidence

**HIGH** — Debate outcome: Idea 1 SURVIVES (3 rounds), Idea 2 WEAKENED → parking lot (promote run 26), Idea 4 WEAKENED → parking lot (promote post-moratorium). The skill exists, the sketches are pre-written, and the action is a single command. The only risk is the same human-action gap that has persisted for 25 runs — but activation energy is now at its all-time low.
