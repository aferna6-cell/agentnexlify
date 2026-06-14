# Improvement Backlog — 2026-05-28-pm (Run 38)

## Active

- **AI-to-Human Handoff v1 via Agent OS outbound** — detect explicit handoff triggers in `widget_chat.py`, write to `handoff_requests` table, notify owner via `os_outbound_mirror.send_sms()` / `send_email()`. ~1 day. MEDIUM confidence. New evidence: PR #188 ships the delivery layer.

## Bonus Action (from Run 37 — do first, 3 min)

- **billing-constant-guard Check 11** — add 10-line bash WARNING block to `scripts/hooks/pre-commit`. Code ready in `subconscious/runs/2026-05-28/winning-concept.md §Step 1`. Autonomous channel failed twice; human-session execution only path.

## Standing Actions (priority order)

1. **GH #181 billing fix (~15 min, human required)** — `billing.py` add `15000: "autopilot"` + `25000: "professional"`; fix backwards test assertions in `test_billing_amount_to_plan.py:38-44`. Prerequisite for handoff sprint.
2. **Invoke /moratorium-sprint (~40 min)** — Items A (check_project_invariants), B (widget sync guard), D (CI eval). Moratorium exits after 24+ days.
3. **email_sequences.py split (~2h, run 35 winner)** — invoke `/god-class-splitter email_sequences.py`. After GH #181 fix.
4. **post-split-test-repair SKILL.md (~5 min)** — create `.claude/skills/post-split-test-repair/SKILL.md`. Content in `subconscious/runs/2026-05-27/winning-concept.md`.

## Parking Lot (survived debate but not chosen)

- **Invoke /moratorium-sprint** — 13 consecutive recommendations without invocation; mechanism uncertain. Still valid; demoted to standing action.
- **post-split-test-repair SKILL.md** — 100% recurrence rate on splits; 54 files in backlog; ~18h total savings. Promote to run 39 if handoff sprint done.
- **email_sequences.py god-class split** — standing active_direction from run 35. First production use of god-class-splitter. Prerequisite: GH #181 fix.
- **Onboarding V2 characterization tests** — ROI 1.7, plans/onboarding-v2_plan.md. Revisit before first sprint issue.
- **Zapier API key plan_status enforcement** — GH #107, ROI 2.5, HIGH security. First post-moratorium winner candidate.
- **Fix email N+1 queries** — GH #112/#113. ROI 2.3. Simpler post email_sequences split.
- **Widget Hot-Zone Regression Suite** — ROI 2.1. Playwright infra unconfirmed.

## Rejected This Run

- **billing-constant-guard as winner** — duplicate of run 37 winner already in active_directions; demoted to Bonus Action to avoid governance noise.
- **Invoke /moratorium-sprint as winner** — 13 consecutive recs without invocation (runs 25-37); mechanism broken; demoted to standing action footnote.

## Questions for Next Run

1. Was billing-constant-guard Check 11 added to `scripts/hooks/pre-commit`? (grep for "Check 11")
2. Was GH #181 fixed? (`grep "15000\|25000" backend/routers/billing.py`)
3. Was AI-to-Human Handoff v1 sprint started? (`ls backend/services/handoff_service.py`)
4. Was email_sequences.py split? (`wc -l backend/routers/email_sequences.py` — should be <600L if done)
5. Were any Agent OS regressions detected in nightly reviews post-PR #188?
6. Was /moratorium-sprint invoked? (`grep "check_project_invariants" scripts/hooks/pre-commit`)
