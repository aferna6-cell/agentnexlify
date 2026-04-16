# Idea 4: Widget Hot-Zone Regression Suite

**Category:** reliability / dx
**Effort:** medium (2–3 days)
**Impact:** High — widget files change 6–8x/week with no e2e test coverage

---

## Hypothesis

A dedicated regression test suite (5–8 tests) targeting the widget hot zone — `widget_helpers.py`, `widget_chat.py`, `widget_lead.py` — run automatically on every push that touches those files will catch the regressions that keep happening in the most-changed code. Three of the last 5 major bugs originated in this zone.

---

## Evidence

1. `docs/daily-logs/2026-04-03.md` line 46: "Hot zone: widget_chat.py + widget_helpers.py + widget JS are the most actively modified files. High change velocity = high regression risk."
2. Most-modified file list: widget_helpers.py (8 changes), widget_chat.py (6 changes) in 7 days — no other files approach this.
3. `docs/dev-knowledge/bug-patterns.md`: conversations.lead_captured bug, RLS silent failure bug, widget null-state guard — all in `widget_helpers.py`.
4. `docs/dev-knowledge/test-coverage.md` lines 47–51: "Widget file upload… SMS delivery… Claude AI response quality — mocked in tests, not integration-tested" — test gaps exist specifically in the widget.
5. The existing test isolation failures (11) are partly because widget modules share mock state — a dedicated widget test file with clean setup/teardown would also fix the isolation issue.

---

## Implementation Sketch (no code)

1. **New test file: `tests/test_widget_regression.py`** — standalone file, no shared fixtures with other tests
2. **8 regression tests** targeting the exact scenarios that failed:
   - Lead capture writes to `leads` with `client_id` (not `tenant_id`)
   - Conversation record created on new session (RLS not blocking anon INSERT)
   - `lead_captured` flag set to True after successful capture
   - Widget returns correct response when `knowledge_base` is NULL (graceful fallback)
   - Widget offline mode returns 200 with offline message
   - Handoff request (if idea-1 wins) creates conversation record
   - Duplicate session UPSERT doesn't create two conversation rows
   - Widget response within 3s (latency regression guard)
3. **GitHub Action trigger** — run only `test_widget_regression.py` on any push touching `backend/routers/widget_*.py`

---

## Success Metric

- 8/8 regression tests pass on current codebase
- CI runs widget suite on every push to widget files (<30s)
- Zero new widget bugs slip through without a corresponding failing test
