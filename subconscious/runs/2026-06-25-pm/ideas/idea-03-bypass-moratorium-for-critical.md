# Idea 03 — Declare Widget + Em-Dash Fix as Critical (Bypass Moratorium)

**Category:** code_health
**Confidence:** LOW
**Autonomous-executable:** NO

## Proposal
Tag run 65 winner as `critical: true` in governance.json to bypass the
`moratorium_active: true` block, enabling immediate processing even while
pending_approvals >= max_pending_approvals.

## Why it seems attractive
- Moratorium currently blocks new non-critical recommendations
- Run 65 fix IS genuinely blocking (Check 13 exits 1, blocks all commits)
- A critical override path would unblock without requiring the cleanup sprint first

## Problems
1. The moratorium is already not blocking run 65 delivery — the blocker is nightly
   scope mismatch, not moratorium logic. Moratorium blocks NEW recommendations, not
   delivery of already-approved pending items.
   
2. Adding a `critical` bypass path to governance.json is governance debt — a new
   concept that needs to be supported in all future reads of governance.json.

3. The real blocker is Check 13 failing, which is itself caused by the run 65 fix
   not being delivered. Circular: can't deliver because scope, not because moratorium.

4. Moratorium will exit naturally once cleanup sprint runs (true_pending drops below 2).
   That's the designed path.

## Verdict: REJECTED
Does not address root cause. Idea 01 is direct and sufficient.
