# Post-Audit Remediation Plan

**Source audit:** [../audits/audit-architecture-2026-04-16.md](../audits/audit-architecture-2026-04-16.md)
**Generated:** 2026-04-16 afternoon
**Last updated:** 2026-04-26 — status reconcile vs HEAD
**Scope:** 4 remaining HIGH/MEDIUM items blocked on own sessions per Rule 1 (plan first) + Rule 9 (factor before extending)

## Status (2026-04-26 reconcile)
- Session 1 — DONE. `backend/services/automation_engine.py` thinned to 1.4K wrapper; logic moved to `backend/services/automation/` package (orchestrator, rule_engine, trigger, scheduled_jobs, templates).
- Session 2 — DONE. `backend/routers/analytics.py` replaced by `backend/routers/analytics/` package (dashboard, recovery, control_center, insights, operations, _common). <!-- drift-skip -->
- Session 3 — PARTIAL. `backend/routers/auth.py` shrunk from 1,896 → 1,506 lines, still 2.5x Rule 9's 600-line threshold. **This is the only remaining session.**
- Session 4 — DONE. `backend/routers/widget_helpers.py` reduced to 98-line wrapper.

---

## Why these items aren't in the current session

1. **Collisions on same file.** God-class split + any incremental edit to `automation_engine.py` diverge under parallel work.
2. **Size.** Each split is sprint-sized: 1,500–4,400 line files refactored into 3–5 modules.
3. **Rule 1 (plan first).** User has not approved any of these. Per project rule, no code before plan approval.
4. **Rule 6 (stop mid-task to rethink).** Router "mixed concerns" often hide cross-cutting state. Sonnet in a worktree without prior mapping tends to leave half-migrations.
5. **Compound-engineering contract.** `.claude/rules/daily-skills.md` section 5 says "don't fix and audit in same session — causes half-finished refactors."

---

## Session 1 — automation_engine.py god-class split (L effort)

**Current state:** 4,418 lines. Grew 133 lines since audit. Handles:
- Sequence triggering + execution (`trigger_sequence`, `process_pending_steps`, `execute_step`)
- Email/SMS dispatch (`execute_email_step`, `execute_sms_step`)
- Appointment/review/billing workflows
- Rule evaluation (`VALID_TRIGGER_EVENTS`, trigger_config filtering)
- Scheduled background checks (`check_no_response_leads`, etc.)

**Target module layout:**
```
backend/services/automation/
  __init__.py              # public API (backward-compat re-exports)
  orchestrator.py          # process_pending_steps, execute_step
  trigger.py               # trigger_sequence, trigger_event handling, VALID_TRIGGER_EVENTS
  dispatcher_email.py      # execute_email_step
  dispatcher_sms.py        # execute_sms_step
  scheduled_checks.py      # check_no_response_leads + other periodic jobs
  rule_evaluator.py        # trigger_config filter logic (e.g. target_stage)
```

**Approach:** compound-engineering pipeline (Opus plan → Sonnet execute → Vertical checker → QA)

**Pre-work for that session:**
1. Run `npx gitnexus analyze` (impact map)
2. `gitnexus_context({name: "trigger_sequence"})` and `gitnexus_context({name: "execute_step"})` → callers
3. List every external caller of current `automation_engine` public functions
4. Generate move map (symbol → new module)
5. Preserve public import path via `__init__.py` re-exports OR bulk-update all callers

**Risks:**
- Circular imports between `orchestrator` and `dispatcher_*`
- Background task registration (`main.py` startup hooks) points at `automation_engine` symbols
- Tests in `tests/test_automation_engine.py` + `backend/tests/test_automation_*.py` import internal helpers

**Gate to merge:**
- Full test suite green (backend + frontend)
- `python -c "from backend.services.automation_engine import trigger_sequence"` still works
- `gitnexus_impact({target: "trigger_sequence", direction: "upstream"})` shows no HIGH/CRITICAL breaks

**Effort:** 1 day of focused compound-engineering session.

**Rollback:** Revert the split commit. Public API preserved by `__init__.py` makes this safe.

---

## Session 2 — analytics.py router split (M effort)

**Current state:** 2,023 lines. 60+ endpoints. Mixed:
- Dashboard metrics
- Agent control center
- Tenant stats
- Recovery analytics
- Wizard tracking

**Target layout:**
```
backend/routers/analytics/
  __init__.py              # aggregates sub-routers
  dashboard.py             # dashboard metric endpoints
  agent.py                 # agent control center endpoints
  recovery.py              # recovery analytics endpoints
```

**Pre-work:**
1. `grep -rn "from backend.routers.analytics import" backend/` — list every consumer
2. Classify the 60+ endpoints into 3 buckets by route prefix
3. Check `main.py` lines 746–813 for router registration — single line → will become 3
4. Shared helpers → `backend/services/analytics_helpers.py` <!-- drift-skip -->

**Risks:**
- Shared query builders may need extraction (Rule 12: new file, not bloat)
- Some endpoints are used by both dashboard and agent control pages (classification ambiguity)

**Gate:** all analytics endpoints return same shape + same RLS enforcement as before; frontend dashboard + agent pages render cleanly.

**Effort:** half-day. Sonnet-executable from a written brief.

---

## Session 3 — auth.py router split (M effort)

**Current state:** 1,896 lines. JWT validation + branding logic + widget-config update co-located. Security layer doing business logic.

**Target:**
- Move branding endpoints + logic → `backend/routers/branding.py` <!-- drift-skip -->
- Move `WidgetConfigDetail` update logic → `backend/routers/widget_config.py` (already exists, may need merging)
- Keep `auth.py` pure: JWT signing/decoding, tenant isolation, OAuth callbacks

**Pre-work:**
1. Enumerate endpoints in `auth.py` by concern (auth vs branding vs widget-config)
2. `auth_service.py` already exists (created in 344df51) — widen its surface
3. Check `main.py` router registration
4. Map frontend API callers (`frontend/src/utils/api/`) — any URL path changes must match

**Risks:**
- Branding endpoints share auth middleware — may need decorator extraction
- `update_widget_config` was recently touched for `enable_structured_lead_parser` toggle (Phase 4 lead parser) — don't regress

**Gate:** login, tenant isolation, widget config save, branding update all work; no endpoint URLs change.

**Effort:** half-day.

---

## Session 4 — widget_helpers.py router split (M effort)

**Current state:** 1,632 lines. Chat, lead capture, booking helpers, callback logging mixed.

**Target:**
```
backend/routers/widget/
  __init__.py
  chat.py                  # /api/widget/chat
  booking.py               # /api/widget/booking/*
  lead_capture.py          # /api/widget/lead/*
  callback.py              # /api/widget/callback
```

**Pre-work:**
1. `_enrich_lead_from_message` helper from Phase 2 lead-parser sits at end of file — preserve its import path or update the `background_tasks.add_task` call site
2. Widget JS (`frontend/public/widget/agentnexlify-widget.js`) hits these endpoints — don't change URLs
3. Test in `backend/tests/test_lead_enrichment.py` imports from this file

**Gate:** widget embed on `chatbot.html` test page captures leads, books appointments, logs callbacks, calls Claude — all identical behavior.

**Effort:** half-day.

---

## Shared constraints for all 4 sessions

- **Never change tests to pass** (Rule 10). If a test breaks after the split, the code is wrong.
- **Register new routers in `main.py` after all splits land** — three concurrent worktrees editing `main.py` collide.
- **Preserve public API via `__init__.py` re-exports.** Lets us roll back individually.
- **No behavior changes.** These are pure refactors. New features or perf fixes belong in separate PRs.
- **Run `gitnexus_impact` before and after.** Goal: 0 unexpected HIGH-risk breaks.

---

## Deferred (not in this plan)

- **Lead-parser Phase 5 rollout** — needs MTOptions tenant UUID + production DB write approval + 24h observability window. Separate operational task.
- **Monolithic test file splits** — LOW priority. Not driving any pain yet.
- **Quarterly `npm audit`** — scheduled task, not a session.

---

## Success criteria

After all 4 sessions:
- No file in `backend/routers/` or `backend/services/` exceeds 600 lines (Rule 9)
- Zero layer violations (service importing router)
- All audit HIGH items closed
- All audit MEDIUM code items closed
- `gitnexus analyze` shows clean dependency graph
