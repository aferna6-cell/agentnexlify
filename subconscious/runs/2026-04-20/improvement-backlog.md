# Improvement Backlog — 2026-04-20

## Active
- **Migration Duplicate Number Pre-commit Guard** — Add Check 8 to `scripts/hooks/pre-commit` to
  FAIL on duplicate migration numbers ≥106. S-effort, pure bash, zero infrastructure. See
  `winning-concept.md`.

## Parking Lot (survived debate or previously parked)

- **widget_helpers.py Phase 1 Extract — widget_lead_helpers.py** [ROI 2.5] — WEAKENED this run.
  Right idea, import-chain risk too high for standalone atomic recommendation. Execute during a
  dedicated widget sprint where the developer has full context. Unblocked when: (a) widget sprint
  is scoped, (b) characterization tests exist for lead-capture path before extraction.

- **Spec Symbol Validation in feature-build/TDD-workflow Skill** [ROI 2.0] — WEAKENED this run.
  Correct diagnosis (two spec-drift bugs in one day) but wrong mechanism (skill doc update without
  hook enforcement). Revisit with pre-build hook implementation: `python -c "from ..."` + migration
  column grep in feature-build SKILL.md. Needs hook, not just doc.

- **JS Silent Catch Pre-commit Guard** [ROI 2.4] — Run 3 winner, still pending_approval. Add Check
  8 (now reassigned to migration guard — renumber as Check 9) to `scripts/hooks/pre-commit` to emit
  WARNING on `.catch(() => null/{})` in staged JS/TS files. See run 2026-04-11-pm winning-concept.md.

- **AI-to-Human Handoff (Explicit Trigger, v1)** [ROI 3.0] — Run 4 winner, still pending_approval.
  1.5-2 day implementation. Explicit-trigger-only v1. Infrastructure exists: conversations table,
  webhooks, Twilio, Resend. Critical gap in customer-gaps.md (all 7 industries).

- **Widget Click Regression Guard (Playwright E2E)** [ROI 2.0] — BLOCKER: confirm Playwright browser
  binaries installed (`npx playwright install --check`). If confirmed, pick for next code_health run.

- **Onboarding AI Parser Edge Case Tests** [ROI 1.5] — `planning/specs/lead-parser-replacement_spec.md`
  exists. Write tests against parser seam before replacement begins.

- **Managed Agents Automated Integration Tests** [ROI 1.5] — Expand `backend/tests/test_managed_agents.py`
  to cover all 5 HTTP endpoints with mocked Claude API.

- **Migration Safety Net Pre-Push Check** [ROI 1.8] — Add after apply-migration helper exists.

- **Widget Hot-Zone Regression Suite** [ROI 2.1] — Bundle into next widget sprint alongside Phase 1
  extract above.

- **Small Business SaaS KB Category Seed (3 articles)** [ROI 1.5] — `/kb-discover` on 3 SMB queries.
  KB INDEX shows "No articles yet." Good foundation, lower urgency than code_health items.

- **Ingest 5 Competitor Briefs into KB** [Low Effort] — `research-briefs/` has GoHighLevel,
  Drillbit, Birdeye, Oscar Chat, Phonely files. `/kb-ingest` × 5.

## Rejected This Run
_(No ideas killed outright — top 3 all survived or weakened into parking lot.)_

## Questions for Next Run
1. Have any of the 4 pending-approval recommendations (runs 1–4) been approved and implemented? If
   not: should the system surface an "implementation lag" warning — the backlog has 4 unimplemented
   winners, adding a 5th may not be productive.
2. Is Playwright installed in CI? (`npx playwright install --check`) — determines if Widget
   Regression Guard can move from parking lot to candidate.
3. Has the compromised admin API key in Railway been rotated? (current-tasks.md P0, DAY 13). If yes,
   remove from task list. If no, this is a human-action blocker that the subconscious cannot resolve.
4. What is the status of the scheduled_jobs split QA (P1 current-tasks)? If still unverified, the
   next run should evaluate a "QA harness for major refactors" recommendation.
