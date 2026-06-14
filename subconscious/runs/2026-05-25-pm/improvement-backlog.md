# Improvement Backlog — 2026-05-25-pm (Run 33)

## Active

- **Create `god-class-splitter` skill** — `.claude/skills/god-class-splitter/SKILL.md`, 12-step checklist for splitting god-class files. Execution arm for `improve-architecture`. Prevents post-split follow-up commits. 54 remaining files in `plans/god-class-refactor_plan.md`. LOW-risk additive, nightly review can create autonomously.

## Parking Lot (survived debate but not chosen this run)

- **Fix GH #181 — AMOUNT_TO_PLAN billing gap** — Add `15000: "autopilot"` and `25000: "professional"` to `billing.py:264`. Remove inverted test methods at `test_billing_amount_to_plan.py:38-44`. S-effort ~15 min. Most urgent human action. RUN 34 ESCALATION: if still unimplemented by run 34, governance mandate fires — winner must switch away from GH #181.
- **Create `billing-constant-guard` skill** — 10-step checklist including CLAUDE.md cross-reference + inverted-test check. Root cause fix for recurring billing constant regressions. Promote to winner after GH #181 is fixed and god-class-splitter is created.
- **Create `post-split-test-repair` skill** — 8-step checklist for repointing stale @patch targets and imports after module splits. Can also be implemented as Step 11.5 of god-class-splitter. Promote once god-class-splitter is implemented and first use reveals whether standalone skill is needed.
- **Update `improve-architecture` SKILL.md** — Add execution handoff step: "For CRITICAL files, immediately invoke god-class-splitter for top-ranked file." Bonus step alongside god-class-splitter creation.
- **/moratorium-sprint Items A+B+D** — check_project_invariants pre-commit (~5 min), widget sync guard (~15 min), CI eval workflow (~20 min). Moratorium day 20+. Standing highest-leverage sprint. SKILL.md ready (7985fbb).
- **Zapier API key plan_status enforcement** — GH #107, backend/services/zapier_auth.py. Cancelled tenants bypass tier gate. ROI 2.5, security. First post-moratorium winner candidate.
- **Fix email sequences N+1 queries** — GH #112. 1001 queries per 1000 enrollments. Bulk .in_() fix. Promote when email adoption grows.
- **AI-to-Human Handoff v1** — GH issue mechanism 3x recommended without action, demoted to parking lot. Promote post-moratorium.

## Rejected This Run

- **billing-constant-guard as run 33 winner** — WEAKENED: narrower scope (yearly pricing changes vs weekly god-class splits), lower recurrence frequency. Stays in parking lot.
- **post-split-test-repair as standalone winner** — Not debated: better as sub-step of god-class-splitter or promoted after god-class-splitter is used once in practice.

## Questions for Next Run

1. Was `god-class-splitter` SKILL.md created? (autonomously by nightly review, or by human action)
2. Was GH #181 implemented? (run 34 governance threshold: 4-consecutive-run mandate fires if not)
3. Which of the 54 remaining files from `plans/god-class-refactor_plan.md` has the highest priority for the next split sprint?
4. Has `post-split-test-repair` been needed as standalone workflow, or is it covered by god-class-splitter Step 11.5?
