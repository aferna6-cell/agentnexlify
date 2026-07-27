# Run 106 Ideas — 2026-07-27-pm

**Evidence window:** 2026-07-23 → 2026-07-27 (4-day quiet period, no human commits)
**Mandate checks:**
1. PR #577 merged? → NO (open draft, 4 days)
2. Step 9H fired on nightly-2026-07-27? → NO (PR not merged, Step 9H not on main)
3. GH #500 resolved? → NO (Day 7, all Actions dark)
4. Managed Agents Phase 0 GH issue filed? → UNKNOWN (run 103 winner pending human approval)
5. KB freshness (knowledge-base/log.md) → PASS (2026-07-23, 4 days, within 7-day threshold)
6. GH #399 AUTOPILOT_GH_TOKEN rotated? → NO (still expired)

---

## Idea 1: Fix god-class-splitter SKILL.md Step 7 — Backward-Compat Re-Exports

**Category:** workflow
**Effort:** XS
**Confidence:** HIGH

**Evidence:**
- `docs/skill-discovery/2026-07-27.md` marks this HIGH priority with exact quote: "Both omissions cause test failures immediately after the split."
- Two god-class splits this week: `calls.py` (1196L → 237/875/133) and `email_sequences.py` (1143L → 529/328/341)
- Both missing: (a) backward-compat re-exports in original file, (b) @patch target update — both required follow-up commits
- Current Step 7: "No re-export shims (`from new_module import *`). No `# removed` comments." — this guidance actively PREVENTED engineers from following best practice
- Step 10.5 covers @patch repair but is reactive (after tests fail). The gap is Step 7 contradiction.

**Proposed fix:**
- Change Step 7 to permit and guide named re-exports: `from .new_module import Symbol1, Symbol2`
- Add inline note: re-exports don't fix `@patch` targets — Step 10.5 still required
- Remove blanket "No re-export shims" since both recent splits needed them

**Autonomous path:** Direct SKILL.md edit (same class as runs 99/102/104 which edited nightly-commit-review SKILL.md directly). Nightly channel cannot pick up edits to other SKILL.md files — must implement directly.

---

## Idea 2: Create feature-docs-trio Skill File

**Category:** workflow
**Effort:** S
**Confidence:** HIGH

**Evidence:**
- `docs/skill-discovery/2026-07-27.md`: 3 occurrences in 7 days (commits 717c7f3, 14ebe8e, d50d1e8)
- Pattern: KB wiki article + ADR entry + INDEX.md update + optional runbook, each within 2 days of feature PR merging
- Estimated 30-45 min saved per feature shipped

**Weakness:** Invoke gap — skill-discovery explicitly notes feature-build SKILL.md doesn't reference it yet. A skill nobody discovers saves nothing. Recommend updating feature-build SKILL.md first (lower-effort seed).

**Decision:** WEAKENED → promote in run 107 after feature-build SKILL.md seed lands.

---

## Idea 3: Add documentation step to feature-build SKILL.md

**Category:** workflow
**Effort:** XS
**Confidence:** HIGH

**Evidence:**
- Skill-discovery recommends: "Add to feature-build/SKILL.md a 'Documentation step' pointing to the feature-docs-trio skill"
- feature-build SKILL.md currently has no post-merge documentation step
- The seed ensures engineers discover feature-docs-trio when they run feature-build

**Weakness:** feature-docs-trio skill doesn't exist yet — pointing to it is premature. Bootstrapping order: (a) create skill, (b) reference from feature-build. Referencing before creation means broken link.

**Decision:** WEAKENED → depends on Idea 2 landing first. Park until feature-docs-trio created.

---

## Idea 4: Add Step 9I — VOYAGE_API_KEY Rotation Schedule Entry to nightly

**Category:** operational
**Effort:** XS
**Confidence:** MEDIUM

**Evidence:**
- Run 104 parking lot: "Step 9I: VOYAGE_API_KEY rotation schedule entry"
- VOYAGE_API_KEY is required for KB embeddings; currently absent (KB catch-up on 2026-07-23 skipped embeddings)
- ops/credential-rotation-schedule.md exists (Step 9E, run 84)
- Adding VOYAGE_API_KEY expiry tracking prevents future embedding gap

**Weakness:** VOYAGE_API_KEY rotation schedule is documentation-only (add a row to credential-rotation-schedule.md). No urgency signal — embeddings currently absent but FTS fallback works. Low ROI vs Idea 1's immediate test-failure prevention.

**Decision:** WEAKENED → parking lot. Defer until VOYAGE_API_KEY actually set in prod.

---

## Idea 5: GH Issue for email_sequences Authentication Failures

**Category:** code_health
**Effort:** XS
**Confidence:** MEDIUM

**Evidence:**
- Run 104 parking lot: "email_sequences 8 auth failures GH issue (defer until CI returns)"
- email_sequences.py god-class split (2026-07-23) produced auth failure edge cases visible in logs
- Filing GH issue with ai-ready label queues it for issue-to-pr-loop once GH #399 resolved

**Weakness:** GH #500 (Actions spending limit) still active — issue-to-pr-loop cannot execute. Filing now queues it but implementation is blocked. Defer until GH #399 resolved.

**Decision:** WEAKENED → parking lot. Resurface when GH #500 fixed.

---

## Selection

| Idea | Verdict |
|------|---------|
| 1. god-class-splitter Step 7 fix | **WINNER** — XS, HIGH evidence, direct test failure prevention, autonomous |
| 2. feature-docs-trio skill create | WEAKENED — invoke gap blocks ROI; needs feature-build seed first |
| 3. feature-build docs step seed | WEAKENED — depends on Idea 2 existing first |
| 4. Step 9I VOYAGE_API_KEY | WEAKENED — low urgency, no prod usage yet |
| 5. email_sequences auth failures GH issue | WEAKENED — blocked by GH #500 |
