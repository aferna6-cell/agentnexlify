# Idea 4: Add Subconscious Phase 2 Verification Step for Prior Winner Status

**Evidence:** Morning digest 2026-07-07 (commit 6ef10ba) stated: "AUTONOMOUS-EXECUTED — issue-to-pr-loop should pick up #385 within 15 min." At the time of run 82 Phase 2, GH #385 labels remain `[nightly-review, backend, medium-risk, frontend]` — no `ai-ready`. The digest misstated execution status because: run 81 committed at `84e5b2b` AFTER today's nightly `460ea68` ran; the nightly had no chance to apply the label yet. The morning digest conflated "recommendation committed" with "recommendation executed." This produces false-positive confidence in the system's autonomous capabilities and could cause future runs to skip verification.

**Action:** Add a Phase 2 step to SKILL.md: "If previous run had `autonomous_executable: true` winner: check GH issue label via `mcp__github__issue_read` to verify ai-ready label is present. If NOT present: note as unverified-pending, do NOT assume executed." Also update morning-digest template to distinguish `status: pending_autonomous` from `status: executed`.

**Impact:** Prevents phantom-execution false positives. Gives future runs accurate state. Improves system's self-awareness of what has and hasn't shipped.

**Category:** agent_performance

**Confidence pre-debate:** MEDIUM — valid observation, but adds complexity to SKILL.md. May be over-engineering for an edge case that only matters when the nightly runs after the subconscious on the same day.
