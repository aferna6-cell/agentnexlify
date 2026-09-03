# Debate Log — Run 115 — 2026-09-03-pm

Top 3 ideas by impact ranked for debate: Idea 1 (Step 9L), Idea 2 (M9.2 dead code fix), Idea 3 (File GH issue 196/197).

---

## IDEA 1: Step 9L — Unapplied Migration Nightly Alerter

### Round 1: Challenge
- Is the evidence strong enough? schema-log.md is manually maintained. If the human forgets to mark a migration as applied, nightly detects it — but if they forget to add the entry to schema-log.md at all, nothing is detected. False negatives are possible.
- Is this the highest-leverage thing to do right now? The 196/197 risk is real today. But filing a GH issue (Idea 3) achieves immediate human notification without touching SKILL.md.
- What could go wrong? Step 9L fires every night with "NOT YET APPLIED" comments until the human applies the migration and updates schema-log.md — could spam the GH issue. Dedup guard mitigates.
- Has something similar been tried and rejected? Steps 9F–9K follow this pattern. All passed. No rejections.
- Is this too similar to the current active direction? Active direction is Step 9K (stale subconscious PR audit). Step 9L is a different detection domain (migrations vs. PRs). Not redundant.

### Round 1: Defend
- Manual maintenance of schema-log.md is the existing workflow — agents already update it on migration application. False negatives from forgotten entries are bounded by the same process that would forget to apply the migration. The detection catches the gap between "SQL file exists" and "schema-log says APPLIED".
- Idea 3 (file GH issue) is one-shot and requires human to re-verify every future migration. Step 9L is systemic — fires on every unapplied migration found, now and forever. Higher leverage.
- Dedup guard (check if issue open before filing, cap at 1 comment per 24h per issue) prevents spam. Proven pattern from Step 9J rebase trigger.

### Round 1 Verdict: SURVIVES

### Round 2: Challenge
- Step 9K was implemented in run 113/114. Adding Step 9L in run 115 means two new SKILL.md steps in three runs. Is SKILL.md becoming too complex to maintain?
- The winning concept would recommend but not implement. Who implements? GH #399 means issue-to-pr-loop can't pick it up automatically. SKILL.md edit is autonomous-executable by nightly, but the detection step itself needs to be added first.
- Is 196/197 really a billing correctness risk today? The nightly log doesn't show a double-invoice send event — only that the migration is unapplied. Risk is potential, not actualized.

### Round 2: Defend
- SKILL.md has steps 9A–9K (11 steps). Each step is self-contained, ~15-20 lines. Adding Step 9L keeps the document under 350 lines (current estimate ~320 + 20 = 340). No maintenance crisis.
- Autonomous-executable means: subconscious SKILL.md edit fires on next nightly-commit-review, which IS autonomous. No GH #399 dependency for the SKILL.md edit itself. The SKILL.md change is the recommendation; nightly will then detect and file the GH issue on its own.
- The risk is potential but migration 197 (double-invoice idempotency) directly governs Billing Automation v1 behavior. Billing errors tend to be discovered by customers, not logs. Proactive detection is exactly the use case.

### Round 2 Verdict: SURVIVES STRONG

### Final Verdict: **SURVIVES → WINNER CANDIDATE**

---

## IDEA 2: Fix M9.2 Dead Code in derive_workflow_status()

### Round 1: Challenge
- Is the evidence strong enough? Nightly flagged this as LOW — not behavioral. Dead code that doesn't break anything.
- Is this the highest-leverage thing to do right now? M9 is actively developed. fdcbb97 landed today (M9.4 fix). Touching engine.py today risks merge conflict in <24h.
- What could go wrong? A 2-line diff to engine.py today could conflict with the M9.4 follow-up commits that may land tomorrow. "Dead code" status could change if M9 adds new state variants.

### Round 1: Defend
- The fix is surgical (remove 1 redundant condition, ~2 lines). Blast radius is zero; semantics unchanged.
- The risk of M9 evolution is real. If M9 adds "unknown" or "failed" as valid workflow states, the inner guard becomes meaningful again. Removing it now is correct for current invariants but could confuse future engineers about why the guard was removed.

### Round 1 Verdict: WEAKENED — timing is poor (M9 active today)

### Round 2: Challenge
- If the recommendation is "fix dead code in M9", it will land AFTER M9 is stable. But by then, M9.5/9.6 may have already reorganized engine.py. The fix could be stale before it's implemented.

### Round 2: Defend
- Can note the risk in the winning-concept's implementation sketch: "verify inner guard is still dead code before applying".

### Round 2 Verdict: WEAKENED — parking lot. Better for nightly to apply autonomously after M9 stabilizes.

### Final Verdict: **WEAKENED → PARKING LOT**

---

## IDEA 3: File GH Issue for Migrations 196/197

### Round 1: Challenge
- GH #399 (AUTOPILOT_GH_TOKEN expired) means issue-to-pr-loop is stalled. Filing a new GH issue for 196/197 creates a record that no automation can act on. It sits unresolved alongside the 30+ other ai-ready issues in the stalled queue.
- Step 9L (Idea 1), if implemented, would detect 196/197 AND file a GH issue automatically on the next nightly run. Step 9L makes Idea 3 redundant — any issue filed manually today would be superseded by Step 9L's automated version.
- Is this more than a paper trail? The subconscious can't apply migrations (no Supabase MCP in headless sessions — confirmed run 88 governance correction). Filing an issue is the only available action, but it's a lower-leverage one than Step 9L.

### Round 1: Defend
- One day's lag matters for billing. If Step 9L is approved but not yet implemented (requires 1 nightly cycle), filing a GH issue today provides immediate notification.

### Round 1 Verdict: KILLED — Step 9L is a strict superset. One-shot GH issue filing is redundant when Step 9L will both detect AND file automatically. No value-add over Idea 1.

---

## Synthesis

| Idea | Final Verdict |
|------|--------------|
| Step 9L: Unapplied Migration Alerter | SURVIVES STRONG → **WINNER** |
| M9.2 Dead Code Fix | WEAKENED → Parking Lot |
| File GH Issue 196/197 | KILLED — subsumed by Step 9L |
| Step 9M: Env-var Staleness Watchdog | Not debated — Idea 4 |
| Governance.json Pruner | Not debated — Idea 5 |

Winner: **Step 9L — Unapplied Migration Nightly Alerter**
Confidence: **HIGH** — strong evidence (196/197 unapplied with billing automation live), autonomous-executable, follows proven 9F-9K pattern, debate survived two rounds without fatal objections.
