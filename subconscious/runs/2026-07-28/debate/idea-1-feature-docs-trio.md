# Debate — Idea 1: `feature-docs-trio` SKILL.md

## FOR

**Evidence is undeniable.** 3 occurrences in 7 days (717c7f3, 14ebe8e, d50d1e8) — all from the skill-discovery report which had 28 commits to draw from. That's a 10.7% commit rate for this specific pattern in one week. The `feature-docs-trio` pattern was the #1 proposed skill in the discovery report.

**Execution path is proven.** Nightly SKILL.md can create new skill files — this is the same channel that created Step 9F and Step 9G. Creating a new `.claude/skills/feature-docs-trio/SKILL.md` is additive (no code changes, no schema changes, no migration).

**Compounds over future runs.** Every feature that ships without this skill costs 30-45 min of "which sections do I need?" overhead. At 2-3 features/week current velocity (feature-heavy sprint seen in the 28-commit window), that's 60-135 min/week of wasted work. The skill eliminates that waste permanently.

**Skill-discovery already did the design work.** The steps are documented verbatim in `docs/skill-discovery/2026-07-27.md` — this is copy-editing, not design. Execution effort: ~30 min to produce the SKILL.md.

**Supports `feature-docs-trio` → `feature-build` linkage.** Skill-discovery also recommended updating `feature-build/SKILL.md` to reference `feature-docs-trio` after a feature PR merges. This creates a documented pipeline: ship feature → run feature-docs-trio → KB + ADR + runbook committed.

## AGAINST

**Challenge 1: Why does a skill need a subconscious run to propose it?** The skill-discovery routine already proposed `feature-docs-trio`. The skill-discovery report is sitting in `docs/skill-discovery/2026-07-27.md`. The owner can read it and create the skill themselves. The subconscious adding a "create this skill" recommendation is noise — the signal is already there.

*Defense:* Skill-discovery proposes but doesn't implement. Past subconscious wins (Step 9F, Step 9G) show the value is in the execution commitment, not the proposal. The subconscious can commit the SKILL.md itself via the nightly channel. The owner reading a doc and acting is a probability <1. A committed skill file is fact.

**Challenge 2: SKILL.md files don't automatically get invoked.** Creating the skill doesn't guarantee it gets used. A skill sitting in `.claude/skills/feature-docs-trio/SKILL.md` still requires a developer to `/feature-docs-trio` or for the nightly to check for missing docs. If no invocation mechanism is wired, the skill is documentation, not automation.

*Defense:* This is true. But skills compound: the skill-creator skill requires that every new skill be "ruthlessly specific" about triggers. Writing the skill forces the trigger definition (e.g., "after any feature PR merges with no corresponding docs commit"). Future runs can add automation on top of the skill once it exists. Can't automate what isn't defined. The skill is the foundation.

**Challenge 3: Low urgency relative to operational risks.** Feature docs are nice to have. Silent failing tenants (Keys Koffee) and broken GH Actions are operational failures that may be actively losing money. The subconscious should prioritize customer value over process improvements.

*Defense:* This is the strongest objection. But: (a) the tenant heartbeat idea requires Supabase access in the nightly SKILL.md bash environment (not verified to work), (b) feature-docs-trio is zero-risk to implement, (c) the compounding benefit over 3-6 months exceeds a one-time operational fix.

## Verdict

STRONG candidate. Evidence score: 9/10. Execution risk: 1/10. Customer impact: 5/10 (indirect via KB quality). Process impact: 8/10.

**Weakness:** Not highest urgency relative to operational failures.
