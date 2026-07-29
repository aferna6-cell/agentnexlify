# Ideas — 2026-07-29-pm (Run 104)

Generated 5 candidate improvements from evidence gathered this run.

---

## Idea 1: feature-docs-trio SKILL.md — direct implementation (CARRY-FORWARD MANDATE)

**Category:** workflow
**Effort:** XS (~50 lines, SKILL.md only, no code changes)
**Evidence:**
- Run 103 explicitly mandated: "feature-docs-trio 2nd carry-forward: direct implementation fires at run 104"
- Pattern occurred 3× in 7 days: 717c7f3 (photo-quote), 14ebe8e (drive-kb), d50d1e8 (zapier integration)
- Skill-discovery-2026-07-27 documented full 6-step design with exact file structure
- feature-docs-trio/ directory does NOT exist on branch (confirmed 404)
- Same channel (SKILL.md creation) proven across all prior subconscious run implementations

**Action:** Create `.claude/skills/feature-docs-trio/SKILL.md` encoding 6-step post-feature documentation pattern (KB wiki article + ADR + INDEX update + optional runbook). Update `feature-build/SKILL.md` to reference it. Commit as `[skip ci]`.

**Impact:** 30–45 min/feature-launch saved × 2–3 features/week = 60–135 min/week. Also feeds KB quality directly (documented features → more accurate wiki → better widget AI responses for tenants).

---

## Idea 2: Autonomy sweeper nightly health report (Step 9I candidate)

**Category:** operational
**Effort:** XS (~15 bash lines in nightly-commit-review SKILL.md)
**Evidence:**
- Sweeper shipped (8e78f5b, 2026-07-29) — `run_loop sweep --dry-run` works
- Sweeper value is latent: no nightly invocation means stranded runs accumulate undetected until manual check
- Step 9G (CCR health) now in SKILL.md — Step 9I would be the next logical operational step
- 422 tests pass, sweeper design is sound (TOCTOU guard, re-enterability classification)

**Action:** Add Step 9I bash block to nightly SKILL.md: `python3 scripts/autonomy/run_loop.py sweep --dry-run` → parse stranded count → if > 0 → comment on GH #403 with count and run IDs.

**Impact:** Automates sweeper monitoring; prevents stranded runs from silently blocking autonomy loop progress.

---

## Idea 3: Silent-green tenant heartbeat (Step 9H candidate)

**Category:** operational
**Effort:** S (~40 bash lines including Supabase query)
**Evidence:**
- `docs/dev-knowledge/bug-patterns.md`: Keys Koffee widget missing 5+ weeks undetected — "silent-green tenant" class of failure
- Nightly sweeper catches stranded runs; no nightly check catches silent paying tenants
- 3 live tenants; any one going silent is revenue risk and churn indicator
- Carry-forward from runs 101/102/103 backlog items: "MEDIUM — prevents Keys Koffee-class silent churn"

**Action:** Add Step 9H bash block: Supabase query for paid tenants with 0 conversations in past 7 days → if any found → comment on GH #403 with tenant list and last-conversation date.

**Impact:** Prevents tenant churn from going undetected. Keys Koffee class of failure: 5+ weeks of missed value delivery.

---

## Idea 4: round-iteration-loop SKILL.md

**Category:** workflow
**Effort:** XS (~40 lines, SKILL.md only)
**Evidence:**
- Run 101 backlog: "round-iteration-loop SKILL.md (LOW) — 3 occurrences in 7 days"
- Agent OS refinement rounds (Steps 9A-9I) exemplify the pattern: evidence-gather → propose → debate → implement → verify
- Pattern now well-established with graph runtime + sweeper shipping
- Natural next skill to encode after feature-docs-trio

**Action:** Create `.claude/skills/round-iteration-loop/SKILL.md` — encodes the evidence → propose → debate → implement → verify pattern for Agent OS-style iterative improvement.

**Impact:** Reusable template for autonomous refinement cycles; reduces cold-start time for new improvement loops.

---

## Idea 5: Feature-docs-trio trigger in nightly commit review

**Category:** operational
**Effort:** XS (~10 bash lines in nightly SKILL.md)
**Evidence:**
- Once feature-docs-trio SKILL.md exists (this run), nightly should actively surface features that ship without docs follow-up
- pattern: `git log --since="48 hours ago"` for PR merges tagged feat/feature → check if corresponding KB article exists
- Would close the docs feedback loop automatically

**Action:** Add Step to nightly SKILL.md: detect recently merged feature PRs with no docs follow-up commit → log "Docs reminder: feature X merged, run feature-docs-trio"

**Impact:** Passive reminder ensures feature-docs-trio actually gets used for each feature.
