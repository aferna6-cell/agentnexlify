# Debate Log — Run 2026-09-18 (Run 122)

## Debated Ideas: Top 3

Ideas ranked by evidence strength and governance binding:
1. Idea 1: Step 9E 10-day P0 escalation tier (governance mandate — 3rd carry-forward)
2. Idea 2: Fix Step 9G SKILL.md (1st carry-forward, autonomous-executable at run 124)
3. Idea 3: File P0 GH issue for credential rotation (operational urgency)

---

## Idea 1 — Step 9E 10-Day P0 Escalation Tier

**FOR:**
- Governance mandate: 3rd consecutive carry-forward (runs 119→120→121→122). SKILL.md says "3 consecutive carries → run 124 fires" for autonomous-executable — this IS run 124's predecessor, and the mandate fires at 3 carries, which is now. The governance chain is binding.
- Direct operational impact: AUTOPILOT_GH_TOKEN expires 2026-10-02 (14 days). The 10-day tier fires at day 80 of a 90-day cycle — exactly when urgency is highest and owner is most likely distracted. Without the tier, there's no P0 alert forcing action before expiry.
- Systemic fix: covers ALL future credentials, not just this one rotation event. Brain PAT, SUPABASE_ACCESS_TOKEN, and any future credentials benefit.
- Effort XS: Step 9E already checks days since last_rotated. Adding `days_remaining = interval - days_since` and `if days_remaining <= 10:` is a small delta.
- Precedent: Steps 9F, 9G, 9I, 9J, 9K, 9L all autonomously implemented via same channel.

**AGAINST:**
- Idea 3 (filing a P0 issue manually) argues that the immediate need doesn't require SKILL.md changes — just file the issue now. True but insufficient: manual filing fixes this rotation cycle only. The SKILL.md change fixes all future cycles.
- Risk of incorrect `days_remaining` math if rotation schedule format varies. Mitigable: read `ops/credential-rotation-schedule.md` for exact column format before implementing.

**VERDICT: SURVIVES → WINNER.** Governance mandate is binding. Systemic fix over one-time manual action. Risk is low (simple arithmetic), evidence is complete.

---

## Idea 2 — Fix Step 9G SKILL.md (Replace `gh workflow run` with MCP)

**FOR:**
- Run 121 winner. Nightly confirmed the MCP workaround works (status 204, "Workflow run has been queued"). The fix path is validated.
- Currently causing Step 9G to silently apply in-session workaround every nightly instead of following SKILL.md instructions. That's a documentation drift — SKILL.md and actual behavior diverge.
- XS effort — direct substitution of one bash block.

**AGAINST:**
- Only 1st carry-forward. Autonomous-executable channel requires 3 carries (runs 121→122→123→124). This idea is only at 1st carry-forward. The governance protocol says autonomous-executable at run 124.
- The nightly already applies a manual workaround, so the operational damage is contained for now.
- Implementing run 121's winner in run 122 isn't wrong per se, but it would compete with the run 122 autonomous-executable mandate for Idea 1 as the "one winner" constraint.

**VERDICT: WEAKENED → Parking lot.** The governance mandate for Idea 1 must take priority as run 122's winner. Idea 2 carries forward to run 123 (2nd carry-forward) → autonomous-executable at run 124.

---

## Idea 3 — File P0 GH Issue for Credential Rotation

**FOR:**
- Immediate escalation: filing a P0-labeled issue provides visibility now, before the 10-day tier of Idea 1 even fires.
- Low risk: just a GH issue creation, no SKILL.md changes.
- Addresses AUTOPILOT_GH_TOKEN + Brain PAT rotation in the same action.

**AGAINST:**
- Step 9E already added a comment to GH #399 yesterday with the staleness warning. The existing tracking issue has the information.
- Idea 1, if implemented, will create the P0 issue automatically in ~4 days when the 10-day tier fires. Manual filing now duplicates what the automated system will do.
- One-time operational action vs. systemic fix: Idea 1 is categorically superior.

**VERDICT: WEAKENED → Bonus action.** File as part of this run's output but don't call it the winner. Idea 1 covers this permanently.

---

## Winner

**Idea 1 — Step 9E 10-Day P0 Escalation Tier**

Single binding reason: governance protocol mandates autonomous execution at 3rd consecutive carry-forward. This is run 122, which is the 3rd carry (runs 119 identified → 120 first carry → 121 second carry → 122 = execute). The implementation is XS effort, high confidence, systemic scope, and operationally urgent given AUTOPILOT_GH_TOKEN expiring in 14 days.
