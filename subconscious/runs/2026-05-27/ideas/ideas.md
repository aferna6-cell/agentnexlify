# Candidate Ideas — Run 36 (2026-05-27)

Evidence base: zero production commits 3 days, moratorium day 23, email_sequences.py 1255L (run 35 winner, day 2), PR #182 draft 4+ days, 5 MEDIUM/HIGH bugs 30+ days open (never been winner), skill-discovery 2026-05-25 flagged post-split-test-repair (ROI 1.9, 2 follow-up repair commits this week).

---

### Idea 1: Create post-split-test-repair SKILL.md

**Evidence:** skill-discovery 2026-05-25 explicitly proposed it as top-ranked new skill. `5f2cd2b` ("test: repoint stale patch targets and imports after refactor") repaired 21 stale patch targets across 4 test files — required because local_seo split (`3555645`) didn't update `@patch` decorators. `4afb3cf` ("Fix test_local_seo_parsers import") was a second follow-up for the same class of problem. Both commits happened within hours of the split, confirming the pattern is predictable. PR #182 (invoices.py split, currently Draft) will require the same repair if any test files import from the old module path. email_sequences.py split (run 35 winner) will also generate this follow-up. Parking lot ROI 1.9 — promoted twice but never been a winner.

**Action:** Create `.claude/skills/post-split-test-repair/SKILL.md` — 8-step workflow: (1) run pytest to capture first failure, (2) identify old module path in error, (3) grep all test files for old path, (4) determine new canonical paths, (5) update `@patch` decorators, (6) update `from ... import` statements, (7) re-run pytest until green, (8) commit as `test: repoint stale patch targets after <split-name> refactor`.

**Impact:** 15–20 min saved per god-class split. Prevents the systematic 2-commit waste (split commit + repair commit). Makes email_sequences split (run 35 winner) cleaner when executed — the repair step is encoded before the split happens, not discovered after. Autonomously executable by nightly review (pure new .md file = LOW-risk, same class as god-class-splitter created by e848b87).

**Category:** workflow

---

### Idea 2: Re-confirm email_sequences.py split (run 35 winner, day 2 — higher confidence)

**Evidence:** email_sequences.py confirmed 1255L. Run 35 said "if not done, stands for run 36 with higher confidence." Three independent concerns confirmed: CRUD (lines 60–728), enrollment (lines 105–253), processor (lines 875–1088 + 1234). god-class-splitter SKILL.md ready (e848b87). PR #182 (invoices.py) is the first production use of the skill — reviewing it provides a concrete pattern for email_sequences. GH #112 (N+1) and GH #113 (duplicate processor loop) both easier to fix post-split.

**Action:** Execute `/god-class-splitter email_sequences.py` — pre-requisite: fix GH #181 (~15 min), then 2h interactive session. Optionally: merge/review PR #182 first to validate the workflow before the larger split.

**Impact:** Reduces 1255L god-class to 3 focused modules (~400/300/300L each). Unblocks GH #112/#113 fixes. Establishes split pattern for remaining 54 god-class targets in plans/god-class-refactor_plan.md.

**Category:** code_health

---

### Idea 3: Fix GH #93 — guard_checkout_for_fraud flags no_payment_required as fraud (HIGH bug, 31 days)

**Evidence:** GH #93 open 31 days. Nightly review 2026-05-27 carry-forward list: "bug(billing): guard_checkout_for_fraud flags no_payment_required as fraud — HIGH." `no_payment_required` is a valid Stripe payment intent status for free/trial subscriptions. The guard treating it as fraud would: (a) block legitimate Stripe webhook events, (b) potentially cause silent false-positives for free/trial tenants. This bug has never been a subconscious winner — 35 runs have focused on GH #181 and god-class refactors without addressing this older billing bug.

**Action:** Read `backend/routers/billing.py::guard_checkout_for_fraud`. Identify the no_payment_required handling. Add explicit allowlist for valid zero-payment statuses. Write regression test that seeds a no_payment_required event and asserts it passes the guard.

**Impact:** Fixes live HIGH-severity bug blocking legitimate free/trial Stripe events. Clears 31-day-old issue. Different mechanism from GH #181 (guard logic vs constant mapping) — not the same recommendation loop.

**Category:** code_health

---

### Idea 4: Review PR #182 (invoices.py god-class split) against god-class-splitter 12-step checklist

**Evidence:** PR #182 (invoices.py split) is Draft, 4+ days open. Nightly review 2026-05-27 explicitly flagged: "verify against god-class-splitter 12-step checklist before merge (Steps 6, 9, 10, 11 specifically — stale importers, pytest count unchanged, no stale module refs, smoke tests present)." This is the first production use of god-class-splitter skill (e848b87). Merging it unblocked = clears a pending item, provides a validated pattern for email_sequences split, and proves the 12-step checklist works in practice.

**Action:** Read PR #182 diff. Verify Steps 6 (no stale importers), 9 (pytest count unchanged from baseline), 10 (no stale module refs in grep), 11 (smoke tests present). If checklist passes → approve/merge. If gaps → note them and fix in-place.

**Impact:** Clears one pending item. Validates god-class-splitter workflow before email_sequences split. ~30–60 min review. Autonomously executable by nightly review (read + comment = LOW-risk).

**Category:** code_health / operational

---

### Idea 5: Create billing-constant-guard SKILL.md (nightly-executable, unblocks post-GH#181 guard)

**Evidence:** Parking lot ROI 2.1. Promoted in run 35 debate (SURVIVES weakened). skill-discovery 2026-05-25 proposed it. The triple-fix pattern (c72b535, 1eaaeec, GH #181 still open) shows the workflow lacks a checklist. Specifically: "check for inverted tests" step was missed twice. Pre-commit Check 11 is BLOCKED on GH #181 fix, but the SKILL.md itself (a checklist for billing-constant fixes) can be created NOW — independent of whether GH #181 is fixed. The skill encodes the "find inverted test assertions" step that was the non-obvious failure mode.

**Action:** Create `.claude/skills/billing-constant-guard/SKILL.md` — 10-step checklist for billing constant fixes: read AMOUNT_TO_PLAN vs CLAUDE.md plan table, identify missing/wrong entries, check for inverted test assertions (`X NOT IN` when `X` should be present), fix dict + tests, add parametric contract tests, verify CI wiring. Distinct from pre-commit Check 11 (that requires GH #181 first; this skill does not).

**Impact:** Prevents next billing-constant-fixing session from repeating the triple-fix pattern. Encodes the "inverted test" diagnostic step that was missed twice. Autonomously executable by nightly review (pure .md file). ~15 min effort.

**Category:** workflow
