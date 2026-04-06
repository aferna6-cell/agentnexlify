# Improvement Backlog — 2026-04-06

## Active
- **Lead Source Analytics Chart** — Add `GET /api/leads/source-stats` endpoint + Recharts panel to Analytics/Leads dashboard. Closes explicit cross-industry gap (customer-gaps.md). ROI: 2.67.

## Parking Lot (survived debate, not chosen)

- **Widget Click Regression Guard** — Add Playwright E2E test that clicks the widget button, asserts chat opens within 1000ms, sends a message, asserts response. Gate nightly CI. Evidence: fdcc3b5 hotfix proved smoke tests miss JS-layer failures. ROI: 2.0.
- **Onboarding AI Parser Edge Case Tests** — Add `tests/test_onboarding_parser_edge_cases.py` with parametrized malformed-JSON inputs (truncated, extra wrapper, null fields) matching failure modes from repurposer (c600cda). Parser seam already extracted (dc3ac62). ROI: 1.5.

## Rejected This Run

- None killed outright — all 3 debated ideas survived. Ideas 4 and 1 below were not debated but ranked lower:
  - **Idea 4: LLM Runtime Docs / ai-feature-pattern skill update** — Valid but low customer-facing impact; documentation-only. Can be folded into any future skill-update run.
  - **Idea 1: LLM Runtime Observability Dashboard** — High effort (new backend endpoint + new dashboard panel with tracing infrastructure). Good idea but effort/complexity makes ROI lower than Idea 2.

## Questions for Next Run

1. Did the Lead Source Analytics chart get implemented? If yes: are source values being reliably populated by the widget capture path, or is the `source` column still mostly NULL for existing leads?
2. Was the Widget Click Regression Guard (Playwright E2E) picked up? If not, it should be the next `code_health` pick — the widget-not-opening class is recurring.
3. The `test-coverage.md` notes 11 test isolation failures (mock state leaks). When is the team planning to fix test infrastructure? This is a compounding debt that degrades confidence in the test suite.
