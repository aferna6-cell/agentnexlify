# Debate Log — Run 33 (2026-05-25)

Top 3 ideas ranked by impact: Idea 1 (GH #181 billing fix), Idea 2 (auth.py refactor), Idea 3 (invoke /moratorium-sprint).

---

## Idea 1: Fix GH #181 — AMOUNT_TO_PLAN + contradictory tests

### Challenge

**C1: This is the third consecutive run with the exact same winner. If runs 31+32 didn't unlock implementation, why would run 33?**
The governance moratorium pattern (runs 7→18) shows that repeating the same winner 4+ times triggers a mechanism change. Run 33 is run 3. No new forcing function has arrived. The recommendation itself has become part of the furniture.

**C2: The nightly review already handles escalation.** GH #181 is open, documented in full, linked from two winning-concept.md files. Nightly review 2026-05-25 confirmed it's waiting on human approval. What does a third subconscious recommendation add?

**C3: Evidence quality is stale.** Everything this run confirmed is identical to runs 31+32: same missing entries, same contradictory tests, same GH issue. No new data. Run 32's "Questions for Next Run" asked "Has GH #181 been implemented?" — answer is no. The question is answered, but the situation is unchanged.

### Defend

**D1: Three consecutive runs ≠ mechanism failure yet.** Governance precedent fires at FOUR consecutive same-winner runs (runs 15/16/17 triggered the switch at run 18). We're at run 3. The moratorium-sprint analogously was recommended 7+ times before the mechanism changed. The fix itself is uniquely high-urgency: CI is ACTIVELY MISLEADING developers by certifying the broken state as correct. Every day of inaction increases probability of a well-meaning developer reverting any correct fix because CI turns red.

**D2: The CI trap is novel evidence.** Run 31 identified the broken test assertions. Run 32 confirmed 1eaaeec failed to fix it AND that 1553bf7 wired those tests into CI. What is new TODAY: the god-class refactor PR #180 (2174732) merged cleanly, auth.py tests are being added — which means the CI test suite is being actively used by humans RIGHT NOW. A developer working on auth.py will see pr-check.yml pass/fail and trust it. The CI trap is in an actively-watched file.

**D3: S-effort, zero blockers, full sketch exists.** Two consecutive runs wrote detailed implementation sketches (subconscious/runs/2026-05-23/winning-concept.md + 2026-05-23-pm/winning-concept.md). Every field documented. No ambiguity. This is a read-the-recipe, execute situation. The only missing ingredient is 15 minutes of human attention.

### Verdict: **SURVIVES** (narrowly — but CI-trap urgency + third-run is the last soft recommendation before mechanism change)

---

## Idea 2: auth.py god-class refactor

### Challenge

**C1: This is M-effort, not S-effort. The moratorium protocol restricts winners to moratorium-safe items.** auth.py refactor requires architectural decisions about which functions go to which service, new file naming, test coverage for 36+ functions. PR #180 was a 5038-insertion, 2064-deletion refactor that took a full sprint. auth.py refactor is at minimum an M-effort item. Moratorium protocol says oldest pending (run 4, 39 days) should dominate.

**C2: auth.py is a routing file.** Nightly review 2026-05-25 explicitly noted: "auth.py remains at 1590 lines — approaching god-class threshold (600+) — but auth.py is a routing file and has been this size intentionally." The file is intentionally large; it's not the same as branding_service.py (which mixed billing logic, display logic, and data access). auth.py's size reflects the number of endpoints, not a design smell.

**C3: Premature. The god-class refactor just landed.** PR #180 merged two days ago. auth.py wasn't in the first PR because it's higher-risk (authentication logic). Recommending it immediately without a stabilization period violates the principle of "slow is smooth, smooth is fast." New services from PR #180 need to settle before adding more refactor surface.

**C4: No user-reported bug driving it.** Every high-urgency item in the backlog (GH #181, sprint items, AI-to-Human Handoff) has a specific failure mode driving urgency. auth.py refactor is preemptive structural work. The moratorium protocol de-prioritizes preemptive work until oldest-pending items clear.

### Defend

**D1: The timing IS right.** PR #180 established the extraction pattern (router → service modules → test_extracted_services.py). Developers and nightly review are both looking at auth.py with that pattern fresh in mind. If we wait another 6 months, the pattern will need to be re-learned. Strike while the refactor template is warm.

**D2: auth.py has growing surface.** 1590 lines, 36 functions. Every new auth feature (Zapier key plan_status, magic links, Google OAuth v2) makes the blast radius bigger. The sooner it's split, the cheaper the ongoing maintenance.

### Verdict: **WEAKENED** — Valid post-moratorium candidate. Moratorium protocol blocks it as winner today. Route to parking lot with HIGH priority. Promote when sprint exits moratorium.

---

## Idea 3: Invoke /moratorium-sprint (Items A+B+D)

### Challenge

**C1: This has been recommended 10+ times. The bottleneck is not information — it's commitment time (40 min).** Runs 25-28 established that the activation energy of /moratorium-sprint is the problem. Recommending it again is adding to the furniture, not to the solution. The moratorium-sprint SKILL.md exists. The tool is ready. The human knows. Subconscious run 33 saying "invoke /moratorium-sprint" produces the same outcome as runs 25-27.

**C2: Items A and B are lower-urgency than they appear.** Item A (check_project_invariants pre-commit): check_project_invariants.py PASSES all 6 checks today, including widget byte-identical. The invariants are working — they just need a 3-line hook addition for enforcement at commit-time. Item B (check-widget-sync.sh): check_project_invariants.py already catches widget divergence — the standalone script adds redundancy but not new coverage.

**C3: Item D (lead-qualifier-eval.yml) has been pending 20 days.** If CI evaluation was that urgent, it would have been implemented. The harness exists, the golden JSON exists. The lack of urgency signals the onboarding V2 sprint it was meant to protect is stable.

### Defend

**D1: Sprint IS the highest-leverage action.** After sprint: moratorium exits (pending 8→5→2 per governance audit). That unlocks: Zapier security (GH #107, ROI 2.5), AI-to-Human Handoff (Critical, 39 days), free-choice runs. The value of moratorium exit is not the 3 items themselves — it's the unlock of 2 blocked Critical items.

**D2: This is still the correct recommendation for THIS session IF human is present.** The constraint is not "is this worth doing" but "will recommending it produce action." Run 33 is being run interactively (human present). moratorium-sprint can be invoked immediately after this run completes.

### Verdict: **WEAKENED** — Not chosen as winner (10+ recs, commitment bottleneck confirmed). Retains standing as HIGHEST-PRIORITY ACTION if human invokes it immediately post-run. Demoted to Parking Lot for this run's winner slot. If not invoked after run 33: escalate to nightly review as sprint-execution request in run 34.

---

## Synthesis

Three ideas evaluated:
- Idea 1 (GH #181): SURVIVES → **WINNER** — Third consecutive, CI trap urgency, zero blockers, full sketch. Mechanism change fires at run 34 if not implemented.
- Idea 2 (auth.py refactor): WEAKENED → Parking Lot, post-moratorium HIGH priority
- Idea 3 (/moratorium-sprint): WEAKENED → Standing action; escalate to nightly review trigger if still uninvoked after run 33

**RUN 34 MANDATE:** If GH #181 still unimplemented after run 33 (third consecutive same winner), run 34 MUST switch winner mechanism — recommend nightly review autonomous fix (billing.py addition is LOW-risk additive, test change is LOW-risk correction). Governance precedent: four consecutive same-winner runs trigger mechanism change (runs 15/16/17 → run 18 mandate).
