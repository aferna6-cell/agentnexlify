# Idea 01 — Step 9G: KB Self-Healing Trigger (3rd Carry-Forward)

**Evidence:**
- `grep -c "Step 9G" .claude/skills/nightly-commit-review/SKILL.md` → 0. Step 9G ABSENT after 3 consecutive wins (runs 100, 101, 102).
- `knowledge-base/log.md` last entry: `## [2026-07-23]` — 11 days stale. Threshold: 7 days. Step 9F fires alert; nobody self-repairs.
- `run_102_mandate` item 1: "Step 9G in SKILL.md? (SHOULD PASS if PR merged)." → FAIL. PR #626 open but unmerged.
- `subconscious/runs/2026-07-23/winning-concept.md` + `subconscious/runs/2026-08-02-pm/winning-concept.md`: verbatim insertion block written twice. Same spec, not yet applied.
- Step 9F (lines 289-305 of SKILL.md): proven channel. Same pattern. All Steps 9B-9F shipped in ≤1 cycle each.
- KB stale 11 days and growing +1/day with no mechanism to self-heal.

**3-cycle escalation signal:** Every subconscious run since 2026-07-23 has chosen Step 9G. The PR is open. The spec is complete. The bottleneck is PR merge.

**Idea:** Add Step 9G block to `.claude/skills/nightly-commit-review/SKILL.md` immediately after Step 9F (after line 305):
```
9G. (KB Self-Healing Trigger) If Step 9F detected staleness (days_stale > 7):
    1. Check if workflow already running:
       `gh run list --workflow=kb-autopopulate.yml --status=in_progress --limit 1`
    2. If NOT running: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
       Log: "Step 9G: KB self-healing trigger fired — kb-autopopulate.yml dispatched"
    3. If already running: log "Step 9G: kb-autopopulate.yml already in_progress — skip"
```

**Escalation note:** Recommend human merge PR #626 this cycle. KB is now 11 days stale and every day of delay costs real KB coverage.

**Expected impact:** KB auto-repairs within 24h of implementation without manual intervention. Closes Step 9F gap permanently.

**Effort:** XS (one SKILL.md edit, ~10 lines)
**Confidence:** HIGH
**Autonomous:** YES (nightly commit review SKILL.md edit channel)
**Mandate:** run_102_mandate item 1 explicitly requires this check
