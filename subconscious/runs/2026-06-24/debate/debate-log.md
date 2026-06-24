# Debate Log — Run 65 (2026-06-24)

## Candidates
- **A**: Idea 1 — Add localStorage detection to post-edit hook
- **B**: Idea 2 — Write AI-to-human handoff PRD/spec
- **C**: Idea 3 — In-widget referral prompt post-conversion

---

## Round 1: A vs B

### FOR A (localStorage hook)
- Closes the last unautomated CLAUDE.md critical invariant. Invariants #1–#4 now automated; #6 is the only gap.
- 8 lines of shell in one existing file. No ambiguity, no dependencies, fully reviewable in under 5 minutes.
- Directly extends the momentum from 3eaf702 (4 invariant checks added) and c8f1bde (em-dash fix) — two consecutive commits improving the same system. A third completes it.
- Permanent compounding value: every future frontend edit gets automatic localStorage protection. One fix, perpetual enforcement.
- localStorage in claude.ai artifact sandbox is a REAL failure mode documented in CLAUDE.md, not theoretical. The invariant exists because it was a past bug.

### AGAINST A
- localStorage violations are rare in this codebase — a post-edit warning prevents a low-frequency bug.
- Doesn't address the "buildable backlog exhausted" signal, which is the most urgent structural gap.

### FOR B (AI-to-human handoff PRD)
- Brain explicitly flagged "buildable backlog exhausted" after #367. Without a new spec, the product stalls — there's nothing to build toward.
- AI-to-human handoff is the only customer gap marked "Critical, all industries" in `docs/dev-knowledge/customer-gaps.md`. Affects all 13 verticals.
- Writing the spec IS the unlock — the build sprint can't start without it. Recommending the spec now means the next interactive session can execute immediately.
- GoHighLevel ($97–497/mo) already has AI-to-human escalation. Every month without it = competitive gap.

### AGAINST B
- Spec writing is a PLANNING action, not a direct code improvement. The subconscious loop's strongest recommendations have been implementable changes, not planning documents.
- Spec writing needs user-interactive grill-me/write-prd to be done correctly. An autonomous loop can't write a good spec — it needs the 40+ clarifying questions answered first.
- "Buildable backlog exhausted" means the automated build loop ran out of pre-approved issues, not that the human is out of ideas. The subconscious loop should surface the direction; the grill-me session fleshes it out.

**Round 1 result: A advances. B goes to improvement-backlog as the highest-priority recommendation for the next interactive session.**

---

## Round 2: A vs C

### FOR C (referral widget prompt)
- Referral pipeline is COMPLETE through #371 (attribution, admin, notifications, weekly digest). The infrastructure is idle.
- Post-conversion is the highest-intent moment in the user journey. Asking for a referral right after "your appointment is booked" is timing gold.
- Revenue impact: referral conversions compound. Even 2 new tenants/month via referral = $40-$200/mo recurring, growing.
- The pipeline being built and not activated is pure waste — every day without the prompt is a missed conversion.

### AGAINST C
- Widget change requires byte-identical copy to two locations — higher execution risk than a shell script change.
- Requires a new `/api/referrals/my-link` endpoint — not a one-file change.
- The timing of referral ask (immediately after form submit) could feel pushy and reduce the quality of the conversion moment itself.
- Referral activation doesn't have to happen this cycle — the pipeline isn't decaying, it's just idle.

### FOR A (localStorage hook) — final defense
- True single-file change. No byte-identical requirement. No new API endpoint. No UX risk.
- Automation > activation for this loop. The subconscious loop's strongest comparative advantage is identifying gaps in automated protection — not product activation decisions that need UX judgment.
- The localStorage gap is the ONLY automated protection gap remaining in the 6-invariant list. Closing it is a clean categorical improvement.
- Referral activation belongs in a dedicated session with UX review; this run shouldn't shortcut that.

**Round 2 result: A wins. C goes to improvement-backlog.**

---

## Final verdict

**Winner: Idea 1 — Add localStorage detection to post-edit hook**

**Rationale:**
1. Only remaining unautomated CLAUDE.md critical invariant
2. Most atomic candidate — 8 lines, one file, one PR
3. Natural continuation of 3eaf702 + c8f1bde momentum
4. Permanent protection; no UX risk; no new dependencies
5. The subconscious loop excels at automation gaps — this is the canonical case

**Backlog order:**
1. B (AI-to-human handoff PRD) — next interactive session via `/write-prd`
2. C (referral widget prompt) — next widget sprint
3. D (Vercel deploy quota) — ops sprint, any session
4. E (vertical KB seeding) — content sprint, any session
