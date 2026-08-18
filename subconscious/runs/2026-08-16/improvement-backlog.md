# Run 105 — Improvement Backlog (2026-08-16)

## This Run's Winner (IMPLEMENTED)
- **route-security-guard-audit SKILL.md** — 3rd-cycle escalation. `.claude/skills/route-security-guard-audit/SKILL.md` written directly.

## Parking Lot (carry-forwards for future runs)

### Step 9I: nightly grep scan for missing block_demo_role
- **Status:** WEAKENED in debate, parking lot
- **Rationale:** Route-security-guard-audit SKILL.md must be written first (Idea 1 = this run's winner). Step 9I is the companion — proactive nightly detection after the skill proves useful. Idempotency guard required (no duplicate GH issues). Autopilot stalled (#399) reduces urgency.
- **Promote when:** route-security-guard-audit SKILL.md used once in practice + autopilot-issue-loop resumes + idempotency design complete.
- **ROI:** 2.1

### scoring_config.py block_demo_role fix
- **Status:** GH #661 filed (nightly 2026-08-16). Human-review gate. Not a subconscious implementation task.
- **Rationale:** Security code change. Requires human or issue-to-pr-loop (when #399 clears).
- **Action:** Issue exists. Promote to autopilot queue when #399 resolved.
- **ROI:** 2.5 (security priority)

### Step 9H v2: idempotent PR pile alerter
- **Status:** Parking lot since run 101. Design issue (would fire every nightly indefinitely).
- **Rationale:** Needs idempotency: check for existing open GH issue before creating new one. Same design required for Step 9I.
- **Promote when:** Design for idempotent issue creation is ready.
- **ROI:** 1.8

### Brain connector GH #394 comment with recovery steps
- **Status:** Debated and weakened (4th autonomous comment = diminishing returns).
- **Rationale:** Step 9E + ops/credential-rotation-schedule.md already provide the checklist. Human needs to check Supabase dashboard themselves. Cannot be automated further.
- **Promote when:** If SUPABASE_ACCESS_TOKEN confirmed as rotated but brain connector still failing.
- **ROI:** 1.3

### LoopHealthPage.jsx promotion
- **Status:** Parking lot since run 100. Condition: Agent OS >5 active tenants.
- **Current:** 2-3 tenants (below threshold).
- **ROI:** 1.7

### MCP Step 9H monitoring (idempotent version)
- **Status:** KILLED run 100 for premature observability. Revisit condition: >5 MCP tenants.
- **Current:** 1 MCP tenant (below threshold).
- **ROI:** 1.5

## Blocked Items (human-required)

| Issue | Blocker | Age | Impact |
|-------|---------|-----|--------|
| GH #394 (brain connector) | GitHub PAT + SUPABASE_ACCESS_TOKEN rotation | 23+ days | Step 9C age gate firing daily |
| GH #399 (AUTOPILOT_GH_TOKEN) | Token expired | 37+ days | Autopilot stalled, 40+ ai-ready issues queued |
| GH #403 (KB autopopulate) | ANTHROPIC_API_KEY missing in GH Actions | 37+ days | KB 24 days stale, Step 9G triggering but blocked |
| GH #643 (appointment_briefs) | PR #653 needs human review + merge | 9+ days | Demo tenant security gap |
| GH #661 (scoring_config) | Needs human or autopilot fix | 0 days | Demo tenant security gap (new) |
| Orphaned commits | Human needs `git branch recover-orphans 00940d9` to preserve, or merge PR #653 | 3+ days | 6 commits unreachable from origin |
