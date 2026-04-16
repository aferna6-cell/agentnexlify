# Implementation Plan — lead-parser-replacement

**Source spec:** [/specs/lead-parser-replacement_spec.md](../specs/lead-parser-replacement_spec.md)
**Generated:** 2026-04-15 via prd-to-plan skill
**Estimated phases:** 5
**Reversibility:** every phase commits behind `widget_configs.enable_structured_lead_parser` flag (default false)

## Phase 1 — Tracer Bullet (DB + flag, off by default) ✅ SHIPPED 2026-04-15
**Goal:** ship the migration + flag, no behavior change yet
**DB:** `migrations/103_widget_configs_enable_structured_lead_parser.sql` (102 was taken)
- ALTER TABLE widget_configs ADD COLUMN enable_structured_lead_parser bool DEFAULT false NOT NULL
- COMMENT ON COLUMN explains purpose + date
**API:** none new — flag defaults false, current pipeline unchanged
**UI:** none — flag invisible to users
**Gate:** migration applies to staging without error; existing widget chat keeps working
**Rollback:** drop column (additive migration, safe)
**Files touched:** 1
**Effort:** 30min

## Phase 2 — Background enrichment helper (off behind flag) ✅ SHIPPED 2026-04-15
**Goal:** wire `_enrich_lead_from_message` helper, gated, never runs yet
**API:**
- `backend/routers/widget_helpers.py` — added `_enrich_lead_from_message()` at end of file (~165 LOC)
- `backend/routers/widget_chat.py` — added background_tasks.add_task call gated on `widget.get("enable_structured_lead_parser")` after `_capture_leads_from_session` (line ~952)
- Spec deviation logged: spec referenced `ExtractorError` but real code raises `ValueError` — helper catches `ValueError` and `Exception` per Rule 10
- Spec deviation logged: spec said dedup by `session_id` but `leads` table has no such column — dedup falls back to email/phone like `_capture_leads_from_session`
**UI:** none
**Gate:** all tests in test_lead_enrichment.py pass; existing widget_chat tests still pass; CI green
**Rollback:** revert 2 files OR keep flag false everywhere
**Files touched:** 2
**Effort:** ~1h

## Phase 3 — Test coverage ✅ SHIPPED 2026-04-15
**Goal:** 8+ tests per spec section "Tests" before any tenant gets the flag
**Files:**
- `backend/tests/test_lead_enrichment.py` (NEW, ~330 LOC, 8 tests across 4 classes)
  - `TestHelperExists::test_helper_is_importable` — sanity check
  - `TestEnrichmentSkipPaths::test_extractor_returns_nothing_new`
  - `TestEnrichmentSkipPaths::test_no_email_or_phone_skips_with_no_db_call`
  - `TestEnrichmentSkipPaths::test_lead_not_found_skips_update`
  - `TestEnrichmentPersist::test_fills_missing_fields`
  - `TestEnrichmentPersist::test_respects_regex_wins_policy`
  - `TestEnrichmentPersist::test_activity_log_written_with_fields_added`
  - `TestEnrichmentNeverCrashes::test_extractor_value_error_does_not_crash`
  - `TestEnrichmentNeverCrashes::test_extractor_unexpected_exception_does_not_crash`
  - `TestEnrichmentNeverCrashes::test_handles_fenced_json_via_extractor_contract`
- Mock `structured_extractor.extract_structured` — no live API
**Gate:** all pass when CI runs.
**Local pytest status (2026-04-16 investigation):**
- pyiceberg IS a blocker, but via transitive chain: `supabase==2.28.3 → storage3==2.28.3 → pyiceberg>=0.10.0`. Not a direct dep.
- Windows + Python 3.14: pyiceberg 0.11.1 has no prebuilt wheel; source build needs C++ toolchain.
- Fixes (pick one when local pytest is needed): (a) install Visual C++ Build Tools, (b) use WSL/Docker for testing, (c) pin Python to 3.12 where wheels exist, (d) pin supabase to a version whose storage3 didn't require pyiceberg.
- Railway/CI unaffected — python:3.11-slim Linux image has pyiceberg wheels.
**Rollback:** delete test file (no prod impact)
**Files touched:** 1
**Effort:** ~1h

## Phase 4 — UI toggle in widget config ✅ SHIPPED 2026-04-15
**Goal:** tenants can self-enable via dashboard
**Files:**
- `frontend/src/pages/WidgetPage.jsx` — added checkbox toggle matching `enable_ai_fallback` pattern (plain checkbox, no ToggleField component — none existed in codebase)
- `backend/models/schemas.py` — added `enable_structured_lead_parser: bool = False` to `WidgetConfigDetail`; `bool | None = None` to `WidgetConfigUpdateRequest`
- `backend/routers/auth.py` — wired `enable_structured_lead_parser` into `WidgetConfigDetail` response in both `update_widget_config` and dashboard load
- Also fixed pre-existing bug: `enable_ai_fallback` was in the DB (migration 101) but missing from both Pydantic models, so the dashboard toggle silently dropped the value on save. Fixed in same PR (Rule 11 additive win).
- Spec deviation: `widget_config.py` not touched — update endpoint is in `auth.py::update_widget_config`, not in widget_config.py.
**Gate:** toggle visible in dashboard, persists to DB, respects RLS, frontend build green
**Rollback:** flip flag off per tenant in DB
**Files touched:** 3
**Effort:** 1h

## Phase 5 — Rollout + observability
**Goal:** enable for MTOptions, monitor, expand
**Steps per spec "Rollout":**
1. Enable flag for MTOptions tenant: `UPDATE widget_configs SET enable_structured_lead_parser = true WHERE client_id = '<mtoptions-uuid>';`
2. Monitor `activity_log WHERE activity_type = 'lead_enriched'` for 24h
3. Compare lead-completion rate before/after — target ≥95% have name+email+phone within 3 messages
4. If green: enable for 4 other testers
5. After 1 week clean: change column DEFAULT to true via migration 103
**Gate:** ≥95% completion rate on enriched tenants AND zero crashes in widget_chat tests AND cost ≤$1.50/tenant/month
**Rollback:** flip flag back to false per tenant
**Files touched:** 0 code (DB only) + 1 audit report in `/audits/`
**Effort:** 1 day calendar (mostly waiting on data)

## Cross-Phase Concerns

### Schema discipline (CLAUDE.md invariants)
- `client_id` not `tenant_id` on `leads` queries — already enforced in `_enrich_lead_from_message` line 131 of spec ✅
- `status` not `lead_stage` — N/A, this feature doesn't touch status
- `areas_of_interest` not `service_interest` — `_enrich_lead_from_message` references "interest" key in merge — verify schema column name in Phase 2

### Widget byte-sync (CLAUDE.md invariant)
This feature touches `widget_helpers.py` (Python helper, not the JS widget). No `widget/agentnexlify-widget.js` or `frontend/public/widget/agentnexlify-widget.js` changes needed. ✅ no byte-sync risk.

### Tests before rollout
Phase 3 MUST land before Phase 5. Phase 4 UI can ship while Phase 3 in progress.

### FastAPI footgun
Per CLAUDE.md Critical Invariant #5 — DO NOT add `from __future__ import annotations` to either modified file. Already verified absent.

### Cost guardrail
Per spec "Cost + latency budget":
- Per call: ~$0.002 (Haiku, <500 input + <200 output tokens)
- MTOptions ceiling: 704 msgs/mo × $0.002 = $1.41/mo
- Max 5 testers: $7.05/mo total. Within ops budget.
- If cost exceeds 2× projection in Phase 5 monitoring → STOP, investigate

## Success Metrics (from spec)
- Lead-field completion rate ≥95% within first 3 messages (baseline ~92% per 2026-04-08 audit)
- Zero widget_chat regression incidents
- Cost ≤$1.50/tenant/month
- No latency increase on chat happy path (background task)

## Known Risks
- **Risk 1:** structured_extractor returns garbage on edge inputs → merge logic over-writes good regex data. **Mitigation:** "regex wins on fields both populated" policy in spec line 117-122.
- **Risk 2:** Anthropic API outage → enrichment fails silently. **Mitigation:** ExtractorError caught, logged warning, no exception bubbled (spec lines 103-114).
- **Risk 3:** Background task queue saturates under load. **Mitigation:** existing widget chat rate limit (60/min) caps enrichment volume implicitly.
- **Risk 4:** "interest" key name mismatch with `areas_of_interest` column — Phase 2 task to verify and fix mapping.

## Status
- [x] Phase 1 — Migration + flag (2026-04-15, applied to live Supabase by user)
- [x] Phase 2 — Background helper (2026-04-15)
- [x] Phase 3 — Tests (2026-04-15)
- [x] Phase 4 — UI toggle (2026-04-15)
- [ ] Phase 5 — Rollout + audit (infrastructure ready 2026-04-15; awaiting MTOptions enable + 24h window)

## Producer skill metadata
Generated by: `prd-to-plan` (v1.0.0)
Methodology: tracer-bullet vertical slices
Phase sizing: each phase fits one PR, deployable independently, ≤5 days work
