# Improvement Backlog — 2026-05-27 (Run 36)

## Active

- **[Run 36 winner]** Create post-split-test-repair SKILL.md — repoint stale `@patch` decorators after god-class splits. Autonomously executable by nightly review. `HIGH` confidence.
- **[Run 35 standing]** Invoke `/god-class-splitter email_sequences.py` — split 1255L into email_crud + email_enrollment + email_processor. Pre-condition: GH #181 fix first. Human session ~2h.

## Critical Standing Actions (Human Required — Not New Pending Items)

- **GH #181** — billing.py AMOUNT_TO_PLAN missing 15000→autopilot + 25000→professional. ~15 min, S-effort. Do before email_sequences split. `CRITICAL`
- **Moratorium Sprint Items A/B/D** — check_project_invariants pre-commit (~5 min), widget sync guard (~15 min), CI eval workflow (~20 min). Total ~40 min.

## Parking Lot (Survived Debate or Promoted)

- **Review PR #182 against god-class-splitter 12-step checklist** — Steps 6/9/10/11. ~30 min, validates workflow before email_sequences split. Nightly review could do this autonomously.
- **email_sequences N+1 fixes (GH #112/#113)** — Best done after god-class split. N+1 in list_enrollments and duplicate processor loop. Blocked on email_sequences split.
- **Billing-constant-guard SKILL.md** — Parking lot ROI 2.1. Encode "check for inverted tests" checklist. Blocked on GH #181 fix for pre-commit Check 11, but SKILL.md itself is not blocked.
- **GH #93 billing fraud false-positive** — HIGH severity, 31 days open. guard_checkout_for_fraud flags no_payment_required as fraud. KILLED this run (moratorium + billing risk), promote to next post-moratorium window.
- **Zapier plan_status enforcement (GH #107)** — ROI 2.5, security. Promote to first non-moratorium winner.
- **AI-to-Human Handoff v1 (Run 4, 41 days)** — Oldest pending customer-value item. Critical gap all industries. WEAKENED in debate; promote when moratorium exits.
- **post-split-test-repair as god-class-splitter step 11.5** — Consider sub-step consolidation after standalone skill is in production use.

## Rejected This Run

- **GH #93 billing fraud fix as winner** — KILLED. Same execution dynamics as GH #181 (billing code + human-required + moratorium active). Valid item but wrong timing. Parking lot.
- **email_sequences split as run 36 winner** — WEAKENED. Already active_direction from run 35. Moratorium conditions favor autonomously-executable winner. Run 35 entry stands.

## Questions for Next Run

1. Was post-split-test-repair SKILL.md implemented by nightly review (check `git log --since="1 day ago"` for the skill file)?
2. Was GH #181 billing fix implemented? (Check billing.py for 15000+25000 entries.)
3. Was PR #182 merged? (If yes: was email_sequences split started?)
4. Is moratorium still active? Check pending_approvals count vs exit threshold (≤2).
5. Did any of the 30+-day bugs (#93, #94, #97, #98, #99) get addressed by issue-to-pr-loop?
