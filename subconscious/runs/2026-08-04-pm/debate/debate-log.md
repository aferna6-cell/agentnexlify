# Debate Log — Run 101 (2026-08-04-pm)

Top 3 ideas ranked by impact. Each runs a challenge-and-defend cycle.

---

## Idea 1: Strengthen Subconscious SKILL.md Dedup Guard

### Challenge
- Is the evidence strong enough? The dedup guard prose already exists — maybe headless sessions just haven't been executed this particular session. Couldn't the proliferation be a one-off?
- Is this the highest-leverage thing? Two competing Step 9G PRs are the morning digest's Priority 1. Wouldn't resolving #625/#626 directly (Idea 2) be faster?
- What could go wrong? Changing SKILL.md triggers the dedup guard check on the NEXT run — but if that run also has the dedup guard bug, we get another new PR. Circular.
- Has something similar been tried and rejected? Run 100 winning-concept.md added the prose guard. Prose guards have a consistent record of failure in this system (see moratorium history: 10+ consecutive runs where prose guidance wasn't followed in headless sessions).
- Is this too similar to the current active direction? No — current active_directions track Step 9G implementation (feature), not dedup guard (meta-workflow). Distinct.

### Defend
- Evidence is strong: 5 competing PRs over 2 days is not a one-off. Morning digest independently flagged it as Priority 1 before this run started. `grep -c "Step 9G"` confirms SKILL.md = 0 despite two PRs claiming to implement it.
- Idea 2 (directly resolve #625/#626) is a human-action recommendation, not an autonomous fix. It closes the immediate problem but not the root cause. Dedup guard fix closes both current and future PR proliferation.
- Circular risk is real but mitigated: SKILL.md edit is committed to the existing open PR (#625 or #626), not a new one. The fix is on the branch BEFORE it's merged to main. When the branch merges, the fixed guard is live. Next headless run sees the fixed guard and follows it.
- Prose guards fail in this system because they rely on the model "reading carefully" in a stateless headless context. Tool-call guards fail only if the MCP server is unavailable — much more reliable.

### Verdict: **SURVIVES → CHOSEN AS WINNER**

---

## Idea 3: Typed KB Notes Retrieval Audit

### Challenge
- Is the evidence strong enough? We don't have direct evidence that the chat path excludes `source='note'` — this is speculative. Maybe the KB retrieval path queries all `tenant_kb_documents` rows regardless of source.
- Is this the highest-leverage thing right now? Typed KB notes just shipped today. No live tenants have added notes yet. If the feature is broken, no real impact exists yet.
- What could go wrong? The audit could consume run attention on a potential problem that doesn't exist. The nightly review (4853c31) passed all invariant checks.
- Has this been tried before? No prior runs have audited the KB retrieval path specifically.

### Defend
- Finding the issue now costs 5 minutes (grep). Letting it go means typed notes are in production but dark — tenants add notes expecting AI to use them, get no change in chat quality.
- Nightly review checked schema invariants, not retrieval path correctness. Different scope.
- The audit result becomes a mandate item either way: PASS = confirm feature complete, FAIL = file GH issue. Low cost.

### Verdict: **WEAKENED — demoted to run_102_mandate item.** Retrieval audit is XS effort and definitively answers the question. But the winner spot goes to the structural fix (dedup guard) because it prevents future systemic failures rather than fixing a potential single-feature gap. Mandate: run 102 MUST grep `backend/services/` for `tenant_kb_documents` queries and verify `source` filter behavior.

---

## Idea 4: Agent OS Loop-Health Noise Reduction

### Challenge
- Is the evidence strong enough? GH #628 and #633 are open `loop-health` issues — but "loop health report" issues being open is expected; they're automated tracking issues, not alerts. Is there actual noise to reduce?
- Is this the highest-leverage thing? Loop-health reporting noise is cosmetic. 5 competing subconscious PRs is structural.
- What could go wrong? Tightening loop-health reporting criteria might suppress real signals. Agent OS is in early rollout (2-3 tenants) — the signal set may legitimately be sparse.
- Has it been tried before? No prior runs proposed loop-health noise reduction.

### Defend
- GH #628 and #633 appear in "Issues opened/updated" section of morning digest. If loop-health issues are routine automated tracking, they don't belong in the "needing action" section. Some de-noise would improve digest signal-to-noise ratio.
- But this is lower leverage than dedup guard. Loop-health is a reporting issue; dedup guard is a delivery failure mode.

### Verdict: **WEAKENED → parking lot.** Re-evaluate after Agent OS scales to 5+ tenants. At current scale (2-3 tenants), loop-health noise is minor.

---

## Summary

| Idea | Verdict | Next Step |
|------|---------|-----------|
| 1. Dedup guard (SKILL.md) | SURVIVES → WINNER | Implement in this run's artifact |
| 3. Typed KB notes retrieval audit | WEAKENED → mandate | run_102_mandate item 1 |
| 4. Agent OS loop-health noise | WEAKENED → parking lot | Re-evaluate at 5+ tenants |
| 2. Resolve #625/#626 directly | Not in top 3 debate | Parking lot — human action |
| 5. VOYAGE_API_KEY alert (Step 9J) | Not in top 3 debate | Parking lot — pending Step 9G merge |
