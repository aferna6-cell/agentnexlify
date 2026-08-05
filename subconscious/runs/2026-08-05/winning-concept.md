# Winning Concept — 2026-08-05 (Run 103)

## Recommendation
Add `backend/tests/test_tenant_kb_widget_retrieval.py`: an integration test verifying that a typed KB note inserted via `POST /api/v1/kb/{tenant_id}/notes` (feature `4853c31`) is retrieved by the KB search function and present in assembled widget chat context.

## Why This, Why Now

Feature `4853c31` (merged 2026-08-02, 3 days old) ships typed KB notes. Tenants can now type pricing, policies, and service details directly into the dashboard. 8 tests cover the insert path (`backend/tests/test_tenant_kb.py`). Zero tests verify the note surfaces in widget chat AI responses.

The booking CTA bug (2026-07-23) is the exact precedent: the URL-sharing feature worked in isolation (AI replied with the URL) but failed end-to-end (widget renderer didn't linkify it). The pattern is: new feature ships, insert-side test added, retrieval-side gap missed, tenants discover the failure empirically.

KB notes exist to power AI chat quality. "Note saved" ≠ "note used by AI." If `source='note'` rows are not included in the KB search query (e.g., filtered by `source='file'` only), tenants will type in their service details and the AI will still give generic answers. None of the 3 live tenants will know why.

## What to Build

File: `backend/tests/test_tenant_kb_widget_retrieval.py`

Test contract:
1. **Setup:** create test tenant, ingest KB note via the new API endpoint (or directly via `upsert_document`)
2. **Search:** call the KB search function with a query that should match the note content
3. **Assert retrieval:** note content (or a phrase from it) appears in search results
4. **Assert context injection:** assemble widget chat context using existing context-builder; assert note text present in assembled prompt

Acceptance criteria:
- Test passes when `source='note'` rows are included in KB search
- Test fails (and catches the bug) when `source='note'` rows are excluded
- Test is deterministic — no LLM call needed, KB search and context assembly are local functions

## Confidence
**HIGH** — Fresh evidence (feature 3 days old), known failure class (booking CTA precedent), concrete test spec, confirmed coverage gap. Nightly commit review cannot catch this (not its job). Subconscious is the right channel.

## What This Replaces
Nothing. Complements existing insert-path tests in `test_tenant_kb.py`. Adds end-to-end retrieval coverage missing from the feature's test suite.

## Scope
S-effort: one new test file, ~60-80 lines. No prod code changes. No migrations. No new dependencies.

## Governance Mandate Status (Run 103 checks)

1. **Step 9G in SKILL.md:** ABSENT (0 grep hits on main). Two PRs exist (#625, #626). Human action pending. Morning digest already flagged as top priority. Subconscious has recommended 7 consecutive runs (97-103). No further subconscious recommendation can break the logjam — human action only.
2. **KB freshness since 2026-07-13:** STILL STALE — 23 days as of 2026-08-05.
3. **Step 9G fired (nightly):** N/A — Step 9G not on main.
4. **GH #403 Step 9G comment:** Cannot verify from repo-local evidence.
5. **Agent OS tenant count:** No change to active directions (condition still parking lot).
6. **MCP tenant count:** No change detected.

Run 104 mandate:
- Re-verify Step 9G status (is #625 or #626 merged?)
- If merged: confirm Step 9F + 9G fired on first stale-KB nightly after merge
- If not merged: escalate to run-summary.json "governance stuck" flag
- Confirm `test_tenant_kb_widget_retrieval.py` is implemented (check if filed as issue or merged)
