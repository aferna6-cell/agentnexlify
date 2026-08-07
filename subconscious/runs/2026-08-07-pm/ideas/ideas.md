# Run 103 Ideas — 2026-08-07-pm

## Evidence Base

**Mandate items (run_103_mandate):**
- Item 1: Step 9G amendment in SKILL.md? → NOT YET. Lines 318-319 still have old `Log: "Step 9G: kb-autopopulate triggered — SUCCESS"`. Amendment is recommended in run 102 winning-concept.md but not yet applied.
- Item 2: Next nightly after amendment → N/A (amendment not applied; nightly has not fired it yet)
- Item 3: GH #403 success-but-stale comment → N/A (dependent on amendment application)
- Item 4: KB freshness → PASS. knowledge-base/log.md shows fresh compile today: 114→124 articles (10 new). Step 9G trigger on 2026-08-07 succeeded.
- Item 5: feature-docs-trio skill (parking lot) → PROMOTED to Idea A
- Item 6: grandfathered plan gate audit (parking lot) → PROMOTED to Idea C

**New evidence gathered:**
- `backend/services/response_score.py` (151 lines, shipped in e0e9be6 2026-08-06): ZERO references to `ai_usage_guard`, `check_usage`, `plan_check`, or `block_demo`. Confirmed via grep.
- `backend/routers/insights.py`: only `verify_tenant` present. No plan gate, no demo block.
- e0e9be6 shipped 22 files, 1528 insertions. New LLM-calling service has no plan gating.
- 7 open subconscious draft PRs (none merged). PR pile-up unchanged.
- autopilot-issue-loop stalled 35+ days (AUTOPILOT_GH_TOKEN).

---

## Idea A — feature-docs-trio Skill
**Category:** workflow
**Effort:** S
**Source:** mandate item #5

Create `.claude/skills/feature-docs-trio/SKILL.md` — a skill that auto-generates three lightweight docs when a feature ships with zero documentation: (1) a feature summary for the ops log, (2) a QA checklist, (3) a customer-facing change note. Triggered by nightly when commits have >10 file insertions with no corresponding `docs/` change.

Evidence: e0e9be6 shipped 22 files (Nexlify Score, appointment briefs, daily focus, usage meter, speed stats) with zero docs. 3 occurrences of >10-file features shipping doc-free in the last 7-day window.

---

## Idea B — Appointment Brief AI Usage Guard
**Category:** security/operational
**Effort:** S
**Source:** evidence (grep-confirmed gap on production main)

**Clarified finding (post-read):**
- `response_score.py`: purely deterministic, no LLM — ai_usage_guard not needed.
- `daily_focus.py`: purely deterministic, no LLM — ai_usage_guard not needed.
- **`appointment_brief.py`: calls `call_claude_messages` twice (lines 119, 150) with `BRIEF_MODEL = "claude-sonnet-5"`. ZERO ai_usage_guard, block_demo_role, or plan check in service or router.**

The `appointment_briefs.py` router uses only `_get_current_tenant` (authentication only). Any tenant on any plan — including `chatbot` ($19.99/mo, "widget/chat only") and `free`/lapsed — can trigger two Claude Sonnet 5 calls per brief with no plan enforcement, no demo block, no usage cap.

Parallel: same class as `block_demo_role` missing on `buy-usage` endpoint (nightly-2026-08-07 caught and fixed immediately). That was auth-dimension guard missing; this is plan+demo+usage guards all missing.

---

## Idea C — Grandfathered Plan Gate Audit
**Category:** code health
**Effort:** XS (grep + report)
**Source:** mandate item #6

Grep all plan gate calls in `backend/` for `agent_os` patterns that do NOT include grandfathered plan names (`growth`, `autopilot`, `professional`, `enterprise`). Tenants on grandfathered plans must not be silently blocked from features they're paying for.

Produces a list of gating call sites with missing grandfathered-plan coverage. Actionable as a GH issue → issue-to-pr-loop.

---

## Idea D — Step 9H PR Pile Alerter (Redesigned, Idempotent)
**Category:** operational
**Effort:** XS
**Source:** run 101 mandate (re-raised)

Add Step 9H to nightly-commit-review SKILL.md: when ≥3 open subconscious draft PRs AND last Step 9H alert was >7 days ago (check last GH comment on loop-health issue), post one digest comment listing open PR numbers. Idempotent — does not re-fire on consecutive nights.

Evidence: 7 open subconscious PRs (#606, #611, #613, #626, #629, #630, #631). PR pile-up pattern predates run 100.

---

## Idea E — Nightly ai_usage_guard Scanner (Meta-Prevention)
**Category:** operational/code health
**Effort:** S
**Source:** new pattern from e0e9be6 finding

Add a check to nightly-commit-review SKILL.md that scans new Python files in `backend/services/` and `backend/routers/` for calls to `client.messages.create` or `anthropic.` without a corresponding `ai_usage_guard` or `check_usage` reference. Post finding when gap detected.

Prevents the class of issue found in Idea B from recurring silently. One check catches all future LLM-calling services shipped without plan gating.
