# Improvement Candidates — 2026-04-06

## Evidence Summary

- **Centralized LLM Runtime** landed (commit a00e1f3, 2026-04-05): 19 files changed, all AI calls routed through `backend/services/llm_runtime.py`. Selective retry added (commit efa18d8). Observability tracing improved (commit 6accaba). Parser seams extracted for testability (commits c2bdeed, dc3ac62).
- **Onboarding sprint** shipped (commits 952a609, 5225763, fbd8de2): full flow, mobile responsive, nightly E2E smoke tests, resume banner, Welcome Series email auto-creation.
- **Widget fix** (commit fdcc3b5): widget not opening on click + 3 pending migrations applied + 59 tests added.
- **Content Repurposer** shipped (commits 705e8ab→c600cda): JSON repair for truncated responses was needed immediately.
- **Bug patterns doc** shows: bare-except silent failures are recurring (#1 root cause in 3+ bugs), model ID drift (wrong model ID caused all AI to fall back), and column-name mismatches cause silent zero-row matches.
- **Customer gaps**: "Lead source analytics" is open (low effort), "AI-to-human handoff" is open (medium) — but handoff is in rejected_paths.
- **Previous winner** (run 2026-04-04): skill update for stale skills — diversify away from workflow this run.

---

### Idea 1: Add LLM Runtime Observability Dashboard to Agent Control Center

**Evidence:**
- 3 consecutive commits (6accaba, fa6a3e4, dc3ac62) focused on LLM runtime tracing and observability in the last 3 days. The centralization work explicitly added tracing but there is no UI surface for it.
- `llm_runtime.py` now handles all AI calls (19 files migrated, commit a00e1f3) — making it the single point where latency, retry counts, token usage, and errors can be surfaced.
- Commit 6accaba message: "observability: improve centralized llm runtime tracing" — tracing exists, dashboard does not.
- Bug pattern: "Widget model ID mismatch" (2026-03) caused ALL AI responses to fail silently for an unknown period. A dashboard showing per-model call counts would have caught this in minutes instead of days.

**Action:** Add a "LLM Runtime" panel to the Agent Control Center page (`frontend/src/pages/AgentControlCenter.jsx` or equivalent) that reads from `llm_runtime.py` tracing data. Show: calls/hour by model, p50/p95 latency, retry rate, error rate, top failing endpoints. Backend: new `/api/llm-stats` endpoint reading from existing tracing logs.

**Impact:** Cuts mean time to detect model/AI failures from days to minutes. Directly addresses the model-ID-mismatch failure class. Gives developers evidence to tune retry policy.

**Category:** operational

---

### Idea 2: Add Lead Source Analytics Dashboard Panel

**Evidence:**
- `customer-gaps.md` explicitly lists "Lead source analytics" as an Open Cross-Industry gap: "Source column exists, no dashboard visualization" — rated Low Effort.
- `leads` table has a `source` column (per schema log and CLAUDE.md). It is written during capture but never visualized.
- 7 days of commits show zero UI work touching lead analytics; the onboarding and content repurposer were the focus.
- Cross-industry impact: affects all 6 business types in simulation findings (cycle 122).

**Action:** Add a "Lead Sources" chart to the existing Analytics or Leads dashboard page using Recharts (already a dependency). Show a pie/donut chart of lead counts by source (widget, manual, import, etc.). Backend query: `SELECT source, COUNT(*) FROM leads WHERE client_id = $tenant_id GROUP BY source`.

**Impact:** Closes a known product gap with low effort. Gives business owners direct ROI visibility ("30% of leads came from the widget"). Reduces churn by surfacing widget value.

**Category:** customer_value

---

### Idea 3: Add E2E Smoke Test Coverage for Onboarding AI Parser

**Evidence:**
- Commit dc3ac62: "test: extract onboarding ai parser seam and document llm runtime ops" — the seam was extracted but coverage is focused on unit-level parser repair, not end-to-end onboarding flow.
- Commit 952a609: "feat: onboarding flow + mobile responsive + nightly E2E smoke tests" — E2E smoke tests were added, but the AI-parsing path (where Claude generates business config from the onboarding form) is the highest-risk path and most likely to silently degrade.
- Bug pattern: "JSON repair for truncated repurpose responses" (commit c600cda) shows AI-generated JSON can be malformed. If onboarding AI output is malformed, the tenant gets a broken widget config with no visible error.
- Content repurposer already needed `max_tokens` increase and JSON repair. Onboarding uses the same pattern.

**Action:** Add a pytest fixture that mocks the Claude API response with known-bad JSON (truncated, extra text wrapper, null fields) and verifies the onboarding parser either fixes it or returns a safe default. Add these as `tests/test_onboarding_parser_edge_cases.py`. 3-5 parametrized test cases covering the failure modes already observed in `content_repurposer.py`.

**Impact:** Prevents silent onboarding failures for new tenants. The onboarding path is first-impression critical — a bad parse here means a broken widget from day one.

**Category:** code_health

---

### Idea 4: Add Retry/Circuit-Breaker Status to Centralized LLM Runtime Docs

**Evidence:**
- Commit efa18d8: "feat: add selective retry policy for centralized ai runtime" — retry policy was added but the CLAUDE.md and dev-knowledge docs have no documentation on which endpoints retry, with what policy, and what the circuit-breaker thresholds are.
- `backend/services/retry.py` exists (listed in services directory) but there's no reference to it in CLAUDE.md or any skill.
- Bug patterns show 2+ incidents where silent failures were the root cause. A documented retry policy helps developers reason about failure modes and prevents over-retrying expensive Opus calls.
- The `ai-feature-pattern` skill (.claude/skills/) guides AI feature building but likely has no retry/circuit-breaker guidance since the service was just centralized.

**Action:** Update `backend/services/llm_runtime.py` docstring and add a section to `.claude/skills/ai-feature-pattern/SKILL.md` describing: retry strategy (which calls retry, how many times, backoff), circuit-breaker thresholds, and which model tier (sonnet vs opus) to use for which endpoint type. Also add one line to CLAUDE.md under Model Selection.

**Impact:** Prevents future developers from accidentally bypassing retry logic or creating duplicate retry layers. Reduces risk of over-retrying Opus-tier calls (costly). Adds ~30min of work, prevents hours of debugging.

**Category:** workflow

---

### Idea 5: Add Widget "Not Opening" Regression Guard to E2E Suite

**Evidence:**
- Commit fdcc3b5 (2026-04-05): "fix: widget not opening on click" — the chat widget silently broke (button click not registering) and required a hotfix. This is the most user-visible failure mode possible: the entire product's front door stopped working.
- Nightly E2E smoke tests were added in commit 952a609, but if the widget click bug was not caught by them (it required a hotfix after they were added), they lack a click-open assertion.
- Bug patterns: "Conversation memory not working" (2025) and widget-test.html data-api-base bug are prior widget regressions — this is a recurring category.
- Widget JS must be identical in `widget/` and `frontend/public/widget/` (CLAUDE.md rule) — any divergence is a regression vector.

**Action:** Add a Playwright E2E assertion to the nightly smoke tests that: (1) loads a test page with the widget embed, (2) clicks the chat button, (3) asserts the chat window opens within 1000ms, (4) sends a message, (5) asserts a response arrives. This test should gate nightly CI and fail if the widget button click is broken.

**Impact:** Directly prevents recurrence of the widget-not-opening regression. The widget is the #1 revenue path — a broken widget means zero leads captured. CI gate = immediate detection instead of customer complaint.

**Category:** code_health
