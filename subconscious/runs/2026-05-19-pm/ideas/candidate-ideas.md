# Candidate Ideas — 2026-05-19-pm (Run 26)

## Evidence Context (200 words)

Run 25 winner was "Invoke /moratorium-sprint" — tool created by nightly review (7985fbb). 4 S-effort items still MISSING as of run 26: (A) check_project_invariants NOT in pre-commit [grep confirmed], (B) check-widget-sync.sh MISSING [ls confirmed], (C) nightly-commit-review SKILL.md has no Moratorium Escalation Protocol [grep: 0 results], (D) lead-qualifier-eval.yml MISSING [ls confirmed]. Zero production feature commits 14 days (since 72f8204 May 5). Pending approvals: 10 existing + 1 new = 11 total. Moratorium exit condition: pending ≤ 2. moratorium-sprint SKILL.md fully documented with exact triggers and step-by-step execution. Skill discovery 2026-05-18 proposed 3 new skills: moratorium-sprint (now built), pre-commit-guard-add, dep-batch-merge. Run 25 governance mandate: "If not invoked by run 26: escalate to nightly-commit-review automatic trigger." USER IS PRESENT in interactive session. Bug patterns: Zapier plan_status bypass (GH #107, security, open). Customer gaps: AI-to-Human Handoff (Critical, all 7 industries, day 33). 4 safe dep PRs aging 7–21 days (#163, #164, #102, #103).

---

## Idea 1: Invoke /moratorium-sprint — Lowest Friction in 26 Runs

**Evidence:** moratorium-sprint SKILL.md exists (7985fbb, 2026-05-19). 4 S-effort items pre-written with exact implementation sketches in runs/2026-05-18/winning-concept.md. User is in active interactive session (ran subconscious interactively). Run 25 governance mandate fires this run. Activation energy: type one command after reading this output.

**Action:** Invoke the moratorium-sprint skill in this same session: say "moratorium sprint" or "clear the backlog" or "execute pending". Skill executes A→D sequentially (~50 min), opens draft PR, pending 11→7 when merged.

**Impact:** First sprint PR in 26 runs. Pending 11→7 (items A-D resolved). Moratorium still active but critical path unblocked. Downstream: AI-to-Human Handoff, Zapier fix, email N+1 all unblocked once pending ≤ 2.

**Category:** workflow

---

## Idea 2: Add moratorium-sprint Auto-Trigger to nightly-commit-review SKILL.md

**Evidence:** Run 25 governance mandate: "If not invoked by run 26: escalate to nightly-commit-review automatic trigger." 14 days zero production commits — nightly review fires every night and IS available. moratorium-sprint SKILL.md has trigger conditions compatible with auto-invocation. Nightly review already creates GH issues and commits files autonomously (7985fbb proof).

**Action:** Add `## Auto-Trigger Protocol` section to .claude/skills/nightly-commit-review/SKILL.md: when `moratorium_active=true` AND `days_without_production_commits > 7` AND `pending_s_effort_count > 0`, auto-invoke moratorium-sprint in the nightly run context.

**Impact:** Bypasses "human must be present" bottleneck. Nightly review runs every night — moratorium-sprint would fire autonomously within 24h. Handles future moratoriums without requiring human presence.

**Category:** workflow / operational

---

## Idea 3: dep-batch-merge — Clear 4 Safe Dependency PRs

**Evidence:** Skill discovery 2026-05-18 proposed dep-batch-merge. Morning digest 2026-05-18 flagged 4 immediately-safe PRs: #163 (`@typescript-eslint/parser` patch), #164 (`@playwright/test` minor), #102 (`youtube-transcript-api` patch), #103 (`python-multipart` patch). All aging 7–21 days. Patch + dev-dep-minor = safe by skill discovery classification.

**Action:** Merge all 4 via mcp__github__merge_pull_request. Independent of moratorium — no new code surface, no schema changes, no tenant impact.

**Impact:** 4 safe PRs cleared, merge-conflict risk eliminated, clean dep baseline before sprint PR. ~5 min. Does NOT affect pending approvals count (different queue from S-effort items).

**Category:** operational

---

## Idea 4: Create pre-commit-guard-add Skill

**Evidence:** Skill discovery 2026-05-18 proposed this as #2 skill (after moratorium-sprint). Pattern: every new bug class → new numbered check. Numbering and structure consistent but require reading the whole hook file each time. Check 10 has been pending 14 days across 9 improvement entries. Recurring cost: ~15 min per new guard (read hook, find insertion point, write check, test, update CLAUDE.md).

**Action:** Create .claude/skills/pre-commit-guard-add/SKILL.md with steps: read hook → find current Check N → write new check block → add opt-out pattern → test with trigger file → commit atomically.

**Impact:** Saves 15 min per new pre-commit guard. Recurring value: 1-2 new guards per month historically. Removes the "re-derive the format" friction that delays guard additions.

**Category:** workflow

---

## Idea 5: governance-state-sync Skill

**Evidence:** Skill discovery 2026-05-18 proposed governance-state-sync as #4 skill. governance.json has accumulated drift: run 24 required retroactive status correction (pending_approval → implemented). Manual verification takes ~5 min per subconscious run (grep each S-effort item, confirm presence/absence). Currently done ad-hoc at Phase 2 of each run.

**Action:** Create .claude/skills/governance-state-sync/SKILL.md: for each pending_approval item, grep codebase for prescribed file, verify presence, auto-update status. Recount pending_approvals. Check moratorium exit condition.

**Impact:** 5 min saved per subconscious run. Accurate state = better ideas. Prevents false "pending" items that were actually implemented (e.g., lead source analytics in run 9). Feeds cleaner evidence to run ideation phase.

**Category:** workflow
