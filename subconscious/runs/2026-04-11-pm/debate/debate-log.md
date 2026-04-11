# Debate Log — 2026-04-11-pm

Top 3 ideas ranked by impact, debated in challenge-and-defend format.

---

## Idea 1: JS Silent Catch Pre-commit Guard

### Challenge
**C1: Does this fix the actual problem?**
There are already 8 silent catches in the codebase. Adding a pre-commit guard prevents new ones but doesn't fix the existing 8. If those 8 are acceptable, the whole premise weakens.

**C2: Commit friction increases.**
The hook already runs 7 checks. Developers hitting a WARNING on every JS commit touching error handlers will start using `--no-verify` more often, which is worse than the original problem.

**C3: Is `.catch(() => null)` a signal or noise?**
Some silent catches are intentional UX decisions (e.g., "if the analytics call fails, don't crash the page"). Flagging all of them conflates intentional patterns with bugs.

**C4: High-priority items exist (24 pending migrations, API key rotation, QA gaps). Is hook cleanup really the highest leverage right now?**

### Defend
**D1:** The 8 existing catches have been stable for 2+ days per daily log — they aren't being fixed organically. Adding a guard prevents the count from growing to 16 before the fix cycle catches up. Fixing existing 8 is a separate, subsequent action (already identified in daily log as a separate task).

**D2:** The hook emits WARNING, not BLOCK — same behavior as the existing Python bare except check (Check 3). Developers aren't blocked; they're reminded. `--no-verify` risk is no different than current practice.

**D3:** The daily log Apr 10 explicitly flags this pattern and recommends the extension. That's the daily monitoring system confirming it's a problem, not speculation. Intentional catches should have a comment marker (e.g., `// eslint-disable-line`) — the hook can exempt commented lines, same as the `__future__` import check already does.

**D4:** This isn't competing with migrations or security — those require human infrastructure access (Railway for key rotation, Supabase for migrations). This is an automated, zero-infrastructure improvement that ships in a single file change.

### Verdict: **SURVIVES**
Direct daily log evidence. Atomic. Zero infra dependency. Compounds on every future commit. WARNING-level consistent with existing patterns. Counter-objection about intentional catches is handled by exempting commented lines.

---

## Idea 2: Widget Click Regression Guard (Playwright E2E)

### Challenge
**C1: Is Playwright installed in this environment?**
The `autonomous-webapp-test` skill was installed today as a skill file — that's documentation, not an installed browser. There's no evidence Playwright's browser binaries are present. If the tests can't run in CI, they're worse than nothing (false green from skip/missing).

**C2: Widget E2E is hard to test correctly.**
The widget runs in an iframe embedded on an external domain. Testing it end-to-end requires: (a) the backend running, (b) the frontend built, (c) a browser with iframe permissions. This is a medium-complexity test harness, not a "write 3 tests" task.

**C3: Unit tests already exist.**
`test_widget_chat_fallback.py` is 430 lines, committed today. If the widget is already well-unit-tested, the marginal value of E2E is reduced.

**C4: Parking lot ROI 2.0 was computed before the unit tests landed. With 430 lines of unit tests, the ROI may have shifted.**

### Defend
**D1:** The `widget-test` skill (distinct from `autonomous-webapp-test`) exists specifically for testing the embedded widget. It mentions cross-origin embedding and CORS. The infrastructure may be more ready than a raw Playwright install implies.

**D2:** E2E catches integration failures unit tests can't: CSS rendering, the JS load sequence, CORS failures on the actual embed host, DOM interaction bugs. The widget's primary surface is the chat button — a click regression destroys the conversion funnel.

**D3:** Unit tests cover function logic; E2E tests cover the user journey. They're additive, not redundant.

**D4:** Parking lot note says "highest severity." Widget is the primary revenue surface. Severity argument holds regardless of unit coverage.

### Verdict: **WEAKENED**
The idea remains valid (widget is the revenue surface, needs E2E guard), but the Playwright infra uncertainty is a real risk. Running it as a precondition check ("verify Playwright is installed first") before writing tests would prevent orphaned test files — the same class of bug documented in bug-patterns.md. Demote to parking lot with updated note: "Confirm Playwright env before executing."

---

## Idea 3: Ingest 5 Competitor Briefs into KB

### Challenge
**C1: Where are the briefs exactly?**
The commit `b97928a` message says "5 competitor briefs" but I cannot verify the file paths from evidence alone. If they're in `docs/` as markdown files they're easy to ingest. If they're in a different structure, `/kb-ingest` may not work cleanly.

**C2: Are the briefs high-quality?**
The briefs were written during a session in Apr 10. LLM-generated competitive analysis can be superficial or contain hallucinated details. Ingesting low-quality data into the KB creates false confidence.

**C3: KB usage is low — only 4 articles after months of operation.**
If nobody is querying the KB, adding 5 more articles has low compounding value. This could be a vanity metric.

**C4: This is operational/housekeeping. The evidence from the daily log priority list doesn't mention KB ingestion as a priority at all — it was a "consider" in the evening self-improvement section, not a task.**

### Defend
**D1:** Evening review says "consider integrating key findings" — that's the daily monitoring system flagging this. The brief locations are resolvable in 30 seconds (`ls docs/competitive/ 2>/dev/null || grep -r "GoHighLevel" docs/`).

**D2:** Quality concern is valid but manageable: the `/kb-ingest` workflow includes a review step. Briefs can be reviewed before compile.

**D3:** Low KB usage might be caused by low KB content — a chicken/egg problem. 4 articles is not enough to be useful. Adding competitive intelligence directly serves decision-making when evaluating features.

### Verdict: **WEAKENED**
Idea is valid and low-effort, but brief quality/location needs verification first. Treat as a follow-up to "locate and assess briefs" rather than a standalone recommendation. Not the right winner for a run that needs one atomic, evidence-solid recommendation.

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| JS Silent Catch Pre-commit Guard | SURVIVED | Direct evidence, atomic, zero risk, compounds |
| Widget Click Regression Guard | WEAKENED | Valid but Playwright infra uncertain |
| Ingest Competitor Briefs to KB | WEAKENED | Valid but brief quality/location unverified |

**Winner: Idea 1 — JS Silent Catch Pre-commit Guard**
