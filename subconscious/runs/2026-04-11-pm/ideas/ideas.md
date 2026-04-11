# Ideation — 2026-04-11-pm

## Evidence Digest

**3-day commits (Apr 9–11):**
- Widget AI fallback landed: migration 101, `widget_chat.py` (198 lines), `test_widget_chat_fallback.py` (430 lines)
- 6 autoskills installed (accessibility, deploy-to-vercel, frontend-design, nodejs-backend-patterns, nodejs-best-practices, seo) + symlinks restored
- 5 competitor research briefs committed (GoHighLevel, Drillbit, Birdeye, Oscar Chat, Phonely) in Apr 10 session
- 2 new planning specs: admin-agent-invocation-ui + lead-parser-replacement
- Managed agents: structured_extractor + support_agent updated, smoke scripts for all 5 agents
- 3 separate fix commits for `get_service_supabase` test patches

**From daily log Apr 10:**
- 8 silent `.catch(() => null/{})` patterns stuck at 8 for 2+ days — "Priority 2" + explicit pre-commit extension recommendation
- Priority 1: QA managed agents (5 active, growing)
- 24 pending migrations — unchanged
- Security incident DAY 8: admin API key rotation overdue

**Bug patterns (top of file, 2026-04-10):**
- FastAPI TestClient deadlocks (fixed) — new class
- Orphaned test files after dead code sweeps (fixed)
- `get_service_supabase` rename cascade (3 fix commits = high churn)

**Governance state:**
- Run 1 winner: Update stale skills (workflow) — pending approval
- Run 2 winner: Lead source analytics chart (customer value) — pending approval
- Parking lot: Widget Click Regression Guard (ROI 2.0), Onboarding AI Parser Edge Case Tests (ROI 1.5)
- Rejected: AI-to-human handoff (too large for atomic)

---

## Idea 1: JS Silent Catch Pre-commit Guard

**Evidence:** Daily log Apr 10 explicitly flags `.catch(() => null/{})` as Priority 2 and recommends extending the pre-commit hook. 8 instances stable across both morning and evening checks — not growing but not fixed. Pre-commit hook (`scripts/hooks/pre-commit`) already blocks Python bare excepts (Check 3) using the same pattern — JS extension is natural.

**Action:** Add Check 8 to `scripts/hooks/pre-commit`: grep staged `.js/.jsx/.ts/.tsx` files for `.catch\s*(\s*() =>` patterns that swallow errors (null, {}, empty return). Emit WARNING (not BLOCK) — consistent with bare except treatment.

**Impact:** Prevents new silent error patterns from accumulating. Compounds on every future commit. Zero infra dependency. Under 15 lines added to existing hook.

**Category:** code_health

---

## Idea 2: Widget Click Regression Guard (Promote from Parking Lot)

**Evidence:** Parking lot entry (ROI 2.0, "pick next for code_health run"). New evidence: migration 101 + `widget_chat.py` (198 lines) + `test_widget_chat_fallback.py` (430 lines) added Apr 11 — widget complexity increased. `autonomous-webapp-test` skill and `widget-test` skill both added/updated this session. Parking lot note: "Highest severity but medium effort."

**Action:** Write 3–5 Playwright E2E tests in `tests/e2e/test_widget_click.py` covering: (a) widget opens on button click, (b) message sends and receives AI response, (c) lead capture form appears and submits, (d) AI fallback mode activates when flag set.

**Impact:** Catches user-visible widget regressions that unit tests miss. Widget is the primary revenue-generating surface. ROI 2.0 per parking lot valuation.

**Category:** code_health

---

## Idea 3: Ingest 5 Competitor Briefs into KB

**Evidence:** Apr 10 evening review: "Competitor research briefs: 5 new docs — consider integrating key findings into knowledge-base/wiki/ via /kb-ingest." Commit `b97928a` added competitor briefs for GoHighLevel, Drillbit, Birdeye, Oscar Chat, Phonely. KB `Competitors` category has only 1 article (competitive-landscape-march-2026). "Small Business SaaS" and "Technical Patterns" categories empty.

**Action:** Run `/kb-ingest` on each of the 5 competitor brief files, producing 5 structured wiki articles in `knowledge-base/wiki/competitors/`. Update `knowledge-base/INDEX.md`.

**Impact:** 5 articles added to KB, making competitive intelligence queryable via `/kb-query`. Improves all future competitive positioning and customer-value decisions.

**Category:** operational

---

## Idea 4: Lead Parser Replacement — Write Tests First

**Evidence:** Parking lot: "Onboarding AI Parser Edge Case Tests (ROI 1.5) — parser seam extracted; tests not yet written." Today (177251d): `planning/specs/lead-parser-replacement_spec.md` committed — a full replacement spec now exists. The spec's existence signals this is being actively planned, making edge case tests the natural immediate step.

**Action:** Write pytest tests in `tests/test_lead_parser_edge_cases.py` against the current parser seam, covering: (a) multi-service requests ("I need a haircut and color"), (b) ambiguous time requests ("sometime next week"), (c) missing fields with fallback, (d) non-English inputs. Tests should fail with current parser — they define what the replacement must pass.

**Impact:** Tests-first locks in expected behavior before replacement. Prevents regressions in the new parser. Gives the spec an executable acceptance test suite. ROI 1.5 per parking lot.

**Category:** code_health

---

## Idea 5: Managed Agents Automated Integration Tests

**Evidence:** Apr 10 daily log: "QA Managed Agents" listed as Priority 1. 5 managed agents active: lead_qualifier, support, structured_extractor, researcher, field_monitor. Commit `b97928a` added router HTTP tests + smoke scripts. Today (df6beff): structured_extractor + support_agent + test_managed_agents.py all updated. But smoke scripts are manual; no automated pytest covering all 5 agent HTTP routes.

**Action:** Expand `backend/tests/test_managed_agents.py` to cover all 5 agent HTTP endpoints (POST `/api/agents/qualify`, `/api/agents/support`, `/api/agents/extract`, `/api/agents/research`, `/api/agents/field-monitor`) with mocked Claude API responses — test routing, auth, and error handling for each.

**Impact:** Closes Priority 1 QA gap. Prevents regressions as managed agents expand. Blocks bad deploys via CI gate.

**Category:** agent_performance
