# Run 101 Ideas — 2026-08-05

**Evidence base:** nightly-commit-review logs 2026-08-04/05, knowledge-base/log.md, bug-patterns.md, customer-gaps.md, governance.json run_101_mandate, memory.jsonl runs 96-100, SKILL.md Step 9F/9G grep results, PR list.

---

## Idea 1 — Merge Step 9G PR (Resolve Governance Mandate)
**Category:** Operational  
**Confidence:** HIGH  
**Effort:** XS  

Step 9G (self-healing KB trigger) was run 100's winner. Two open PRs implement it (#625, #626). `grep 'Step 9G' .claude/skills/nightly-commit-review/SKILL.md` returns 0 hits — absent from main. Governance mandate fires. Morning digest (2026-08-04) already marks this as top priority #1. Human action is unblocked.

**Action:** Human merges #626 (`subconscious/run-101-step9g`) or closes #625 as duplicate, resolving 4-run carry-forward.

---

## Idea 2 — Validate Step 9F Is Still Firing on Stale KB
**Category:** Operational  
**Confidence:** MEDIUM  
**Effort:** S  

KB is 23 days stale (last automated run 2026-07-13). Step 9F is confirmed present in SKILL.md (6 occurrences). However, nightly logs for Aug 1-5 show no Step 9F output. Either: (a) Step 9F is running but not logging visibly to ops/routines/logs/, (b) the nightly skill is skipping the Step 9F block due to a path issue, or (c) the run context can't read knowledge-base/log.md. This is a silent failure class.

**Action:** Add a verification pass — read nightly-commit-review SKILL.md Step 9F block, confirm the log path and grep pattern are correct against current knowledge-base/log.md format. File a diagnostic issue if mismatched.

---

## Idea 3 — KB Notes End-to-End Widget Retrieval Test
**Category:** Code Health / Customer Value  
**Confidence:** HIGH  
**Effort:** S  

Feature `4853c31` (2026-08-02, 3 days old) ships typed KB notes: POST `/api/v1/kb/{tenant_id}/notes` → `tenant_kb_documents` with `source='note'`. 8 tests cover the insert path. Zero tests verify notes surface in widget chat AI responses. The booking CTA bug (2026-07-23) is the exact precedent: URL was shared by AI (worked) but not linkified in widget renderer (failed). Notes saved ≠ notes used by AI. Gap closes before tenants discover it empirically.

**Action:** Add `backend/tests/test_tenant_kb_widget_retrieval.py` — integration test: insert note via API → call KB search function → assert note content appears in retrieval results → simulate widget context injection → assert note text present in assembled context.

---

## Idea 4 — Expand client_id Guard to All Remaining Tables
**Category:** Code Health  
**Confidence:** MEDIUM  
**Effort:** M  

`bug-patterns.md` (2026-08-01): connector_awareness.py used `.eq("tenant_id", client_id)` on `tenant_api_keys` — a silent query failure. Fix applied in connector_registry.py. Invariant #1 in CLAUDE.md lists leads + conversations; `tenant_api_keys` was a third table. How many others? `tenant_kb_documents` (new, from 4853c31) is accessed by `client_id` ✅. But `widget_configs`, `appointments`, `analytics_events`, `tenant_plan` — unverified. The connector_awareness pattern (wrong column, silent empty result, misreported state) could recur.

**Action:** Grep all Supabase query call sites that use `.eq("tenant_id", ...)` — verify each table's actual column name against schema. File issue for any mismatches found.

---

## Idea 5 — Cross-Phase Feature Integration Test Audit (Capabilities Phase 1-5)
**Category:** Code Health  
**Confidence:** MEDIUM  
**Effort:** M  

Customer-gaps.md shows AI-to-human handoff still Critical. The broader concern: as features ship across phases (widget → backend → KB → AI context), integration gaps accumulate. No automated coverage that follows the full data path: user types in widget → message stored → KB queried → AI context assembled → response returned. The KB notes gap (Idea 3) is one instance. The booking CTA bug was another. An audit of Phase 1-5 capabilities could surface 3-5 similar gaps systematically.

**Action:** Run an exploratory grep audit across backend/tests/ for tests that cross the widget→backend→KB→AI boundary. Count gaps. File GH issue with a ranked list. This is a discovery task, not an implementation.

---

## Summary Table

| # | Title | Category | Confidence | Effort |
|---|-------|----------|------------|--------|
| 1 | Merge Step 9G PR | Operational | HIGH | XS |
| 2 | Validate Step 9F firing | Operational | MEDIUM | S |
| 3 | KB Notes e2e widget retrieval test | Code Health / Customer Value | HIGH | S |
| 4 | Expand client_id guard audit | Code Health | MEDIUM | M |
| 5 | Cross-phase integration test audit | Code Health | MEDIUM | M |
