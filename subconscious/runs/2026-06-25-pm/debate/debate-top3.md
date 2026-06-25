# Debate — Top 3 Candidates

Run: 2026-06-25-pm (run 67)
Debating: Idea 01 vs Idea 02 vs Idea 04

---

## Candidate A: Idea 01 — Execute Run 65 Steps + Step 9B in Interactive Session

**Evidence for:**
- check_project_invariants.py exits 1 (confirmed this run)
- Mandate from run 65 fires explicitly: "escalate to interactive human execution"
- Root cause of delivery failure is scope mismatch (cp + text replacement not in nightly scope)
- Adding Step 9B to nightly SKILL.md requires editing EXISTING file — also not in scope
- Interactive session resolves both in ~10 minutes: cp + 10 sed + SKILL.md edit
- Precedent: every SKILL.md scope extension delivered in 1 nightly cycle once properly done
- No further layers of abstraction needed

**Evidence against:**
- Requires human attention (blocks on human to schedule)
- If human delays, invariant keeps failing and blocking commits

**Risk:** LOW — concrete, well-understood, tested by prior runs 58/62/63

---

## Candidate B: Idea 02 — Extend Nightly Scope (meta-fix layer)

**Evidence for:**
- Would make delivery truly autonomous for broader fix class
- Reduces future human intervention

**Evidence against:**
- Explicitly forbidden by run 65 mandate: "Do NOT add yet another layer of meta-fixes"
- Runs 65 → 66 → 67 have each added a meta-fix layer (AUTONOMOUS-EXECUTABLE label → Step 9B → ???)
- Each layer delayed delivery by 1 cycle
- Pattern has failed 2 consecutive times
- Would be run 68 at earliest, meaning invariant fails for 4+ more cycles

**Verdict: ELIMINATED** — mandate forbids this path

---

## Candidate C: Idea 04 — Plan-Name Invariant Guard (Check 7)

**Evidence for:**
- High ROI (prevents GH #292/#293-class bugs at repricing time)
- AUTONOMOUS-EXECUTABLE (clean implementation, 20 lines)
- No human required once Check 13 exits 0

**Evidence against:**
- BLOCKED: cannot add to check_project_invariants.py while it currently exits 1
  Adding a new check to a failing script masks signal and creates confusion
- Moratorium is active — subconscious should not add new pending items this run
  unless mandated or critical
- This is a PARKING LOT item, not this run's winner

**Verdict: PARKING LOT** — run 68 candidate, after run 65 fix lands

---

## Winner: Candidate A — Idea 01

Mandate fires. Delivery chain broken for 2 cycles. Root cause confirmed.
Interactive session is the correct path.

**No dissenting opinion.** Evidence is unambiguous. Three meta-fix layers
have already delayed this. The fix is a cp command and 10 text replacements.
