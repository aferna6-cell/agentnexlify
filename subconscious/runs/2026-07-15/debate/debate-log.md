# Debate Log — Run 94 (2026-07-15)

Top 3 by impact: Idea 1 (widget_guard fix), Idea 4 (Step 9F), Idea 3 (attribution GH issue).

---

## Idea 1: Fix widget_guard._SESSION_TURN_COUNTS unbounded dict

### Challenge
1. Nightly said "not an immediate problem" — over weeks, not days. Is this urgent enough to be the run 94 winner?
2. Adding `cachetools` as a new dependency for a 3-line fix could introduce supply chain surface for minimal gain.
3. Would a TTL eviction cause unexpected behavior? A session mid-conversation after 1hr inactivity would lose its turn count and reset to 0 — is that correct?
4. Is there a simpler eviction approach that avoids any new dep?

### Defend
1. "Not immediate" is exactly when to fix: PR #431 is 1 day old, the code is fresh in context, and fixing now costs far less than re-reading + fixing in 3 weeks when the problem surfaces in a production incident. Timing is optimal.
2. `cachetools` is already a well-established PyPI package used by many FastAPI projects. But it's not required — a hand-rolled approach with `_SESSION_LAST_SEEN: dict[str, float]` + eviction in `check_turn_budget()` avoids any new dep entirely. 5 extra lines, zero new packages.
3. Turn-count reset on TTL expiry is the correct behavior: a session returning after 1hr of inactivity should start a fresh turn window. The guard is rate-limiting per-burst, not per-lifetime. Even if the TTL triggers mid-conversation, the user simply gets their turn count reset to 0 — the conservative outcome is they get MORE turns, not fewer.
4. A maxsize cap (e.g., `maxsize=10_000`) with LRU eviction is the cleanest alternative: no TTL, no time dependency, just bounded by count. An OrderedDict with a 10k cap is 10 lines and no dep.

### Verdict: SURVIVES (STRONG)
Direct evidence from nightly. Fix is small, timing is optimal, behavioral risk is minimal (conservative direction), no new dep required. Autonomous-executable via nightly code-change channel.

---

## Idea 4: Add Step 9F to nightly-commit-review SKILL.md

### Challenge
1. Steps 9A-9E are already in SKILL.md — is there room for another without the file exceeding readability limits?
2. GH #399 and #403 have already been escalated via comments from both nightly review AND subconscious runs. Does adding Step 9F produce a materially different outcome, or just more noise on already-noisy issues?
3. The subconscious runs twice daily and already tracks these issues in its mandate check. Step 9F would duplicate that with nightly checks — is this additive or redundant?
4. What's the escape condition? If Step 9F keeps escalating forever and the human never acts, is it self-defeating?

### Defend
1. `.claude/skills/nightly-commit-review/SKILL.md` currently has Steps 9A-9E at lines 265-288. Step 9F would add ~20 lines — well within the file's current scope.
2. The issue isn't noise volume — it's timing. Current pattern: subconscious detects staleness at Day 11+. Step 9F would catch it at Day 7, potentially before the compound cost of 40 blocked issues accumulates. Earlier signal = earlier resolution.
3. The subconscious mandate check is strategic (runs per subconscious cycle). Step 9F would be operational (runs every night, posts a daily count). Different cadence, different signal. Not redundant.
4. Step 9F should include a staleness-escalation cap: post daily at Day 7-14, then weekly after Day 14. This prevents pure noise while maintaining signal. The cap is in the SKILL.md spec.

### Verdict: SURVIVES (MODERATE)
Valid addition to nightly operational monitoring. But lower leverage than Idea 1 — it's a workflow improvement, not a code fix. Also: GH #399/#403 are already well-known to the human (multiple escalations). Step 9F would add marginal value over existing escalation pattern. Parking lot candidate.

---

## Idea 3: File GH issue for attribution dashboard frontend gap

### Challenge
1. GH #403 (ANTHROPIC_API_KEY) still blocks issue-to-pr-loop. Filing a new issue now adds to a queue that can't be executed — backlog noise until the blocker resolves.
2. Is attribution.py actually what "Lead source analytics" in customer-gaps.md refers to? customer-gaps.md pre-dates PR #431. The connection between the two may be assumed, not confirmed.
3. PR #431 was shipped yesterday — should the human review the new services first before queuing frontend work for them? Rushing to frontend before backend is battle-tested is premature.
4. How confident are we that `/api/attribution/summary` exists? attribution.py was read by nightly review but not the router.

### Defend
1. Filing now means when GH #403 resolves, the queue already has a complete, well-described issue. The cost of filing is 5 minutes; the cost of rediscovering this gap after GH #403 resolves is 30+ minutes.
2. Attribution.py adds lead_source tracking per lead. customer-gaps.md's "Lead source analytics" is definitionally this: which sources (widget, form, API) produce leads. The connection is strong, not speculative.
3. Valid concern — but the issue can specify "backend must be stable 1 week before frontend PR" as a dependency note. This doesn't block filing.
4. This is a genuine uncertainty. The attribution router may not expose a summary endpoint yet. The GH issue should specify what API endpoint is needed (not assumed to exist) — making this a feature request, not a connect-the-dots task.

### Verdict: WEAKENED
Valid future work. The uncertainty about the attribution router endpoint weakens confidence. Also lower urgency than Idea 1 (code health) since the issue-to-pr-loop is blocked anyway. Parking lot.

---

## Ranking

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 1: widget_guard unbounded dict | SURVIVES (STRONG) | → WINNER |
| Idea 4: Step 9F nightly infra check | SURVIVES (MODERATE) | → Parking lot |
| Idea 3: attribution dashboard GH issue | WEAKENED | → Parking lot |
| Idea 2: BotHealthPage.jsx | Not debated (lower priority than top 3) | → Parking lot |
| Idea 5: manual KB refresh script | Not debated | → Parking lot |

## Winner: Idea 1 — Fix widget_guard._SESSION_TURN_COUNTS unbounded dict
