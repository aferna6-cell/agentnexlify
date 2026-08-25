# Debate Log — Run 110 (2026-08-25)

## Ranking by Impact (input to debate)
1. Idea 4: Block_demo_role middleware — closes 97-router security gap
2. Idea 1: Step 9K — stale PR closer, run 110 mandate
3. Idea 2: memory.jsonl dedup guard — structural hygiene

---

## Debate 1: Idea 4 — Block_demo_role Middleware in main.py

### Challenge
**Is evidence strong enough?** GH #669 is class-wide (97 routers) but step 9I has been sweeping for 6 days without any router getting fixed. PR #653 (middleware draft, 12d) hasn't been reviewed. If the human hasn't reviewed a 12d draft PR, recommending the same thing again adds no new signal.

**Is this highest-leverage right now?** PR #653 already encodes this recommendation. The subconscious does NOT implement — it recommends. The recommendation already exists as a live PR. Repeating it is a no-op.

**What could go wrong?** Middleware approach is broad: must exclude widget chat (public), healthz, webhooks, public endpoints. Wrong exclusion list → breaks paying-tenant widget. High risk of a silent regression in a non-obvious path.

**Rejected before?** Not explicitly, but context: the subconscious has been noting GH #669 in mandates since run 106. 4+ references to it without new evidence. Approaches the rejected_paths threshold.

**Too similar to active direction?** Step 9I (active, implemented) already sweeps nightly and files issues per violation. The class-wide fix is a separate architectural decision that needs human code review — not subconscious's lane.

### Defend
**Counter on "no new signal":** PR #653 exists but is 12d stale. Escalating with a clear implementation sketch (specific exclusion list from nightly sweep data) adds precision the original PR lacked.

**Counter on risk:** The middleware exclusion list can be derived exactly from Step 9I sweep results — any route NOT flagged by Step 9I is safe to exclude.

**Counter on lane:** Subconscious CAN produce an implementation sketch precise enough that a human (or executor agent) can apply it in under 10 minutes.

### Verdict: **WEAKENED** → Parking Lot
Rationale: PR #653 already encodes the recommendation. Subconscious adding a 5th reference without new implementation-enabling specificity is noise, not signal. Step 9I provides daily pressure. The missing ingredient is human review time — subconscious cannot supply that. Demote to parking lot. Re-elevate only when GH #399 unblocked (so issue-to-pr-loop can implement autonomously).

---

## Debate 2: Idea 1 — Step 9K: Stale Subconscious PR Closer

### Challenge
**Is evidence strong enough?** 4 open draft PRs (>= 3 threshold). Run 110 mandate explicitly named Step 9K. Threshold met on all counts.

**Is this highest-leverage right now?** PR queue management doesn't fix security holes or generate revenue. Is this procrastination on harder problems?

**What could go wrong?** Step 9K might auto-close a PR that the human actually wanted to review. #653 (block_demo_role middleware, 12d) is substantive — auto-closing it would lose the implementation sketch. Need a safeguard: only auto-close PRs whose winning concept is confirmed `implemented` in governance.json.

**Has similar been tried?** No — this is a net-new step. Steps 9A through 9J all established in prior runs; 9K is next logical slot.

**Too similar to active direction?** No. Current direction (Step 9J) is about merging Dependabot PRs. Step 9K is about closing superseded subconscious PRs. Different mechanism, different target PRs.

### Defend
**Counter on leverage:** The PR pile-up causes a specific harm: the human needs to decide which subconscious PR to review. With 4 open, the signal is diluted. Step 9K auto-closes the clearly-superseded ones (#575 = 32d, implementations from runs 78+101 already shipped; #626 = 22d, Step 9G direct-edit already shipped). Reduces queue from 4 to 2 after first run.

**Counter on auto-close risk:** Add explicit safeguard: auto-close only if governance.json active_directions entry shows `"implemented": true` for the concept. #653 (block_demo_role middleware) has no implemented entry → safe from auto-close. #575 and #626 are clearly superseded.

**Counter on "harder problems":** The subconscious cannot fix GH #399 (token rotation), KB staleness (human secrets), or block_demo_role (code review). It can fix PR noise. Within autonomous channel capabilities, this is the highest-value action.

### Verdict: **SURVIVES**
Rationale: Run 110 mandate explicit. Evidence threshold met (4 PRs ≥ 3). Auto-close safeguard (implemented=true guard) neutralizes the main risk. Net-new step with no prior rejection. Autonomous-executable via SKILL.md edit. Compounds permanently — future runs won't accumulate stale drafts.

---

## Debate 3: Idea 2 — memory.jsonl Dedup Guard

### Challenge
**Is evidence strong enough?** Two identical entries from run 109. This is a single-instance observation — could be a one-off from the multi-run PR (#674 merged multiple run artifacts).

**Is this highest-leverage?** memory.jsonl is read for context in Phase 1 (last 5 entries). A duplicate entry wastes one of the 5 slots. Impact is minimal — the other 4 entries are still correct.

**What could go wrong?** The dedup guard itself could be wrong: if the check compares `run` field but the run is given a date-string (e.g. "2026-08-24") vs integer (109), the comparison fails silently.

**Has similar been tried?** No prior runs have mentioned this bug. It's genuinely novel.

**Too similar to active direction?** Not in conflict. But it's a meta-fix to the subconscious loop itself, not a product improvement.

### Defend
**Counter on one-off:** Run 109 artifacts show TWO separate memory entries with identical content. The PR (#674) merged multiple run folders — confirming the mechanism: when multiple run-folders are committed at once, Phase 6 runs once per commit (or the skill ran twice). The dedup guard prevents recurrence.

**Counter on leverage:** Agreed — minimal impact. The 5-entry window is fine with 4 unique entries. But the fix is a 1-line check that takes 2 minutes. ROI is positive even at minimal impact.

**Counter on safeguard:** Use string equality on the `winner` field, not run number, to compare entries robustly.

### Verdict: **SURVIVES but low priority** → Parking Lot
Rationale: Genuine bug, real fix, but minimal blast radius. Step 9K produces more value per token spent writing the SKILL.md block. Recommend for a future run when no higher-leverage item exists.

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| Idea 4: Block_demo_role middleware | WEAKENED → Parking Lot | PR #653 already exists; subconscious recommending again adds no new signal without autonomous execution path |
| Idea 1: Step 9K stale PR closer | **SURVIVES → WINNER** | Run 110 mandate, 4 PRs ≥ threshold, autonomous-executable, safeguard neutralizes risk |
| Idea 2: memory.jsonl dedup guard | SURVIVES → Parking Lot | Real bug, minimal impact; save for lower-leverage run |
| Idea 3: Step 9J fallback | Not debated (lower rank) | Parking lot — valid but Step 9K more urgent |
| Idea 5: Step 9J dark-awareness | Not debated (lower rank) | Parking lot — honest logging improvement |
