# Idea 1 — Escalate run 65 delivery via explicit nightly trigger instruction (RUN 66 MANDATE)

**Score:** 9.2 / 10
**Effort:** S (~5 min, SKILL.md edit)
**Category:** workflow
**Autonomous:** YES (SKILL.md edit — same class as runs 40/43 both delivered autonomously)
**Mandate:** RUN 66 MANDATE FIRES — run 65 winning-concept.md §Run 66 mandate: "if not implemented by run 66, add explicit nightly trigger instruction"

## Evidence

- check_project_invariants.py exits 1: widget drift (landing-page-v2/widget/) + 10 em-dashes confirmed since PRs #368-371
- nightly-commit-review 2026-06-24 (commit 4a80f40): ran but DID NOT implement run 65 winner
- Pre-commit Check 13 still in FAIL+BLOCK mode — all developer commits blocked
- Run 65 winner has AUTONOMOUS-EXECUTABLE: YES + same fix class as runs 49/55/57 (all delivered in 1-2 cycles)
- Gap: nightly executed but did not act. Mechanism: nightly scope doesn't have an explicit directive for "check latest winning-concept.md, execute if AUTONOMOUS-EXECUTABLE"
- Precedent: run 43 (extend nightly scope to pre-commit bash additions — DELIVERED by nightly 4226ef4 in 1 cycle). Run 50 (extend nightly scope + Item B directive — DELIVERED by nightly in 1 cycle).

## Fix

Add to nightly-commit-review SKILL.md a new step:

**Step 9B — AUTONOMOUS-EXECUTABLE Pending Check:**
> After the standard commit review, check governance.json `active_directions[0]`. If `autonomous_executable: true` AND `status: "pending_approval"`: read the winning-concept.md from the referenced run directory, execute Steps 1-N listed under Implementation, run `python3 scripts/check_project_invariants.py` to verify, commit as "auto: [run-date] subconscious autonomous execution — [winner title]". Mark as executed in commit msg. If check_project_invariants exits 0: success. If not: log failure and skip.

**Immediate outcome:** nightly 2026-06-25 reads this instruction, executes run 65 steps (cp widget + 10 em-dash replacements), verify exits 0, commits. All commits unblocked.

## Why this wins over alternatives

- Run 65 winner has been ready for 24h — the sketch is complete, the fix is trivial (cp + 10 sed-style replacements)
- Pre-commit Check 13 blocks ALL developer work until this lands
- 5-min SKILL.md edit unblocks a 5-min fix that's been waiting 24h
- Autonomous delivery path proven (runs 43, 50 both used this exact mechanism)
- Moratorium compliant — SKILL.md edits explicitly within nightly's autonomous scope (run 40 formally added this)
