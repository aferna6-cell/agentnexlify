# Debate Log — Run 118 (2026-09-08)

Top 3 by impact: Idea 1 (meter-ai-endpoint skill), Idea 2 (os_tool_executions split), Idea 3 (Step 9J fix).

---

## Idea 1: Create `meter-ai-endpoint` skill

### Challenge
1. **Is this redundant?** Step 9L now files GH issues for violations. Won't issue-to-pr-loop auto-fix them once GH #399 (AUTOPILOT_GH_TOKEN) is resolved?
2. **Frequency question.** 9 metering commits this week looks high, but this was a retroactive catch-up sprint (#792-#799 + PR #803). Once the backlog is cleared, new violations should be rare. Does a skill warrant recommendation for a one-time burst?
3. **Scope creep?** The ai-feature-pattern skill already exists. Is meter-ai-endpoint distinct enough?
4. **Effort allocation.** Skill creation takes 30-60 min. Each endpoint fix would take 10 min with the skill vs 30-60 min without. Break-even is 1-2 uses. Is that likely?

### Defense
1. **Issue-to-pr-loop is stalled.** GH #399 AUTOPILOT_GH_TOKEN expired — 30+ violations won't auto-fix even after Step 9L files issues. The skill is the path for manual or agent-driven fixes while the loop is down. With 30 violations and the loop stalled, each manual fix takes 30-60 min. The skill drops that to 10 min.
2. **Not a one-time burst.** Each new AI route starts unguarded. Every new Agent OS feature, every new analytics endpoint, every new diagnostic function — all unguarded at creation. The pattern repeats every sprint. Steps 9I (block_demo_role) and 9L (metering) both detect gaps in classes of problems that recur permanently. The skill is the remediation layer for what 9L detects.
3. **Distinct from ai-feature-pattern.** That skill covers prompt engineering for widget chat (persona, knowledge-base injection, fallback chains). meter-ai-endpoint covers the billing lifecycle (reserve_ai_tokens, call_claude_messages, record_ai_usage, release_ai_token_reservation) — completely different concern, different files, different test patterns.
4. **Break-even is already exceeded.** Skill discovery counted 9 metering commits this week × 20 min savings each = 3 hours that would have been saved had the skill existed. At current rate (1-2 new AI endpoints per sprint), break-even is 2 weeks.

### Verdict: SURVIVES. Strong evidence, explicit skill-discovery validation, immediate need with 30+ violations and stalled auto-fix loop.

---

## Idea 2: Split `os_tool_executions.py` god class (783L)

### Challenge
1. **Urgency?** The file hasn't changed in 5 days. Nothing is blocked on it. Rule 9 says "stop before adding more" — but nobody is adding more right now.
2. **Blast radius risk.** 783L with Agent OS features: splitting could touch import chains across the os_workflow modules. A bad split creates cascading ImportError.
3. **Wrong time?** Agent OS is experimental/evolving. Premature modularization of a volatile file creates more refactoring work than it saves.
4. **Lower ROI than Idea 1.** Idea 1 saves 10+ hours immediately. Idea 2 prevents future tech debt — harder to quantify.

### Defense
1. **Rule 9 is explicit**: >600L = stop and factor before adding. At 783L it's 30% over threshold. The longer we wait, the harder the split. Recommending now while it's stable is precisely the right timing.
2. **Recommendation only.** The subconscious recommends the split; implementation requires human-approved compound-engineering. A proper blast-radius analysis (gitnexus_impact) before starting prevents the cascading ImportError risk.
3. **Agent OS is growing.** The M9+ roadmap (shadow_planner, tool_catalog, planner_bakeoff) shows active growth. If the god class isn't split now, the next sprint will add 100+ more lines.
4. **Compound: each line harder.** At 900L this split costs double. At 1100L it becomes a multi-session refactor.

### Verdict: WEAKENED → parking lot. Good code health case but lower urgency than Idea 1. No immediate unblock. Revisit run 119 if Agent OS sprint adds lines.

---

## Idea 3: Fix Step 9J token budget (17/19 PRs skipped)

### Challenge
1. **Root cause unknown.** Can't write a specific action without knowing which step exhausts the token budget. The mandate note from run 117 said "read nightly session transcript to identify where 17-skip hits" — not done in 2 runs.
2. **Human is merging Dependabot manually.** Recent git log shows 5 Dependabot dep-bump merges in last 3 days (uvicorn, @vitejs/plugin-react, @playwright/test, jsdom, @testing-library/jest-dom). The gap isn't causing complete stagnation.
3. **Misdiagnosed scope?** The 17/19 skips may be a budget limit set intentionally to cap nightly token use. Raising the budget may push nightly into usage limits.
4. **Insufficient diagnostics to propose an action.** Without reading a nightly transcript, the recommendation would be "investigate Step 9J" — too vague to be actionable.

### Defense
1. **10% effective = failed system.** If Step 9J only processes 2/19 PRs, it provides false confidence. The human must still manually review and merge 17 PRs — the same job Step 9J was built to eliminate.
2. **Human bandwidth.** Even if the human is merging some, they're doing the work Step 9J was built to do. The token budget issue directly adds maintenance burden.
3. **The investigation is S-effort.** Reading one nightly log to identify the budget-exhaust point is 10-15 min.

### Verdict: KILLED this run. Cannot write a specific action without root cause. Add "diagnose Step 9J token budget exhaustion" to mandate for run 119 — not a winner without diagnostics.

---

## Synthesis

**Idea 1 SURVIVES → WINNER**: `meter-ai-endpoint` skill creation
**Idea 2 WEAKENED → parking lot**: os_tool_executions.py god class split (revisit run 119)
**Idea 3 KILLED → run 119 mandate investigation**: Step 9J root cause diagnosis required first
