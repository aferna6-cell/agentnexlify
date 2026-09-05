# Debate Log — Run 115 (2026-09-05)

## Top 3 Ideas Debated (ranked by impact)

---

## Idea 4: Step 9L — AI Metering Coverage Nightly Check

### Challenge
- Is the metering problem actually recurring, or was PRs #792-#799 a one-time catch-up?
- grep-based detection could produce false positives — files that import anthropic but delegate the call to another service
- Step 9J already has a token budget problem (17/19 PRs skipped 2026-09-05). Adding Step 9L could exhaust budget earlier.
- Similar to Step 9I (demo-role sweep) — but demo-role violations cause immediate runtime failures; metering gaps are silent accumulations.

### Defend
- PRs #792-#799 show 6 endpoints metered in 3 days: widget_guard.screen, categorize_conversation, extract_action_items, extract_tags, voice call summaries, sms_agent.reply. Pattern is real and recurring. The metering PRs each required 498-1726 new test lines — substantial sprint cost.
- False positives: Step 9L can check for `ai_usage_guard` dependency OR `reserve_tokens`/`record_usage` pattern in the same file. Both patterns together confirm metering. Helper files that only import anthropic without calling it won't have reserve/record calls.
- Token budget: Step 9L is grep-only — no per-PR iteration. Budget impact is minimal vs Step 9J which loops 19 PRs individually.
- Demo-role gaps DO cause failures; AI metering gaps cause cost leakage + incorrect billing. Silent but expensive. Fitness for Step 9L is confirmed.

**Verdict: SURVIVES** — strong evidence, low implementation risk, nightly grep is the proven mechanism.

---

## Idea 1: Add AI Usage Guard Checklist to compound-engineering SKILL.md

### Challenge
- compound-engineering already has quality gates (code-reviewer agent, /ultrareview, vertical-checker)
- A checklist that humans must remember to run is weaker than automated detection
- Doesn't catch AI endpoints added via commits that bypass the compound-engineering skill
- Duplicates what Step 9L would do automatically each night

### Defend
- compound-engineering is the PREVENTION layer; Step 9L is the DETECTION layer. Both have value.
- Code added via compound-engineering is the bulk of new AI endpoints — a pre-merge checklist catches issues before they ship, not the next morning.
- Checklists in SKILL.md are enforced at the skill's quality gates — less reliant on human memory.

**Verdict: WEAKENED** — not wrong, but superseded by the better automated version (Idea 4). compound-engineering checklist is follow-up work after Step 9L proves the pattern. Move to parking lot.

---

## Idea 3: Invoke /god-class-splitter on os_tool_executions.py

### Challenge
- 783L is 30% over the threshold, but the file has been touched 0 times in 4-5 days — it's not actively accumulating.
- Splitting a 783-line file across multiple modules risks import path changes that break callers.
- No bugs in os_tool_executions.py were reported in the last 3 nightly reviews — not a burning problem.
- Run 114 mandate said "if stable 4d+, candidate for 115" but didn't mandate it.

### Defend
- 783L is 30% past threshold (Rule 9). The file handles tool execution, billing, state management — 3 distinct concerns. That IS god-class territory.
- The file IS stable (4-5d no commits) — best time to refactor is when nothing is actively changing it.
- Impact: reduces blast radius for future billing/automation work. No runtime bug required — Rule 9 is preventive.
- Caller count matters: need to grep callers before committing. Low caller count → low risk.

**Verdict: SURVIVES** — second candidate. Demoted to parking lot for run 116 because Step 9L has higher leverage (prevents future metering sprints > refactors one file).

---

## Winner

**Idea 4: Step 9L — AI Metering Coverage Nightly Check**

Reasoning: highest leverage among surviving ideas. Automates detection of a proven recurring problem class. grep-based, low token cost, same proven mechanism as Steps 9I/9K. Prevents multi-day retroactive metering sprints. SKILL.md edit — autonomous-executable if not approved by run 116. Compound-engineering checklist (Idea 1) is weakened but adjacent — useful as a follow-up once Step 9L confirms the pattern. os_tool_executions.py split (Idea 3) is run 116 candidate if still stable.
