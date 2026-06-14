# Debate Log — Run 2026-06-08-pm (Run 52)

Top 3 by impact: Idea 3 (systemic + autonomous), Idea 2 (security HIGH), Idea 1 (moratorium exit)

---

## Idea 3: Add Check 12 — agent-service timing-safe guard to pre-commit

### Round 1

**Challenge:** Is 2 incidents enough evidence for a new pre-commit check? One was a default config bug (2287f6b — widget_enabled default), not strictly a grep-catchable pattern. The other (PR #209) is the first true timing attack. One clear security pattern = weak precedent.

**Defend:** Check precedent:
- Check 9 (JS silent catch): added after 3 occurrences in 14 days (runs 3/9/11)
- Check 11 (billing constant guard): added after 1 direct incident (c72b535 billing fix) + GH #181 pattern analysis

One incident with a **clear grep pattern** (look for `=== req.headers` or variable named `token`/`key` compared with `===` outside timingSafeEqual context) is sufficient, consistent with the Check 11 precedent. The 2287f6b widget bug is additional evidence of insecure defaults in agent-service as a general codebase hygiene signal.

**Verdict: SURVIVES Round 1.**

---

### Round 2

**Challenge:** Does the pre-commit hook actually run over agent-service/ files? The pre-commit hook focuses on backend/**.py and frontend/**.{jsx,js}. If agent-service commits are separate or agent-service devs bypass the hook, the guard is useless.

**Defend:** Pre-commit hooks run on ALL staged files across the entire repo. The hook already scans `widget/` JS files (Check 9 guards JS catch patterns). Adding a grep scan over `agent-service/src/**/*.ts` is the same mechanism — bash glob on staged/all files. Evidence: `scripts/hooks/pre-commit` currently has 12 checks including file-type-scoped scans.

Furthermore, 3 of the last 5 agent-service commits (#204, #205, #208) were by `aferna6-cell` (human) running through the standard commit flow. The hook would have caught a === comparison.

**Verdict: SURVIVES Round 2.**

---

### Round 3

**Challenge:** Is this higher leverage than Idea 1 (PR #200 merge)? PR #200 merge triggers 2 autonomous executions tonight (Items A+B). Check 12 adds 1 new item to the autonomous queue. Net delta: PR #200 = -2 items, Check 12 = +0 items (autonomous). The moratorium is at 15 pending. Shouldn't moratorium exit be the priority?

**Defend:**
1. PR #200 merge was Bonus A in run 51. Morning digest lists it as #2 priority. If it hasn't been merged in 3 days despite both signals, recommending it as run 52 winner is the 4th repetition of a mechanism that isn't working. This is exactly the pattern the moratorium protocol was designed to catch.
2. Check 12 is AUTONOMOUS-EXECUTABLE → it doesn't add to pending_approval count. The moratorium is about pending_approval items (human-required). An autonomous item is in a parallel channel that self-executes.
3. Compound value: every future agent-service commit benefits from Check 12. There are 30+ agents and the codebase is shipping 2-3 PRs/day. The guard compounds immediately.

**Verdict: SURVIVES Round 3 → WINNER.**

---

## Idea 2: Merge PR #209 (timingSafeEqual security HIGH)

### Round 1

**Challenge:** The morning digest already surfaces PR #209 as #1 priority with explicit merge command. If the human reads the morning digest, this is handled without the subconscious. What does the subconscious add by recommending the same thing?

**Defend:** The subconscious compounds: PR #209 is the fix; Check 12 is the prevention. If we recommend PR #209 as winner, we're recommending a one-time fix with no systemic lever. Idea 3 (Check 12) SUBSUMES the PR #209 message: "the nightly review caught this; now let's catch it at commit time."

**Verdict: WEAKENED Round 1.** The PR merge is tactical; Idea 3 is systemic.

### Round 2

**Challenge:** Security HIGH is the highest priority class. Should a pre-commit guard (preventive, future-facing) ever beat closing an active HIGH vulnerability?

**Defend:** PR #209 has a PR already open, morning digest flagging it, and moratorium doesn't block it. It requires 5 minutes of human attention and the path is clear. The subconscious should surface what ISN'T already covered by existing systems. PR #209 merge is handled; Check 12 is not.

**Verdict: WEAKENED → Parking Lot. Merge PR #209 is a Bonus Action (5 min, human, today).**

---

## Idea 1: Merge PR #200 (unblock Items A+B)

### Round 1

**Challenge:** This was Bonus A in run 51 (2026-06-05-pm). It's also #2 priority in morning-digest-2026-06-08.md. It hasn't been merged in 3 days. Recommending it again as run 52 winner would be the 3rd signal with the same message. Prior pattern: 4+ repeated recommendations → mechanism is broken.

**Defend:** PR #200 is genuinely the highest-ROI human action available (5 min merge → 2 autonomous executions tonight). The morning digest framing may not be emphatic enough. Making it the subconscious winner raises its urgency above tactical noise.

**Verdict: WEAKENED Round 1.** 3 days + 3 signals = mechanism not working. Choose Bonus Action path, not winner path.

### Round 2

**Challenge:** Is there an AUTONOMOUS PATH to merge PR #200? If the human isn't merging it, can nightly review auto-close it?

**Defend:** No. PR merges require human action (or explicit auto-merge configured). The nightly review can create issues and modify SKILL.md files, but cannot merge PRs. The autonomous path is blocked.

**Verdict: WEAKENED → Parking Lot / Bonus Action (5 min, highest-priority human action for moratorium exit).**

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 3: Check 12 agent-service guard | **SURVIVES 3 rounds → WINNER** | Active direction run 52 |
| Idea 2: Merge PR #209 (timingSafeEqual) | **WEAKENED** | Bonus Action A (5 min, today) |
| Idea 1: Merge PR #200 | **WEAKENED** | Bonus Action B (5 min, unblocks chain) |
| Idea 4: Agent OS booking eval harness | Not debated | Parking lot (moratorium active, M-effort) |
| Idea 5: KB VOYAGE_API_KEY fix | Not debated | Parking lot (operational, 34d stale) |
