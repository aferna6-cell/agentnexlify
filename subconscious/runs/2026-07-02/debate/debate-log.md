# Debate Log — Run 77 (2026-07-02)

## Top 3 Ideas (Ranked by Expected Impact)

1. Idea 1 — Subconscious SKILL.md: File-Location Verification in Evidence Phase
2. Idea 3 — Custom Automation Templates (cross-industry)
3. Idea 2 — Plan-Name Guard Pre-Commit (Check 14)

---

## Debate Round 1: Idea 1 — File-Location Verification in Evidence Phase

### Challenge
- "Is this just accounting? The subconscious is supposed to improve the PRODUCT, not its own machinery."
- "The nightly already corrected memory.jsonl — is a SKILL.md patch even needed?"
- "What's the ROI vs shipping an actual feature?"
- "Has this failure mode happened before, or is this a one-time event?"

### Defend
- The skill brief explicitly says the subconscious should improve workflows and agent performance, not just ship product features. "Agent Performance" is category 3 in the brief.
- The nightly corrected memory.jsonl but did NOT patch the SKILL.md. Future runs still have no guidance on file-location verification. Without the patch, the same failure will recur on any governance.json entry with a stale or assumed file path.
- ROI: 2 wasted runs × ~50 agent calls each = ~100 wasted agent calls. 1 line in SKILL.md prevents the next occurrence. Compounding prevention.
- The B-001 incident is NOT isolated: `email_sequences.py` is ALSO not found at the assumed path from run 41's governance note. Same failure mode, second target already visible. Pattern confirmed.

### Verdict: **SURVIVES**

Evidence strength: HIGH (two concrete wasted runs + second stale-path instance found this run)  
Leverage: AUTONOMOUS-EXECUTABLE, compounds across all future runs  
Conflict with prior rejected paths: NONE (never proposed before)

---

## Debate Round 2: Idea 3 — Custom Automation Templates

### Challenge
- "Moratorium is active (pending > max_pending_approvals=2). Adding a Medium-effort human-required item makes the moratorium worse."
- "Agent OS shipped 5 weeks ago but no tenant has requested automation templates yet — is this evidence or just a doc entry?"
- "7 consecutive runs since the moratorium triggered (run 15) have been meta or code-health. Is customer value work even feasible?"

### Defend
- customer-gaps.md cross-industry signal is the strongest available. All 6 simulated verticals surfaced this gap.
- Agent OS infrastructure genuinely reduces implementation from scratch (~5 days) to leveraging existing plumbing (~2-3 days).
- But: moratorium is the hard constraint. Medium effort + requires_human: true = adds 1 to pending queue. true_pending after Phase 6 corrections will be ~2-3. Max = 2. Adding another human item keeps moratorium alive.
- Counter: even if the idea is good, wrong time. Re-evaluate post-moratorium.

### Verdict: **KILLED — wrong timing**

Reason: Moratorium active. Medium effort. Adds to human queue. The idea itself is valid — park for post-moratorium cycle.

---

## Debate Round 3: Idea 2 — Plan-Name Guard Pre-Commit (Check 14)

### Challenge
- "No documented incident where a retired plan name (`foundation`/`operations`) appeared in new code. The GH #292/#293 incident was about MISSING new plan names, not PRESENCE of retired ones. Different failure mode."
- "Check 13 already exists (check_project_invariants.py). Does that not already cover plan-name violations?"
- "Is this CLAUDE.md compliance or a real bug risk?"

### Defend
- CLAUDE.md rule: "Retired names, never use: foundation, operations." No pre-commit guard enforces this. check_project_invariants.py (Check 13) checks for CLAUDE.md schema field naming (`client_id`, `status`, etc.) but NOT plan name strings.
- GH #292/#293 proves plan name dicts cause revenue bugs — wrong plan = wrong feature access = revenue loss.
- However: Challenge is correct that retired-names-in-NEW-code has ZERO documented occurrences. Only the absence of a guard, not evidence of a real gap.
- A zero-incident risk with a 10-line autonomous fix is worth doing — but it's not the HIGHEST leverage thing this run.

### Verdict: **WEAKENED → parking lot**

Valid, zero cost, autonomous. But evidence of actual occurrence is absent. Pick it up opportunistically when touching pre-commit next. Or make it the winner in a "nothing more urgent" run.

---

## Synthesis

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 1: SKILL.md file-location verification | SURVIVES | → WINNER |
| Idea 3: Custom automation templates | KILLED | Moratorium active; re-propose post-lift |
| Idea 2: Plan-name guard pre-commit | WEAKENED | → Parking lot; autonomous, low urgency |
| Idea 4: Trial-to-member metric | Not debated | → Parking lot; single vertical |
| Idea 5: customer-gaps.md cleanup | Not debated | → Bonus action (XS, run alongside winner) |
