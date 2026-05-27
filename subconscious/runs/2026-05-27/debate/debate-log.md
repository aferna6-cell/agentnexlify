# Debate Log — Run 36 (2026-05-27)

Top 3 ideas debated: Idea 1 (post-split-test-repair SKILL.md), Idea 3 (GH #93 billing fraud fix), Idea 2 (email_sequences split re-confirmation).

---

## Idea 1: Create post-split-test-repair SKILL.md

### Round 1 Challenge
**Attack:** This skill is a support tool for god-class splits that haven't happened yet. god-class-splitter was just created yesterday (e848b87). Creating post-split-test-repair before even running email_sequences split is premature — the skill's value only materializes after a split produces stale patch targets. Why recommend a meta-improvement over the actual work?

**Defend:** The pattern isn't premature — it's already happened twice this week WITHOUT the skill (5f2cd2b, 4afb3cf). god-class-splitter was created before email_sequences split specifically to make the split more reliable — that's the same logic. The subconscious's working implementation channel for the last 3 runs has been LOW-risk autonomous nightly review items (7985fbb moratorium-sprint SKILL.md, 2ce31b2 escalation protocol SKILL.md, e848b87 god-class-splitter SKILL.md). This fits that exact pattern. Recommending email_sequences split (MEDIUM-risk, 2h human) for the 2nd consecutive run when the human hasn't acted in 3 days has diminishing returns; recommending something the nightly review CAN execute has compounding returns.

### Round 2 Challenge
**Attack:** The subconscious should recommend the highest-value improvement, not the easiest-to-implement one. Optimizing for "nightly review can do it" creates a selection bias toward LOW-value, LOW-risk items while MEDIUM-value items like email_sequences split or GH #93 never get acted on. The moratorium is ACTIVE with 10 pending items — adding another pending item (even LOW-risk) makes it worse.

**Defend:** A key distinction: post-split-test-repair is NOT a human-approval-required item. It's nightly-executable. It does NOT add to pending_approvals count because nightly review autonomously executes LOW-risk skill creations without human gate. The moratorium's "pending_approvals" counter tracks items waiting on human — this doesn't. Evidence: god-class-splitter was created autonomously by nightly review and its governance entry says "status: implemented" (not "pending_approval"). Same outcome predicted here.

Additionally: the impact compounds. 29 backend files and 25 frontend files exceed 600 lines (per god-class-refactor_plan.md). Each split will need a post-split-test-repair pass. Creating the skill NOW encodes the checklist before email_sequences split runs, preventing the predictable follow-up commit.

### Round 3 Challenge
**Attack:** Is the evidence strong enough? Only 2 repair commits this week. Is that sufficient to justify a dedicated skill? Could this be a sub-step of god-class-splitter (step 11.5) instead of a standalone skill?

**Defend:** 2 repair commits in ONE week — 100% recurrence rate, on every split. skill-discovery 2026-05-25 explicitly flagged both commits and proposed the skill. The skill-discovery report noted: "Consider whether it should be a sub-step of god-class-splitter (step 11.5) rather than a standalone skill. Standalone is better if the repair needs to run days after the split when test drift compounds." For email_sequences.py (which has 1255L and is likely imported by multiple test files), the repair will almost certainly require a separate commit hours or days after the split — making standalone the right choice.

**Verdict: SURVIVES** — Evidence is strong (100% recurrence rate, explicit skill-discovery proposal), moratorium-safe (nightly-executable, no human-approval gate), compounding value (29+ future splits ahead).

---

## Idea 3: Fix GH #93 — guard_checkout_for_fraud false-positive (HIGH, 31 days)

### Round 1 Challenge
**Attack:** GH #93 is a billing/payments bug — the same risk category as GH #181 (also billing, also MEDIUM). The recommendation loop for billing bugs is what exhausted the subconscious at run 35 (5-consecutive GH #181, moved to rejected_paths). Picking another billing bug as the winner immediately after GH #181 was exhausted suggests the subconscious is circling the same category without new insight.

**Defend:** GH #93 is a DIFFERENT mechanism: guard_checkout_for_fraud logic error (allowlist for no_payment_required), not a missing AMOUNT_TO_PLAN dict entry. They're in the same FILE (billing.py) but different functions. The HIGH severity distinguishes it from GH #181's MEDIUM. The risk profile for false-positive fraud detection is customer-blocking (legitimate Stripe events rejected), vs GH #181's silent downgrade risk.

### Round 2 Challenge
**Attack:** HIGH severity doesn't change the execution dynamics. GH #93 is still MEDIUM-risk code requiring human approval. The pattern is identical: recommend billing fix → human doesn't implement → recommendation ages → repeat. The reason human isn't implementing billing fixes isn't priority — it's that billing code is psychologically heavier to touch than skill files. GH #93 would become the 11th pending item.

**Defend:** The argument applies to ALL human-required items, not just billing. By this logic, no MEDIUM-risk item should ever be recommended. But the subconscious's job is to identify highest-value improvements, not only LOW-risk ones. GH #93 has been open 31 days and never been the winner — it deserves its turn in the debate.

### Round 3 Challenge
**Attack:** Even if we accept the recommendation, what's the implementation sketch? Reading guard_checkout_for_fraud and figuring out the right fix requires code context we don't have in this run. The subconscious brief says "Evidence first — no recommendations without supporting data." We haven't read billing.py:guard_checkout_for_fraud in this run. The recommendation would be speculation about the fix.

**Defend:** The recommendation doesn't need to contain the full fix — it needs to identify the problem and point to the action. GH #93 is already filed with the problem description. The implementation sketch can say: "Read guard_checkout_for_fraud, add no_payment_required to valid status allowlist, write regression test." That's specific enough for an executor.

**But the critical flaw:** The moratorium condition (max_pending_approvals = 2, actual pending = 10) argues strongly against adding a new human-required item. GH #93 fix requires human approval. Adding it as the winner increases the pending count — wrong direction.

**Verdict: KILLED** — Billing code + human-required + moratorium active + no new execution mechanism = same failure pattern as GH #181. Demoted to parking lot. Evidence supports filing it as a priority issue but NOT as the subconscious winner in moratorium conditions.

---

## Idea 2: Email sequences split re-confirmation (run 35 winner, day 2)

### Round 1 Challenge
**Attack:** Re-confirming a winner from the previous run is low-information. The human didn't act in 2 days — what new evidence does run 36 add? If the answer is "nothing new," the recommendation is equivalent to repeating it until the human acts, which is exactly the behavior that sent GH #181 to rejected_paths after 5 consecutive runs.

**Defend:** Run 35 explicitly documented: "if the session doesn't complete the split, the recommendation stands for run 36 with higher confidence." This was the plan from the start. It's normal for MEDIUM-risk items to require 1–2 runs before a human acts (vs GH #181 which required 5 runs — different failure mode). New context for run 36: PR #182 (invoices.py) is 4+ days old and has checklist gaps — reviewing it first provides a validated pattern. This is new actionable information.

### Round 2 Challenge
**Attack:** The "review PR #182 first" insight is a sub-task of the email_sequences split, not a new recommendation. The subconscious should recommend ONE thing. "Review PR #182 AND then do email_sequences split" is two things.

**Defend:** Fair point. The PR #182 review could be made the explicit winner (Idea 4) rather than a sub-step of email_sequences. But email_sequences split is still the HIGHER value recommendation — PR #182 review is operational scaffolding.

### Round 3 Challenge
**Attack:** Compare directly against Idea 1. Both survive to round 3. Idea 1 (post-split-test-repair) is autonomously executable — will almost certainly be implemented by tomorrow's nightly review. Idea 2 (email_sequences split) requires 2h human session — uncertain implementation timeline given 3 days of no production commits. Which recommendation compounds more reliably?

**Defend:** The subconscious shouldn't only recommend what gets implemented easily. email_sequences split is higher total value (1255L → 3 clean modules, unblocks GH #112/#113). Post-split-test-repair is complementary but secondary. The right winner is the highest-value improvement, even if it requires human activation.

**Counter:** HOWEVER — the moratorium condition overrides. max_pending_approvals = 2, actual = 10. Re-confirming a human-required item that's already in active_directions doesn't ADD a new pending item (it's already there), but it also doesn't make progress toward moratorium exit. Idea 1 makes progress (gets implemented autonomously). Idea 2 stays stuck.

**Verdict: WEAKENED** — Natural continuation of run 35 but optimizing for implementation probability in moratorium conditions. Demoted to parking lot for run 36. Stands as the highest-priority recommendation whenever moratorium conditions ease or human signals availability for a 2h session. Active direction entry from run 35 remains valid.

---

## Summary

| Idea | Verdict | Disposition |
|------|---------|-------------|
| Idea 1: post-split-test-repair SKILL.md | SURVIVES → WINNER | Chosen as run 36 winner |
| Idea 3: GH #93 billing fraud fix | KILLED | Parking lot — moratorium active, billing code |
| Idea 2: email_sequences split re-confirm | WEAKENED | Parking lot — run 35 active_direction stands |

**Winner rationale:** post-split-test-repair is the highest-leverage recommendation given current execution conditions. It will be implemented by nightly review (matches the LOW-risk autonomous channel that's been working for 3 consecutive runs). It compounds with all 54+ future god-class splits. It's moratorium-safe (no human-approval gate). It addresses a 100%-recurrence waste pattern identified by skill-discovery evidence.
