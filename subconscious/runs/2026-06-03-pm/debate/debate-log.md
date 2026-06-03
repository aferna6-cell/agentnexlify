# Debate Log — Run 49 (2026-06-03-pm)

Top 3 ideas by impact: Idea 1 (autonomous em-dash), Idea 2 (Items A+B human), Idea 5 (AI-to-Human Handoff).

---

## Idea 1: Extend nightly SKILL.md + apply 5 em-dash patches (AUTONOMOUS-EXECUTABLE)

### Round 1 Challenge
**Attack:** Run 44 also attempted an autonomous scope extension and failed. Nightly confirmed "Python script edits outside its scope." What guarantees this SKILL.md extension works where run 44's didn't?

**Defend:** Different class of change. Run 44's failure was about Python script edits to `scripts/hooks/pre-commit` — modifying a hook file. Run 49's fix is simple character substitutions in JSX UI copy strings. e7e0a3b (June 1) is direct evidence nightly CAN fix em-dashes in source files (App.jsx, os-inbound.js). The distinction is: nightly fixes UI copy strings with em-dashes when authorized to do so. It didn't fix these 5 because its SKILL.md scope says "LOW-risk source code fixes" without explicitly naming em-dash violations from check_project_invariants.py.

### Round 2 Challenge
**Attack:** The nightly ran 3 consecutive times (June 1, 2, 3) without fixing these violations. If the nightly's autonomous scope already allowed source-file em-dash fixes (via e7e0a3b precedent), why didn't it apply them? This suggests the nightly's interpretation of "em-dash fix scope" is narrower than assumed.

**Defend:** e7e0a3b fixed em-dashes described as "in comments" — the nightly may have scoped that fix to code comments only, not JSX content strings. The SKILL.md extension makes this explicit: "em-dash → hyphen replacement in JSX/JS source files when check_project_invariants.py exits 1 for em-dash check." Explicitness is the mechanism. Every successful SKILL.md extension (runs 40, 43, 47) worked because the scope was explicit, not implicit.

### Round 3 Challenge
**Attack:** Adding em-dash fixes to nightly autonomous scope creates a permanent behavior change. What if future UI copy legitimately needs em-dashes for a different reason?

**Defend:** CLAUDE.md personality rules (`.claude/rules/personality.md`) explicitly ban em-dashes in project output. This is a project-wide rule. Making it autonomous is consistent with enforcement intent. check_project_invariants.py already enforces it on commit — nightly auto-fixing is just closing the feedback loop.

### Verdict: **SURVIVES → WINNER**
New mechanism. Evidence-backed. Explicit SKILL.md scope is the proven pattern. Exact patches in winning-concept.md leave no ambiguity for nightly execution.

---

## Idea 2: Items A+B combined — human-execute

### Round 1 Challenge
**Attack:** This is the exact same recommendation as run 48 (and similar to runs 45, 46). What forcing function exists in run 49 that didn't in run 48?

**Defend:** None — which is the honest problem with this idea. The recommendation is technically correct. Human execution in an interactive session IS the most reliable path if a human is present. But 2 consecutive identical recommendations without implementation signal that human activation energy is the true bottleneck, not information.

### Round 2 Challenge
**Attack:** If Idea 1 (autonomous) succeeds, Idea 2 becomes redundant for Item A. Item B (widget sync guard) still needs human action. Should Idea 2 be scoped down to "just Item B"?

**Defend:** Yes. If Idea 1 wins, Item B becomes the standalone human task (~15 min vs 25 min combined). Reducing scope reduces activation energy. "Create scripts/check-widget-sync.sh" alone is a cleaner ask.

### Round 3 Challenge
**Attack:** Is there evidence that humans are MORE likely to create a widget sync script than to fix 5 em-dash lines? Both are short tasks.

**Defend:** No strong evidence either way. The moratorium has shown that even S-effort items go unimplemented for 30+ days. Idea 1 bypasses this entirely via automation.

### Verdict: **WEAKENED → Parking Lot**
Dominated by Idea 1 for Item A. Item B (widget sync guard, ~15 min) survives as a standalone Bonus Action. If Idea 1 fails overnight, Idea 2 remains the fallback for run 50.

---

## Idea 5: AI-to-Human Handoff minimal v1

### Round 1 Challenge
**Attack:** 7+ prior recommendations without implementation. Specifically "AI-to-Human GH Issue mechanism evaluated: 3x recommended without action — demoted to parking lot" (run 30). Run 38 reframed via Agent OS. Still deferred 4 more runs. What's genuinely new in run 49?

**Defend:** Nothing new beyond what run 38 established (Agent OS scope reduction). The moratorium has been displacing this for 34 days. The case for this is strong on merits but the mechanism is broken.

### Round 2 Challenge
**Attack:** Moratorium protocol. Adding a new M-effort pending item during moratorium increases pending count and extends moratorium. Protocol prioritizes clearing existing pending items over adding new ones.

**Defend:** This is correct per governance. Moratorium exit path (Items A+B → Check 10 → moratorium sprint) should complete before starting M-effort items. AI-to-Human Handoff has waited 48 days; it can wait for the 2-3 more items needed to exit moratorium.

### Round 3 Challenge
**Attack:** Every run, this item is called "post-moratorium first priority." Moratorium has been active 34 days. At what point does keeping this in parking lot become negligence?

**Defend:** Valid concern. But recommending it as subconscious winner when the mechanism is clearly broken (7+ recs, zero implementation) just adds pending count and delays moratorium exit further. The right answer is: exit moratorium FIRST, then sprint on AI-to-Human Handoff with full human attention.

### Verdict: **KILLED as winner**
7+ recommendations without implementation. Moratorium active. No new forcing function. Standing note: post-moratorium FIRST priority. Run 50 or first post-moratorium free-choice run.
