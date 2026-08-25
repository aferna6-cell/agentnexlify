# Debate Log — Run 111 (2026-08-25-pm)

Top 3 debated: Idea 1 (pre-commit hook), Idea 2 (Step 9J escalation), Idea 3 (annual plan guard).

---

## Round 1: Idea 1 — Pre-commit block_demo_role detection hook

**CHALLENGE:**
- M-effort — requires writing a new shell script, wiring it into install-hooks.sh and testing. Not implementable autonomously by nightly review.
- The nightly Step 9I already catches missing guards dynamically. The lag is 12-36h, not years — is prevention worth the engineering cost?
- Pre-commit hooks are bypassable with `--no-verify`. Determined developers can skip it.
- The codebase already has 97 missing guards (GH #669) — the preventive hook doesn't fix the existing backlog.

**DEFEND:**
- M-effort is still S-M — it's one shell script + two config lines. Subconscious recommends, human implements. 2-4h of work.
- Step 9I detection lag: partners.py was committed today in a 46-file sprint. It won't be detected until the 2026-08-26 nightly. In that window, the endpoint is live with a missing guard. Shift-left to commit time closes this window to zero.
- Yes, `--no-verify` exists. But the hook's purpose is DEFAULT friction — it stops accidental omission (like billing_addons.py vs partners.py in the same sprint). It's not a hard security barrier; it's a reminder.
- The 97-router backlog doesn't diminish the value of preventing the 98th+. Compounding regressions cost more than the hook.

**VERDICT:** SURVIVES. Shift-left security is a real principle. The evidence (partners.py committed without guard in same sprint as correctly-guarded billing_addons.py) proves this is an accidental omission problem, not a deliberate bypass. A reminder hook catches accidents.

---

## Round 2: Idea 2 — Step 9J consecutive-0-merge escalation

**CHALLENGE:**
- Step 9J already logs clearly: "0 PRs merged. All minor/patch candidates have `mergeable_state: "unknown"`. No action taken." The human reading nightly logs can see the situation.
- GH #500 already tracks GH Actions being dark. A new issue saying "Dependabot auto-merge blocked" is noise on top of GH #500.
- Autonomous-executable is a nice property, but adding it to SKILL.md just to file a GH issue that duplicates GH #500 content doesn't add compounding value.
- Consecutive-night tracking requires Step 9J to read and write state between runs. SKILL.md steps are stateless by design.

**DEFEND:**
- GH #500 tracks "Actions dark" at the general level. A specific issue "Dependabot auto-merge blocked: 22d PRs aging" surfaces the COST with specific PR numbers, ages, and impact. Different audience hook.
- The stateless concern is real — consecutive-night tracking needs a file. But the check could be simpler: "if Step 9J merges 0 PRs AND all candidates have `mergeable_state: unknown` AND total aging Dependabot PRs > 5 → check for existing Dependabot-block issue → file if absent." Single-night trigger, no state.
- But... GH #500 is already the right place. A separate issue creates fragmentation.

**VERDICT:** WEAKENED. The observability goal is valid, but GH #500 is the right tracker. If Step 9J's 0-merge streak matters, a comment on GH #500 is more appropriate than a new issue. This idea is useful but not the most impactful winner. Parking lot: Step 9J comment on GH #500 after N consecutive 0-merge nights.

---

## Round 3: Idea 3 — Annual plan guard consistency check

**CHALLENGE:**
- XS-effort, but it's a one-time diagnostic, not a systemic improvement. The subconscious recommends, then humans act. But if humans don't act on prior recommendations (GH #403, #669, #399), why would they act on this?
- The test suite (test_billing_annual.py — 386 lines) presumably catches misclassification of annual subscribers. If tests pass in CI, the guard is probably consistent.
- The annual plan is brand-new (10acf83 today). No tenants are on it yet. The risk window before any annual subscriber signs up might be days or weeks.
- XS effort recommendations get lost in the noise without a concrete blocking scenario.

**DEFEND:**
- Valid counterpoint: test coverage. But test_billing_annual.py tests billing flow, not necessarily the ai_usage_guard.py token-limit classification. These are separate systems — a subscriber could pass billing tests but hit free-tier limits.
- Revenue impact: annual plans are typically the highest-LTV customers ($99.99 × 12 = $1,199/yr vs $99.99/mo). Misclassifying them as free-tier on day 1 is a severe revenue/trust failure.
- XS-effort is the point — the diagnostic takes 10 minutes to run, and if it finds an issue, it becomes a blocker before any annual subscribers convert.
- Timing: 10acf83 landed TODAY. This is exactly when to audit it.

**VERDICT:** SURVIVES but as BONUS A (not winner). Strong case for correctness, but XS one-time audit doesn't match the compounding-value criterion as well as a systemic fix.

---

## Synthesis

| Idea | Verdict | Rationale |
|------|---------|-----------|
| Pre-commit block_demo_role hook | **WINNER** | Shift-left prevention, concrete evidence, systemic, not in rejected/frozen, M-effort justified by GH #669's 97-violation lesson |
| Step 9J escalation | WEAKENED → parking lot | GH #500 is right tracker; fragmentation risk |
| Annual plan guard audit | BONUS A | XS, do alongside winner; low downside if wrong |
| Step 9J merge threshold lowering | KILLED | Policy decision outside subconscious scope; HIGH merge risk |
| Step 9D GH Actions dark escalation | PARKING LOT | Valid but less urgent than winner; revisit run 112 |
