# Run 102 — Improvement Backlog

**Date:** 2026-08-11

---

## Active (approved, awaiting or in implementation)

| ID | Description | Channel | Status |
|----|-------------|---------|--------|
| step-9f | KB staleness alert in nightly-commit-review SKILL.md | SKILL.md edit | DONE (run 97) |
| step-9g-v1 | KB autopopulate self-healing trigger — gh CLI version | SKILL.md edit | DONE but broken (run 101) |
| step-9g-v2 | **THIS RUN — Amend Step 9G to use MCP trigger (primary path)** | SKILL.md edit | PENDING APPROVAL |
| detached-head-guard | Guardrail #8 + step 1.5 in nightly SKILL.md | SKILL.md edit | DONE (nightly 2026-08-11) |

---

## Parking Lot (SURVIVED debate, not selected this run)

### 1. `pr-backlog-triage` skill
**Category:** workflow
**Evidence:** 10 open PRs, 3 Dependabot PRs open 7 days, morning digest flagged for 2+ consecutive days
**Action:** Create `.claude/skills/pr-backlog-triage/SKILL.md` per spec in `docs/skill-discovery/2026-08-10.md`
**Blocked by:** Nothing — ready to implement
**Why deferred:** Correct idea, secondary priority vs Step 9G MCP fix which is higher urgency (KB 19 days stale)
**Propose again:** Run 103 if still pending; strong evidence, clear spec already written

### 2. `route-security-guard-audit` skill
**Category:** code_health
**Evidence:** block_demo_role guard applied twice in 48h (cbbaae5/c204af2), GH #643 still open
**Action:** Create `.claude/skills/route-security-guard-audit/SKILL.md` per 6-step spec in `docs/skill-discovery/2026-08-10.md`
**Blocked by:** AUTOPILOT_GH_TOKEN expiry (blocks issue-to-pr-loop that would use this skill)
**Why deferred:** Evidence weakened after guardrail #8 fixed the root cause (detached HEAD); motivating case (#643) blocked by token expiry
**Propose again:** Run 103 or 104 after AUTOPILOT_GH_TOKEN rotated and loop is healthy

---

## Rejected this run

| Idea | Verdict | Reason |
|------|---------|--------|
| Fix appointment_briefs.py directly | KILLED | Subconscious mandate = recommend only; direct implementation breaks channel boundary; wrong tool for this loop |
| Step 9H: Dependabot auto-merge in nightly SKILL.md | KILLED | Overlaps with `pr-backlog-triage` skill (Idea 1); better implemented once in skill, not as parallel automation |

---

## Frozen (never propose)

- `ai_human_handoff` — frozen per `governance.json`. Do not propose.

---

## Open Questions

1. **Did kb-autopopulate.yml workflow actually run after Step 9G MCP trigger on 2026-08-11 nightly?** Check GitHub Actions run history for `kb-autopopulate.yml` — was there a run at ~02:37 UTC on 2026-08-11? What was the outcome?

2. **Are kb-autopopulate.yml secrets current?** Workflow requires ANTHROPIC_API_KEY, VOYAGE_API_KEY, SUPABASE_ACCESS_TOKEN. These may have expired if not rotated. AUTOPILOT_GH_TOKEN expiry suggests a broader secret rotation may be needed.

3. **PR #626 status:** Contains Step 9G (gh CLI version). Once Step 9G v2 (MCP fix) is ready, should PR #626 be updated to contain the amended version, or opened as a separate PR?

4. **`mcp__github__actions_list` tool availability in nightly sessions:** Confirmed in deferred tools for this session. Is it available in the scheduled nightly session context? Same MCP server should be active.
