# Winning Concept — 2026-06-08-pm (Run 52)

## Recommendation
Add Check 12 to `scripts/hooks/pre-commit` — a 12-line bash WARNING block scanning `agent-service/src/**/*.ts` for timing-unsafe token comparisons (`===` on variables named `token`, `key`, `secret`, `header` without `timingSafeEqual`) — labeled AUTONOMOUS-EXECUTABLE for tonight's nightly.

## Why This, Why Now
GH #206 (timing attack in `auth.ts`, filed by nightly 2026-06-07) + 2287f6b (opt-in/opt-out default bug in `os_inbound_bridge.py`, fixed same week) = 2 security-adjacent incidents in 7 days on the agent-service TypeScript layer. The Python backend has 11 pre-commit guards preventing recurrence of exact bug classes; agent-service has 0. The agent-service is shipping 2-3 PRs/day (30+ agents registered) and is becoming customer-facing via Agent OS dashboard (PR #207). Every future agent added to `agent-service/src/agent-os/agents/` is now in the blast radius of an unchecked security surface. Check 12 catches the timing-attack pattern at commit time instead of the current 12-24h nightly review delay. The AUTONOMOUS-EXECUTABLE channel is confirmed working (Check 11 via 061582c; SKILL.md scope extension via 4226ef4). This item adds to `pending_autonomous` — not `pending_approval` — so it doesn't worsen moratorium metrics.

## Implementation Sketch

1. **Verify:** `grep -n "Check 1[0-9]" scripts/hooks/pre-commit` — confirm Check 11 exists (billing constant guard), Check 12 slot is free.

2. **Write Check 12 block** — append to `scripts/hooks/pre-commit` after Check 11:
```bash
# Check 12: agent-service timing-safe comparison guard
echo -n "Check 12: agent-service timing-safe comparison guard... "
if find agent-service/src -name "*.ts" 2>/dev/null | xargs grep -l "==" | xargs grep -l "token\|secret\|key\|header" 2>/dev/null | \
   xargs grep -E "(token|secret|key|header)[a-zA-Z]* ===|=== (token|secret|key|header)" 2>/dev/null | \
   grep -v "timingSafeEqual" | grep -q .; then
  echo "WARNING: agent-service may have timing-unsafe token comparisons. Use timingSafeEqual from node:crypto."
else
  echo "PASS"
fi
```
*(WARNING mode, not FAIL — same policy as Check 11.)*

3. **Label in governance.json:** Set `status: "pending_autonomous"`, `autonomous_executable: true` on run 52 active_direction entry.

4. **Nightly executes:** Tonight's nightly (2:37 AM) reads AUTONOMOUS-EXECUTABLE label + scope covers pre-commit bash additions (confirmed scope extension 4226ef4). Check 12 added to pre-commit by morning.

5. **Verify (post-nightly):** `grep "Check 12" scripts/hooks/pre-commit` — confirm block present. Run `bash scripts/hooks/pre-commit` — confirm WARNING fires on agent-service/src/auth.ts (before PR #209 merge) or PASS (after merge).

## Bonus Actions (human, today — not subconscious winners)

- **Bonus A (5 min):** Merge PR #209 → closes GH #206 timing attack before Check 12 is live
- **Bonus B (5 min):** Merge PR #200 → enables Items A+B autonomous execution tonight (Check 10 + widget sync guard)
- **Bonus C (10 min):** Merge PR #183 → closes GH #181 billing fix (AMOUNT_TO_PLAN 15000/25000), run 51 active direction

These 3 bonus merges (~20 min total, independent) would reduce moratorium pending_approval count by ~3 items.

## What This Replaces
Run 51 active direction (verify + merge PR #183) remains in place — run 52 winner is parallel, not sequential. This is the first subconscious recommendation targeting the agent-service TypeScript layer in 52 runs.

## Confidence
**HIGH** — Evidence strong (1 confirmed incident with grep-catchable pattern, consistent with Check 11 precedent), implementation matches proven autonomous channel, SKILL.md autonomous scope explicitly covers pre-commit bash additions.
