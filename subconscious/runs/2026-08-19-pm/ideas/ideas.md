# Run 108 Ideas — 2026-08-19-pm

**Context:** Step 9I confirmed implemented (run 107). 6 Dependabot PRs aging 2-17d. GH #399/#403 both 42d+ open. KB 27d stale. Nightly-2026-08-19 ran 0 product fixes (2 operational log commits). First nightly with Step 9I active fires 2026-08-20.

---

## Idea 1 — Step 9J: Dependabot Auto-Merge in Nightly (AUTONOMOUS-EXECUTABLE)
**Category:** workflow  
**Effort:** S (~50 lines bash block in SKILL.md)  
**Confidence:** HIGH

Add Step 9J bash block to `.claude/skills/nightly-commit-review/SKILL.md`. Every nightly run:
1. `mcp__github__list_pull_requests` (state=open, perPage=50) — filter head.ref starts with "dependabot/"
2. For each: check CI via `mcp__github__actions_list` on head SHA
3. If ALL checks passing AND no requested reviewers AND not draft: `mcp__github__merge_pull_request` (squash)
4. Log: "Step 9J: {N} reviewed, {M} merged, {K} skipped"

**Evidence:** 6 Dependabot PRs aging: #629/#630/#631 (17d), #665/#666 (2d), #598 (pip/stripe), #597/#596/#595/#594 (other pip). Run 107 parking lot explicitly flags as run 108 candidate. Morning digest 2026-08-19 flagged 6 dep PRs daily for 7+ days. skill-discovery-2026-08-17 proposed `dependabot-merge-runner` skill with identical heuristic (CI green + no requested reviews = safe). Channel proven: Steps 9C/9E/9F/9G/9I all implemented via SKILL.md-edit.

**Risk:** Squash merge on bad dep could break build. CI gate prevents this — if CI red, skip. No manual review removed that wasn't already absent (Dependabot PRs get auto-reviewed by CI only, no human requested reviewers).

---

## Idea 2 — stale-autonomy-pr-closer SKILL.md
**Category:** workflow  
**Effort:** M (complex dedup/superseding detection logic)  
**Confidence:** MEDIUM

Create `.claude/skills/stale-autonomy-pr-closer/SKILL.md` — scan draft PRs >10 days old from subconscious branch pattern, close superseded ones with comment, label still-valid ones "stale-but-valid".

**Evidence:** 7 open subconscious PRs (#626 9d, #613 11d, #611 12d, #606 14d, #575 26d+, #648 13d, #653 10d). Run 107 parking lot: defer until pile >8 drafts. Currently 7 — approaching threshold.

**Risk:** False-positive closures. Superseding detection across PR descriptions is brittle. Root cause is GH #399 blocking autopilot-issue-loop, not an orchestration problem. Closing PRs doesn't fix #399. M-effort with destructive risk.

---

## Idea 3 — Post PR #660 merge-readiness comment (one-time action)
**Category:** workflow  
**Effort:** XS (one GH comment)  
**Confidence:** HIGH

PR #660 (scoring_config.py block_demo_role fix) has been ai-ready for 3d with CI green. Comment on PR #660 with merge-now recommendation and impact summary.

**Evidence:** PR #660 exists (confirmed run 107). GH #661 tracks the gap. Loop stalled (GH #399). Human needs nudge.

**Risk:** Minimal. But: one-time action, not structural. Does not address systemic workflow gap. Low leverage.

---

## Idea 4 — KB autopopulate local fallback (subconscious-side workaround)
**Category:** operational  
**Effort:** M (script authoring + env setup)  
**Confidence:** LOW

Write a script that runs kb-autopopulate locally in the subconscious session without GH Actions, using the session's available ANTHROPIC_API_KEY.

**Evidence:** KB 27d stale. GH #403 blocks GH Actions path. Subconscious session has model access.

**Risk:** Session doesn't have ANTHROPIC_API_KEY in env. This path was killed in run 104 governance corrections ("mechanism mismatch: session doesn't have ANTHROPIC_API_KEY env var access"). Re-debating a killed mechanism is prohibited per governance.

---

## Idea 5 — Morning digest summary GH issue for human-only blockers
**Category:** workflow  
**Effort:** S (~30 lines, one GH issue)  
**Confidence:** MEDIUM

File a consolidated GH issue "Human Action Required: 3 critical blockers (GH #399/#403/#394)" with a combined action checklist and daily-stale counts.

**Evidence:** 3 blockers aging 17-42d with zero human action. Morning digest flags them daily but silently (no new GH pressure).

**Risk:** GH #399 and #403 both already have open issues with multiple comments. Consolidation issue duplicates existing tracking. Low incremental value. Human has seen #399/#403 comments many times.

---

## Ranking

1. **Idea 1 (Step 9J)** — SURVIVES → top candidate. Autonomous-executable, proven channel, strong evidence (6 PRs aging), CI gate makes it safe, parking-lot promoted by run 107.
2. **Idea 2 (stale PR closer)** — WEAKENED → parking lot. M-effort, destructive risk, root cause is #399.
3. **Idea 3 (PR #660 comment)** — not top-3; one-time action only.
4. **Idea 4 (KB local fallback)** — KILLED → governance prohibits re-debating killed mechanisms.
5. **Idea 5 (blocker consolidation)** — not top-3; duplicates existing tracking.
