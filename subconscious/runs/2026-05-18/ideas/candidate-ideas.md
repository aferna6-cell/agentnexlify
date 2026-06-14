# Candidate Ideas — 2026-05-18 (Run 23)

**Evidence context:** Zero production commits day 13 (since 72f8204 2026-05-05). Pending=8
pre-run. check_project_invariants.py PASSES all 6 checks (verified live this run). All 4
S-effort items remain unimplemented. Human present in active session. Run 20 governance
mandate (max_pending 3→2) fires unconditionally this run.

---

### Idea 1: Consolidate All 4 S-effort Items into Single Sprint PR

**Evidence:**
- 4 items pending 13–24 days each, all with pre-written implementation sketches
- All 4 are purely additive (new scripts, new CI files, new SKILL.md section, 3-line hook addition)
- None modify existing production code behavior
- Total implementation time: ~50 min for all 4 together
- Every previous run recommended these items separately — separate approval friction may be the blocker
- check_project_invariants.py passes all 6 checks right now (verified live)

**Action:** Create single branch `moratorium-exit-sprint` with all 4 changes:
1. `scripts/hooks/pre-commit` — add 3 lines (Check 10: check_project_invariants)
2. `scripts/check-widget-sync.sh` — new file + wire into pre-push + fix CLAUDE.md Invariant #4
3. `.claude/skills/nightly-commit-review/SKILL.md` — add Moratorium Escalation Protocol section (~10 lines)
4. `.github/workflows/lead-qualifier-eval.yml` — new file (Monday cron + PR trigger)

Open as draft PR. One approval implements all 4.

**Impact:** Pending 8→4 (+ run 23 = 9→5). Closest to moratorium exit in 23 runs. One
decision instead of four. Approval friction: 1x vs 4x.

**Category:** workflow / code_health

---

### Idea 2: Wire check_project_invariants.py into Pre-commit (Run 22 Re-escalation)

**Evidence:**
- Script passes all 6 checks (verified this run)
- NOT in pre-commit — confirmed via `grep check_project_invariants scripts/hooks/pre-commit` → NOT FOUND
- Run 8 mandate: 23 days stale (037865f added the script 2026-04-25)
- Em-dash blocker cleared 2026-05-05 (8f680e8)
- Same winner as run 22 — human present in that session too but didn't implement

**Action:** Add 3 lines to `scripts/hooks/pre-commit` after Check 9:
```bash
# Check 10: Project invariants (client_id, status, areas_of_interest naming)
echo "Running project invariants check..."
python3 scripts/check_project_invariants.py || exit 1
```

**Impact:** Pending 9→8. One guard active. Proves implementation loop alive.

**Category:** code_health

---

### Idea 3: /sprint Slash Command for Moratorium Exit

**Evidence:**
- `.claude/commands/` has 19 existing commands; `/morning`, `/evening`, `/checkpoint`, `/recover` pattern established
- All 4 S-effort items have pre-written implementation sketches in `subconscious/runs/*/winning-concept.md`
- Moratorium pattern repeats: backlog accumulates → S-effort sprint needed → manual process
- Skills/commands infrastructure fully operational

**Action:** Create `.claude/commands/sprint.md` that:
1. Reads `subconscious/state/governance.json` active_directions where status=pending_approval
2. Filters for S-effort items (≤30 min)
3. Reads `winning-concept.md` for each
4. Executes implementation steps sequentially

**Impact:** Reusable moratorium exit automation. Future runs exit moratorium in same session
instead of waiting for manual human sprint. Converts 50-min manual work to 1 command.

**Category:** workflow

---

### Idea 4: Auto-Approve Micro-Guard Policy in governance.json

**Evidence:**
- Average days-pending for S-effort hook/CI items: 18 days (runs 7, 8, 14, 19)
- All are purely additive: new files or ≤5 lines to existing hooks
- `auto_approve: false` was designed to prevent large-scope auto-implementation; doesn't distinguish by risk tier
- Implementation lag is the primary moratorium driver, not review quality gaps

**Action:** Add `"auto_approve_micro_guard": true` to governance.json config. Criteria: category=code_health
+ effort=S + change_type in (hook_wiring, new_script, new_ci_file, skill_md_addition). Requires
SKILL.md Phase 5 update to act on the field.

**Impact:** Future S-effort guard items auto-implemented same-run. Eliminates 18-day average
lag for the lowest-risk improvements. Moratorium would never re-trigger for hook-wiring items.

**Category:** workflow

---

### Idea 5: Investigate Autopilot-Issue-Loop Status + Tag 4 Items as ai-ready

**Evidence:**
- Loop confirmed dormant via git (zero commits 13 days) but NOT confirmed via direct process/GH check
- Possibility: loop running but starved of ai-ready tagged issues (no new tags since confirmation)
- SKILL.md: loop polls assigned GH issues every 15 min; Haiku classifies, Sonnet implements
- GH issues exist for items 7 (#107 area), 8, 14 (#110), 19; adding ai-ready label = free implementation
- Issue-to-pr-loop could implement all 4 S-effort items without any human coding

**Action:** (1) Check `ps aux | grep issue-to-pr-loop` + GH Actions for loop status. (2) If running:
add `ai-ready` label to GH issues for runs 7, 8, 14, 19. (3) If not running: create GH issue to
restart with Railway cron config.

**Impact:** If loop running: all 4 items implemented without human coding, pending 9→5. If not:
clear restart path. Expected value high given loop architecture already exists.

**Category:** operational / workflow
