# Ideas — Run 2026-05-22-pm (Run 30)

## Evidence Digest

Three days of commits broke 17 days of silence: billing.py AMOUNT_TO_PLAN had wrong
$150/$250 plan mappings + missing enterprise (c72b535 → 1eaaeec), local_seo_handlers.py
(886 lines) split into execute/fetch modules as god-class template (god-class-refactor_plan.md
now exists with 54 targets), OS plan finalized (Aider removed, effort frontmatter added to
skills). Test suite required 908-line repointing after local_seo split (5f2cd2b). Run 29 winner
(write AI-to-Human Handoff GH issue) NOT implemented — mechanism now 3x recommended
without action. Moratorium day 17, 5 pending, oldest 36 days. /moratorium-sprint still not
invoked.

---

### Idea 1: Billing Constants Contract Tests
**Evidence:** c72b535 fixed AMOUNT_TO_PLAN — $150 and $250 plan mappings were wrong, enterprise entry
missing. These values drive plan identification in every Stripe billing webhook. 1eaaeec
just wired local_seo tests into pr-check.yml, establishing the pattern. billing.py is 906 lines
and explicitly HARD-STOP for refactor (grill-me required), but the AMOUNT_TO_PLAN/PLAN_TO_STRIPE_PRICE
constants can be tested entirely independently with no refactor risk.
**Action:** Create `backend/tests/test_billing_constants.py` — parametric assertions for every
plan name × its documented price in AMOUNT_TO_PLAN + PLAN_TO_STRIPE_PRICE + verify enterprise
present. Add target to `.github/workflows/pr-check.yml`.
**Impact:** Guards against silent billing price regression. S-effort (~20 min). Revenue-critical
scope. Bug class fixed forever.
**Category:** code_health

---

### Idea 2: email_sequences.py God-Class Split
**Evidence:** god-class-refactor_plan.md (created c63888f) ranks email_sequences.py at 1255 lines
as the #3 priority (behind hard-stop auth.py + widget_chat.py). GH #112 (N+1 queries in
list_enrollments — 1001 queries per 1000 enrollments) + GH #113 (process_sequences duplication
~120 lines) both root-cause to the god class. local_seo split provides the reference template.
ROI 2.3 in parking lot since run 13 (2026-05-04).
**Action:** Split into `email_sequences_crud.py` + `email_sequences_enrollment.py` +
`email_sequences_send.py`. Fix N+1 in list_enrollments via bulk `.in_()` as part of the
send module refactor. Green test suite + delete old file.
**Impact:** Closes GH #112 + #113. Removes ROI 2.3 N+1 item from parking lot. Next god-class
domino after local_seo.
**Category:** code_health

---

### Idea 3: Test Patch Path Standard (Prevent Stale Mock Churn)
**Evidence:** 5f2cd2b "test: repoint stale patch targets and imports after refactor" — 908 net
lines across 4 test files manually repointed after the local_seo split. Stale `@patch` targets
(e.g. `backend.services.local_seo_handlers.some_fn`) broke when the module was renamed.
god-class-refactor_plan.md has 54 remaining targets. Without a standard, each split triggers
the same manual repointing cycle.
**Action:** Add section to `docs/dev-knowledge/testing-standards.md` (or `.claude/rules/testing-standards.md`)
defining mock-at-import-site pattern. Reference test_local_seo_handlers.py as canonical example.
Add check to `scripts/check_project_invariants.py`.
**Impact:** Saves ~30 min test-repair per split × 53 remaining files = ~26 hrs avoided. Converts
chore into standard.
**Category:** workflow

---

### Idea 4: models/schemas.py Domain Split (Enable Clean Router Splits)
**Evidence:** god-class-refactor_plan.md lists `models/schemas.py` at 999 lines, calling for
a `schemas/` subdirectory split by domain (leads, billing, appointments, etc.). Every future
router split currently imports from the same monolith — without splitting schemas first, each
router refactor generates import-path churn across multiple files. Schema imports are the
connective tissue for all 54 targets.
**Action:** Create `backend/models/schemas/` directory. Migrate by domain (leads.py, billing.py,
appointments.py, onboarding.py, widget.py). Update all routers to domain imports. Delete
monolith.
**Impact:** Prerequisite unlock for clean future splits. Each subsequent router refactor has
smaller diff scope and less cross-file churn.
**Category:** code_health

---

### Idea 5: AI-to-Human Handoff GH Issue (Mechanism Evaluation)
**Evidence:** Run 21 (2026-05-17) + run 29 (2026-05-21) both recommended writing this GH issue.
Neither was implemented. Run 29 explicitly stated: if not created, "consider freezing the
write GH issue mechanism." Oldest pending item 36 days (run 4). Morning digest 2026-05-22
lists as Priority #2. Human is ACTIVE today (billing fix + local_seo split = production code
moving). Full spec ready: subconscious/runs/2026-05-21-pm/winning-concept.md §Step 1.
**Action:** Create GH issue "feat(widget): AI-to-Human Handoff v1 — explicit trigger" using
full spec from run 29 winning-concept.md.
**Impact:** Resolves runs 4+21+29 pending items. Triggers issue-to-pr-loop pickup for
scaffolding. ~5 min. Moratorium-exempt.
**Category:** customer_value
