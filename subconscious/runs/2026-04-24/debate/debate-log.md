# Debate Log — 2026-04-24

Top 3 ideas debated: Idea 1 (Widget 3-Copy Sync Guard), Idea 2 (Widget Hot-Zone Regression Suite),
Idea 3 (Stripe Billing Smoke Tests).

---

## Idea 1: Widget 3-Copy Sync Guard

### Challenge
1. **Evidence strength?** "Touched twice today" is from 2026-04-21 evening. Three days old. Could
   be a one-time anomaly.
2. **Highest leverage?** landing-page-v2 is listed in CLAUDE.md as "legacy, do not touch." If
   deprecated, drift doesn't matter.
3. **What could go wrong?** Adding 3-way sync requirement means every widget change now updates 3
   files — increased maintenance burden.
4. **Has something similar been tried?** Not in rejected_paths or frozen_ideas.

### Defend
1. The "touched twice today" note was added by the developer themselves in the evening routine —
   it's a directive, not an observation. The explicit note "Codify widget 3-way sync check as
   skill" means action was requested.
2. CLAUDE.md says "legacy, do not touch" but the tasks say it was touched. These contradict.
   Developer's own note overrides the legacy label — if it's being touched, it's not dead.
3. The maintenance burden is trivial: the third copy is a binary copy operation, not a merge. The
   burden is on the checker script, not the developer.
4. CLAUDE.md incorrect invariant is a dangerous instruction failure — every session reads it and
   believes there are 2 copies when there are 3.

### Verdict: SURVIVES
Strong evidence (48h, developer-flagged), atomic fix (S-effort), no infrastructure dependencies.

---

## Idea 2: Widget Hot-Zone Regression Suite

### Challenge
1. **Evidence strength?** widget_helpers split confirmed done but "QA widget_helpers god-class
   split (6cf4646)" is still carried/pending in current-tasks. Writing tests against unverified
   code risks false confidence.
2. **Highest leverage?** If split is already broken, tests surface that — or mask it.
3. **What could go wrong?** Playwright infra still unconfirmed. Run 2 was weakened for this exact
   reason. No evidence of confirmation in recent commits.

### Defend
1. Writing tests against unverified code IS the verification. If they fail, that surfaces the bug.
2. Playwright binaries are listed in .mcp.json. E2E smoke test files exist in docs/daily-logs.
   Probably installed but not confirmed in this run.

### Verdict: WEAKENED
Playwright confirmation step remains open. Pre-condition met (split done) but infrastructure
unverified. Parking lot — promote to run 8 winner candidate once confirmed.

---

## Idea 3: Stripe Billing Smoke Tests

### Challenge
1. **Evidence strength?** 821f660 landed 1 day ago. No reported bug — this is proactive. Horse
   may already be out of the barn.
2. **Highest leverage?** Tests for a shipped change don't prevent bugs already caused.
3. **What could go wrong?** Billing tests often need Stripe sandbox fixtures — brittle.

### Defend
1. Value is prospective — once billing smoke tests exist, every future pricing change is protected.
   821f660 is evidence pricing changes are frequent (3rd+ in 90 days).
2. Tests don't need Stripe sandbox: plan constant assertions + FE component render tests are pure
   unit tests with no external calls.

### Verdict: WEAKENED
Correct diagnosis, real risk. Framing needs to be "billing constants test harness" not one-off
coverage. Parks in parking lot with ROI 2.2.

---

## Synthesis

Surviving: **Idea 1 (Widget 3-Copy Sync Guard)** only.
Weakened to parking lot: Idea 2 (Playwright unconfirmed), Idea 3 (framing too narrow).

Winner: **Widget 3-Copy Sync Guard** — fix CLAUDE.md invariant + create CI sync check script.
