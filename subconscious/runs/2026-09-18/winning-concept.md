# Winning Concept — Run 2026-09-18 (Run 122)

**Winner:** Step 9E 10-Day P0 Escalation Tier
**Category:** operational / workflow_efficiency
**Effort:** S (one block edit in SKILL.md Step 9E)
**Confidence:** HIGH
**Carry-forward count:** 3 (AUTONOMOUS-EXECUTABLE — implement this run)
**Autonomous-executable threshold:** 3 consecutive carries → run 122 fires

---

## Problem

Step 9E in `.claude/skills/nightly-commit-review/SKILL.md` monitors credential staleness and warns at >=76 days. It has NO escalation tier for imminent expiry (≤10 days). Current behavior:

- Checks `days_since_rotation` against `threshold_days` (76d)
- Adds comment to GH #399 when threshold crossed
- Does NOT detect or alert when expiry is days away

**Evidence of damage:**
- AUTOPILOT_GH_TOKEN: last rotated 2026-07-04 (76d as of 2026-09-18), expires 2026-10-02 (14 days away)
- Brain connector PAT: same rotation date, same expiry
- When these tokens expire, all CCR-based automation stops: nightly reviews, KB autopopulate triggers, subconscious loop commits — everything
- The 10-day tier would fire at 2026-09-22 (in 4 days). Without it: no P0 alert, owner may miss the deadline
- GH #399 has generic staleness comment from yesterday but no P0-labeled urgent issue

**Why governance mandates this now:**
- Run 119 (2026-09-11): identified 10-day tier gap
- Run 120 (2026-09-11-pm): 1st carry-forward, noted for autonomous-executable at run 122
- Run 121 (2026-09-17-pm): 2nd carry-forward
- Run 122 (2026-09-18): 3rd carry-forward = AUTONOMOUS-EXECUTABLE per governance protocol

---

## Implementation

Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block.

**Current Step 9E behavior (approximate):**
```python
# Checks days_since_rotation for each credential
# At >= 76d: warns, adds comment to GH #399
# At expiry date: no specific detection
```

**Add to Step 9E block — P0 escalation tier:**

After computing staleness days for each credential, also compute:
```python
# For each credential with a known next_due date:
days_remaining = (next_due_date - today).days

if days_remaining <= 10:
    # Search for existing P0 issue to dedup
    existing = mcp__github__search_issues(
        owner="aferna6-cell", repo="agentnexlify",
        query=f"{credential_name} expires P0 is:open"
    )
    if not existing.items:
        mcp__github__issue_write(
            owner="aferna6-cell", repo="agentnexlify",
            title=f"P0: {credential_name} expires in {days_remaining} days — rotate NOW",
            body=f"...",
            labels=["human-action-required", "ops", "P0"]
        )
        log(f"Step 9E: P0 issue filed for {credential_name} ({days_remaining}d remaining)")
    else:
        log(f"Step 9E: P0 issue already open for {credential_name} — no duplicate filed")
```

**Credential rotation schedule source:** `ops/credential-rotation-schedule.md`
- AUTOPILOT_GH_TOKEN: last_rotated 2026-07-04, interval 90d, next_due 2026-10-02
- Brain connector PAT: last_rotated 2026-07-04, interval 90d, next_due 2026-10-02
- SUPABASE_ACCESS_TOKEN: unknown state (file notes "unknown")

**Step 9E log format after fix:**
```
Step 9E: AUTOPILOT_GH_TOKEN — 76d since rotation, 14d remaining (threshold: 76d CROSSED, P0: 14d > 10d NOT YET)
Step 9E: Brain PAT — 76d since rotation, 14d remaining (threshold: 76d CROSSED, P0: 14d > 10d NOT YET)
Step 9E: SUPABASE_ACCESS_TOKEN — unknown state
```
At day 80 (4 days from now):
```
Step 9E: AUTOPILOT_GH_TOKEN — 80d since rotation, 10d remaining (P0 tier: issue filed #XXX)
```

---

## Verification After Implementation

```bash
grep 'days_remaining' .claude/skills/nightly-commit-review/SKILL.md
grep 'P0' .claude/skills/nightly-commit-review/SKILL.md
grep '<= 10' .claude/skills/nightly-commit-review/SKILL.md
```

All must return results in the Step 9E block.

Next nightly run: Step 9E should compute days_remaining for AUTOPILOT_GH_TOKEN (14d) and Brain PAT (14d) and NOT file a P0 issue (14 > 10). At run where days_remaining ≤ 10, the P0 issue fires.

---

## Run 123 Mandate

1. Verify 10-day tier present in Step 9E (grep check above)
2. Did Step 9E correctly compute days_remaining for AUTOPILOT_GH_TOKEN in the next nightly? Check nightly log.
3. Step 9G SKILL.md fix: 2nd carry-forward. Autonomous-executable at run 124.
4. AUTOPILOT_GH_TOKEN: rotated by owner before 2026-10-02?
5. os_tool_executions.py 783L: 6th consecutive mention — GH issue needs to be filed.
6. Bonus action: verify or file canonical GH issue for AI metering (45 violations Step 9L).
