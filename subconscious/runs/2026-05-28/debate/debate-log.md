# Debate Log — Run 37 (2026-05-28)

Top 3 ideas debated: Idea 2 (billing-constant-guard), Idea 1 (post-split-test-repair SKILL.md), Idea 3 (Agent OS delivery monitoring).

---

## Idea 2: Billing-constant-guard pre-commit Check 11 (WARNING mode)

### Round 1

**Challenge:** The parking-lot note explicitly says "Execute AFTER GH #181 fix." Adding Check 11 while the gap exists creates WARNING noise on every commit before the fix is applied. Devs who see a persistent WARNING they can't clear will start ignoring pre-commit output. That undermines the entire pre-commit system.

**Defend:** The "Execute AFTER GH #181 fix" note applies to FAIL mode — a FAIL that blocks commits before the fix would be a self-inflicted CI blocker. WARNING mode has no such dependency. Pre-commit already has one WARNING (Check 5, migration duplicate numbers) — the pattern is established and hasn't caused warning fatigue. The pre-commit output clearly labels each check, so the WARNING is visible alongside its label and fix hint. A developer who sees "Check 11 WARNING: AMOUNT_TO_PLAN missing 15000, 25000" will either (a) know what it means and act or (b) leave it for the person who owns billing. Neither outcome is "ignore everything."

### Round 2

**Challenge:** GH #181 has been stale for 26 days. Five explicit subconscious winner recommendations didn't move it. A WARNING in pre-commit is yet another signal pointing at the same gap. Why would the 6th mechanism be different?

**Defend:** The mechanism IS different. The previous 5 recommendations were RECOMMENDATIONS — recommendations that required the human to read the subconscious backlog, understand the context, and decide to act. A pre-commit WARNING fires on every commit in the dev's normal workflow, without needing to read any documentation. It's signal at the point of action, not signal in a weekly review. More importantly: Check 11's primary value is NOT fixing GH #181 — it's preventing future billing constant drift. AMOUNT_TO_PLAN will need updating again when pricing changes (it already has 7 legacy entries from past price changes). The guard protects against all future instances of this class of bug, not just GH #181.

### Round 3

**Challenge:** Is ROI 2.1 realistic given that pre-commit hooks only fire locally? If a developer bypasses pre-commit with `--no-verify`, the guard doesn't fire. And billing.py changes could come through automated commits (nightly review, etc.) that might not run hooks.

**Defend:** The codebase has `.claude/rules/claude-code-security.md` and CLAUDE.md explicitly prohibiting `--no-verify` bypass. The pre-commit hook system has protected against `__future__ annotations` and bare excepts effectively — there's no evidence of bypass. Additionally, the plan is to wire Check 11 into CI eventually (via pr-check.yml) after GH #181 is resolved — the pre-commit addition is the first step of a two-step hardening. Even without CI integration, the local hook creates a feedback loop for the primary dev workflow.

**Verdict: SURVIVES** — Strong evidence, autonomous execution, systemic value beyond GH #181, WARNING mode removes the only valid objection (FAIL dependency). ROI 2.1 stands.

---

## Idea 1: post-split-test-repair SKILL.md (run 36 winner re-recommendation)

### Round 1

**Challenge:** This was run 36's winner (recommended 2026-05-27). The nightly review today explicitly labeled the run 36 artifact as "Documentation/ideas only. No production code changes." — confirming the nightly review DOESN'T autonomously implement skills from winning-concept artifacts. The autonomous implementation mechanism that worked 3 times (runs 24/19/33) appears to be inconsistent. What's the new mechanism that guarantees implementation in run 37?

**Defend:** bca2082 today provides NEW evidence that the run 36 winning-concept.md didn't have: the pattern now covers API cleanup migrations, not just god-class splits. This warrants a scope update to the skill title. More importantly, the skill's full content exists in `subconscious/runs/2026-05-27/winning-concept.md` — any human or Claude session can copy-paste it into the correct path in under 1 minute. The email_sequences split (run 35 winner) is the next god-class target; if the split happens before the skill is created, post-split test repair will again be unencoded. Urgency is real.

### Round 2

**Challenge:** Recommending the same item in two consecutive runs without the mechanism changing is a red flag. The governance.json has a "freeze threshold" of 3 — this is the 2nd consecutive recommendation. One more rejection and the idea gets frozen. If frozen, it can never be recommended even though it clearly has value. Isn't it better to save the recommendation slots for when there's a new mechanism?

**Defend:** The mechanism HAS changed: the task framing in run 37's winning-concept would say "implement this in the current session" rather than "implement this via nightly review." The run 36 winning concept was written assuming the nightly review would execute. Run 37's concept would acknowledge the nightly review didn't act and direct the execution differently. The freeze threshold applies to REJECTED ideas — an idea that's recommended and pending is not "rejected." But the concern about consumption is valid.

### Round 3

**Challenge:** The billing-constant-guard (Idea 2) wins on ALL dimensions — more autonomous, higher ROI, addresses a longer-standing gap, doesn't risk freeze-threshold consumption. Why should post-split-test-repair win over billing-constant-guard?

**Defend:** It shouldn't. The debate isn't about which is BETTER — billing-constant-guard is clearly the stronger candidate for winner. Post-split-test-repair should survive as a parking-lot item, not win.

**Verdict: WEAKENED** — Valid idea, 3-occurrence evidence base, but loses to billing-constant-guard on all decision criteria. Move to parking lot. If email_sequences split happens before the skill is created, re-propose next run with "implement NOW in session" framing.

---

## Idea 3: Agent OS outbound delivery failure tracking

### Round 1

**Challenge:** PR #188 was reviewed by nightly review and passed (MEDIUM, clean). The Agent OS tests include 152 tests covering the outbound channels. The author explicitly verified 498 tests passing. `os_outbound_mirror.py` has try/except error handling — what evidence is there that delivery failures are silently swallowed rather than logged?

**Defend:** Without directly reading `os_outbound_mirror.py`'s error paths, the evidence is CIRCUMSTANTIAL — 3 new external APIs without visible monitoring. The `bca2082` test fix immediately after PR #188 merged suggests the new surface is still stabilizing. But the challenge is valid: we don't have proof of a silent-swallow bug.

### Round 2

**Challenge:** If delivery failure tracking requires a new migration (migration 131), that's a new pending approval item — exactly what the moratorium is trying to reduce. Any PR adding a migration and new logic to `os_outbound_mirror.py` adds to the human-required pending queue. Moratorium exit condition is pending ≤ 2; adding a migration-backed feature pushes the count in the wrong direction.

**Defend:** The monitoring could be implemented without a migration — just add structured `logger.error()` calls in `os_outbound_mirror.py`'s exception handlers. No migration needed. That's a LOW-risk code change (logging only, no schema change). But the problem: without a DB record of delivery failures, the only visibility is Railway logs. That's acceptable for now while the Agent OS is new.

### Round 3

**Challenge:** Is this the highest-leverage thing right now? Agent OS just landed clean. 498 tests pass. The nightly review said "no issues found." The real risk areas per governance are the 4 true pending items (GH #181, moratorium sprint, email_sequences split, AI-to-Human Handoff). Delivery monitoring is a future operational need, not a current critical gap.

**Defend:** Weak. The challenge is correct. Agent OS is stable, monitoring is a "nice to have" right now, and the timing (immediately post-merge, moratorium active) is wrong. Should be a parking-lot item for the first post-moratorium sprint.

**Verdict: KILLED** — Wrong timing. Moratorium conditions. Evidence of actual delivery failures absent. Parking lot — revisit after moratorium exits and Agent OS has production usage data.

---

## Synthesis

| Idea | Verdict |
|------|---------|
| Billing-constant-guard Check 11 (WARNING) | SURVIVES → WINNER |
| post-split-test-repair SKILL.md | WEAKENED → parking lot |
| Agent OS delivery monitoring | KILLED → parking lot |

**Winner: Idea 2 — Billing-constant-guard pre-commit Check 11 (WARNING mode)**

Confidence: HIGH — 26-day evidence base, autonomous execution, systemic guard value independent of GH #181, WARNING mode removes the only valid implementation-dependency objection. 10 lines of bash. Pattern established by Check 5 and Check 9.
