# Debate Log — Run 117 (2026-09-02)

## Contestants

- **Idea 1**: Step 9L — ai-ready loop stall diagnostic in nightly SKILL.md
- **Idea 2**: Exhaustive quote-pair test matrix for `sales_exact_email.ts`
- **Idea 4**: Step 9E 60-day AUTOPILOT_GH_TOKEN advisory (supplement)

Note: Branch run 116 already proposed "Step 9L" as a connector auth scan. This Idea 1 is complementary — a loop PR output check, not a connector grep. Both can coexist in SKILL.md. If Idea 1 wins, the SKILL.md edit should verify branch run 116's Step 9L hasn't already claimed that block name — if so, name this Step 9M.

---

## Round 1: Idea 1 — Step 9L/9M (ai-ready loop stall diagnostic)

### Challenge
"Step 9D already surfaces stale issues. You're proposing Step 9L/9M detects whether PRs were opened in 14 days. But branch run 116 already defined 'Step 9L' as a connector auth pattern scan. If Step 9L is already in SKILL.md (autonomous-executable from run 116), you'd be adding a block with a conflicting name. The nightly would fail or skip one block."

### Defense
Evidence needed: check SKILL.md state on this branch. If run 116's Step 9L is already implemented (it was tagged autonomous-executable), then this winner becomes Step 9M. Name conflict is an implementation detail, not a reason to reject. The diagnostic value is unchanged: detecting 0 loop PRs in 14 days despite stale issues is a gap that Step 9D does not cover. Run 116 targeted connector auth code — a static grep. This targets loop runtime behavior — a PR output check. Complementary.

### Verdict: **SURVIVES** — if Step 9L name conflicts, use Step 9M. Evidence for stall is fresh (3 issues >24h, valid token, 0 loop PRs visible in any recent nightly log). Autonomous-executable via proven channel.

---

## Round 2: Idea 2 — Exhaustive quote-pair test matrix for `sales_exact_email.ts`

### Challenge
"4 PRs in 3 days on the same bug is compelling. But this fix requires: (1) reading the current test file, (2) understanding the TypeScript implementation, (3) building an 8-combo parameterized test suite. That's NOT autonomous-executable via SKILL.md edit. It needs a Cursor session or human developer. The subconscious can only recommend; it cannot implement. So the recommendation is: 'someone should write this test.' That's weak — it gives no implementation artifact. The nightly SKILL.md-edit channel produces zero value here."

### Defense
Idea 2 IS executable — by a human or Cursor. The winning concept would include exact test combinations, the parameterized `test.each` structure, and file path. That's a complete spec a developer can paste-implement in <30 min. It prevents the next 3 PRs.

### Counter-challenge
"Compare leverage vs. Idea 1. Idea 1 is autonomous-executable — nightly fires it automatically. Idea 2 requires a human to decide to act on the spec. Given ai-ready loop stall (0 PRs, queue of 4 issues), the loop capacity is zero. A Cursor-dependent recommendation has no forcing function. Idea 1 fires next nightly automatically."

### Verdict: **WEAKENED** — sound recommendation but lower leverage. No forcing function. Drops to backup; escalate to run 118 winner if ≥2 more sales_exact_email fix PRs appear.

---

## Round 3: Idea 4 — Step 9E 60-day AUTOPILOT_GH_TOKEN advisory

### Challenge
"Step 9E fires at 76d. You're adding a 60d advisory 16 days earlier. Token is at 60d — so this fires TODAY. But the change is 2-3 lines of SKILL.md. It provides zero operational improvement beyond 'hey, rotate soon.' If the human ignores the 76d alert, why will they act on a 60d advisory?"

### Defense
60d advisory is LOG-ONLY, no comment. Very low noise. Value is scheduling flexibility: 30d vs 14d to rotate. Historical GH #399: 55d stall because token expired without early warning.

### Counter-challenge
"Insufficient leverage to displace Idea 1. Can be bundled as a bonus in the winning concept (2-3 extra lines) without taking the winner slot. Idea 1 addresses a live, confirmed stall with HIGH leverage."

### Verdict: **KILLED as standalone** — bundleable as bonus in same SKILL.md commit. Not winner-slot material.

---

## Final Ranking

| Idea | Verdict | Reason |
|------|---------|--------|
| Idea 1 — Step 9L/9M loop stall diagnostic | **SURVIVES** | Autonomous-executable, live evidence, proven channel |
| Idea 2 — quote-pair test matrix | **WEAKENED** | Sound but no forcing function |
| Idea 4 — 60d token advisory | **KILLED as standalone, bundled** | Trivially bundleable |

## Winner: **Idea 1 — Step 9L or 9M (loop stall diagnostic)**

Implementation note: verify SKILL.md for Step 9L presence (from run 116). If present, use Step 9M. Bundle Idea 4 (60d advisory) as a 2-line bonus in the same commit.
