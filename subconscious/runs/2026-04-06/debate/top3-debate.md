# Top 3 Debate — 2026-04-06

Ranking rationale: Ideas ranked by cross-cutting impact before entering debate.
1. Idea 5 — Widget Click Regression Guard (highest severity: blocks entire revenue path)
2. Idea 2 — Lead Source Analytics Dashboard (cross-industry gap, low effort, customer value)
3. Idea 3 — Onboarding AI Parser Edge Case Tests (first-impression risk, recurring JSON failure class)

---

## Idea 5: Add Widget "Not Opening" Regression Guard to E2E Suite

### Objections

**Objection 1: The nightly E2E smoke tests added in commit 952a609 may already cover this.**
If the smoke script (`scripts/daily/e2e-smoke.sh`) already tests widget button clicks, this recommendation adds zero value.

**Defense:** The commit message for fdcc3b5 ("fix: widget not opening on click") was *after* the nightly smoke tests were added (952a609). If the smoke tests tested widget click-open, this bug would have been caught before the hotfix was needed. The sequence of commits proves the gap: smoke tests added → widget click bug landed → hotfix required. The smoke tests clearly do NOT include a click-open assertion. Evidence: `scripts/daily/e2e-smoke.sh` was created in 952a609 but tests health/config/chat endpoints at the API level — not DOM click behavior. Widget click failure is a JavaScript-layer failure, not an HTTP-layer failure.

**Objection 2: Playwright requires a separate dependency installation and CI infrastructure — this is non-trivial effort.**
Adding a Playwright E2E test to the nightly cron requires `npm install playwright`, a headless browser, and CI infrastructure that may not exist. This could take a full sprint, not an afternoon.

**Defense:** The existing `scripts/daily/e2e-smoke.sh` is a bash+curl script that runs against live endpoints. The widget-open regression could alternatively be tested by checking that the widget JS initializes without errors (a simpler smoke signal). However, the full recommendation already scoped this as a Playwright test — which is the correct solution. The effort is bounded: the smoke test infra already runs nightly, adding Playwright is `npm install playwright` + one test file (~80 lines). The risk of NOT having this test is a broken widget going undetected until a customer complains — the highest-cost failure mode possible. Effort is Medium, risk of not doing it is CRITICAL.

**Objection 3: Widget JS already has two copies (widget/ and frontend/public/widget/) which the CLAUDE.md rule already guards. Is this duplication the real risk vector, not the click handler?**
The CLAUDE.md rule "Widget JS must be identical in widget/ AND frontend/public/widget/" covers the sync problem. The click bug came from a variable reference error in `init()`, not from sync divergence. Does a regression test actually prevent the root cause?

**Defense:** The root cause (undefined variable `data.plan` crashing `init()`) is a JavaScript runtime error that would be caught immediately by a test that actually clicks the widget. Regression tests don't prevent root causes — they catch regressions before customers do. The widget is the #1 revenue path; the cost of a click-handler regression going undetected for even 6 hours is unbounded in lost leads. The test is cheap, the insurance is high.

**Verdict: SURVIVES**
- Impact: 5 (widget-not-opening = zero leads captured = direct revenue loss)
- Effort: 3 (Playwright setup + one test file, nightly cron already exists)
- Risk: 2 (low risk — test addition is purely additive)
- ROI = (5 * 2) / (3 + 2) = **2.0**

---

## Idea 2: Add Lead Source Analytics Dashboard Panel

### Objections

**Objection 1: The `source` column on leads may have sparse data — if most leads have NULL source, the chart is useless.**
If lead capture doesn't reliably populate `source`, a pie chart showing "90% NULL" is noise, not signal.

**Defense:** The widget capture path (`widget_helpers.py`) has been actively maintained and the schema log shows `source` was added in migration 022 (lead_source_tracking, cycle 122 per customer-gaps.md). The commit `feat: lead source tracking — All — 122` confirms this was deliberately built. The `source` column exists specifically to drive this kind of visualization. If some older leads have NULL, the chart should simply show a "Direct / Unknown" bucket — standard analytics practice. The customer-gaps.md rates this "Low Effort" explicitly.

**Objection 2: This is pure frontend work with no backend complexity. Is this really an "improvement" or just a missing feature that belongs in the feature backlog?**
The subconscious brief says improvements should compound. A chart panel doesn't compound — it's a one-time feature addition.

**Defense:** The distinction between "improvement" and "feature" is semantic. The subconscious brief explicitly calls out "customer value" as a category (category 4). This gap was identified across ALL 6 industry simulations — it affects every tenant on every plan. It's the highest-breadth open gap in customer-gaps.md. "Low effort, cross-industry impact" is exactly the profile that compounds into churn reduction. Also: it closes a documented product gap, which has direct competitive positioning value against GoHighLevel and Podium (both show lead source analytics).

**Objection 3: Recharts is already a dependency and the Analytics page exists, but we don't know if the Analytics page is already complex. Adding a panel could cause frontend layout issues on mobile.**
The onboarding sprint (952a609) specifically fixed mobile responsive layout issues. Injecting a new panel risks regressing those fixes.

**Defense:** Adding a chart panel to an existing page section is low-coupling. Recharts components are isolated — they don't affect surrounding layout unless poorly positioned. The recommendation is to add to the *Analytics* or *Leads* page specifically, not touch the newly-fixed onboarding or mobile layout. A developer can scope the placement to avoid any layout conflict. This objection would apply to any frontend change and is not specific enough to weaken the recommendation.

**Verdict: SURVIVES**
- Impact: 4 (closes cross-industry gap, direct customer retention value, competitive differentiation)
- Effort: 2 (low — Recharts already present, source column exists, simple GROUP BY query)
- Risk: 1 (purely additive frontend chart, no backend risk)
- ROI = (4 * 2) / (2 + 1) = **2.67**

---

## Idea 3: Add Onboarding AI Parser Edge Case Tests

### Objections

**Objection 1: The onboarding parser seam was already extracted (commit dc3ac62 "test: extract onboarding ai parser seam"). If the seam is extracted, isn't it already tested?**
Commit dc3ac62 title implies coverage exists. Why add more?

**Defense:** Seam extraction and test coverage are different things. Extracting a parser seam means the function is now separately testable — but that doesn't mean edge case tests were written. The commit message says "extract ... and document llm runtime ops" — documentation of behavior, not parametrized failure-mode coverage. The commit for content repurposer tests (055b994: "test: harden repurposer json repair and parser coverage") shows 7 days of JSON-repair hardening work. The onboarding parser faces the same failure modes (truncated JSON, extra wrapper text, null fields) but has zero equivalent hardening commits. Evidence: no `test_onboarding_parser_edge_cases.py` exists in the test file list from test-coverage.md.

**Objection 2: Onboarding runs once per tenant. Even if it silently fails with bad JSON, the tenant can re-run onboarding. The blast radius is one tenant, one time — not a production hot path.**
The continuous hot path (widget chat, every conversation) deserves priority over a one-time flow.

**Defense:** Onboarding failure is first-impression critical. A new tenant whose widget config is malformed from day one experiences: broken chat responses, no FAQ entries, no bot personality. They will churn in the first 24 hours before ever seeing value. This is the highest churn-risk moment in the product lifecycle. Fixing it after the fact requires human support intervention. The repurposer JSON repair bug (c600cda, fdcc3b5) demonstrated that AI-generated JSON malformation is not rare — it happened to a mature feature and required an immediate hotfix. The onboarding path is younger and uses the same Claude pattern.

**Objection 3: The test suite already has 11 test isolation failures (mock state leaks). Adding more test files may worsen this problem before the isolation issues are resolved.**
The test-coverage.md notes "11 test isolation failures remain." Adding more tests to a leaky suite compounds the problem.

**Defense:** This is a real constraint. However: (1) the isolation failures are in existing files with complex cross-module mocking; (2) a new file focused on a single parser function (pure input→output with no DB or HTTP calls) would not trigger state leaks; (3) the fix for content repurposer parser coverage (055b994) was added after the isolation issues were documented — it did not appear to worsen them. The onboarding parser edge case tests are narrowly scoped to pure Python parsing logic, the lowest-risk test category to add.

**Verdict: SURVIVES (WEAKENED)**
- Impact: 3 (first-impression critical, but blast radius is one tenant at a time)
- Effort: 2 (parser seam is already extracted, test patterns are established)
- Risk: 2 (small test isolation risk from the existing 11 failures)
- ROI = (3 * 2) / (2 + 2) = **1.5**

---

## Summary

| Idea | Verdict | ROI | Notes |
|------|---------|-----|-------|
| Idea 5: Widget Click Regression Guard | SURVIVES | 2.0 | Highest severity, prevents #1 revenue-path failure |
| Idea 2: Lead Source Analytics Panel | SURVIVES | 2.67 | Highest ROI, lowest effort, cross-industry |
| Idea 3: Onboarding AI Parser Tests | SURVIVES (WEAKENED) | 1.5 | Valid but lower ROI; parser seam extracted, narrowly scoped |

**Winner by ROI: Idea 2 — Lead Source Analytics Dashboard Panel (ROI 2.67)**
