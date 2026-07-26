# Run 103 — Candidate Ideas (2026-07-26)

## Evidence Base
- 3 consecutive quiet nightly days (Jul 24–26): no feature commits, no issues filed
- GH #500 (Actions spending limit) open 6+ days — ALL GitHub Actions dark since 2026-07-20
- GH #399 (AUTOPILOT_GH_TOKEN) expired — 30 ai-ready issues stalled since 2026-07-04
- Step 9G present on branch `subconscious/run-101-step-9g` (7 occurrences), NOT merged to main
- KB fresh: 2026-07-23, 124 articles, within 7-day threshold
- fastapi<0.136 cap in requirements.txt, comment says "0.136.x incompatible with pinned starlette pair"
- Keys Koffee widget: silent 39+ days, no business hours configured, no bookings
- email_sequences split DONE (ab1a7c2); 8 pre-existing auth test failures remain unclassified
- Managed Agents rollout plan created (ab1a7c2) but Phase 0 NOT started
- PR #577 (this PR) still open/draft — Step 9G awaiting human merge

---

## Idea 1: Step 9H — Nightly GH Actions Spending-Limit Heartbeat
**Category:** Operational
**Evidence:** GH #500 open 6+ days. 5 systems dark: autopilot loop, KB autopopulate, PR CI, issue-to-pr-loop, Dependabot. 30 ai-ready issues stalled. Step 9G will fail silently when KB goes stale because `gh workflow run` hits the spending limit. No automated accountability loop targeting #500.
**Mechanism:** Add Step 9H bash block to nightly SKILL.md (same channel as Steps 9B–9G). Checks `gh run list --limit 3 --json conclusion,createdAt` — if no successful run in last 7 days, post comment on GH #500 with: days elapsed, systems blocked list, engineering-hours opportunity cost (30 issues × 2h = 60h), billing settings URL. Gate: skip if a successful run appears in last 24h (issue resolved).
**Confidence:** HIGH — gh list command is read-only (no auth beyond PAT), comment-posting via AUTOPILOT_GH_TOKEN (if rotated) or flag as human-manual. Proven SKILL.md channel.

---

## Idea 2: fastapi Security Cap Analysis + GH Issue
**Category:** Code Health
**Evidence:** `fastapi>=0.115.6,<0.136` has been capped since GH #265 (2026-05+). Starlette is the noted compat constraint. Latest fastapi is 0.115.x (no 0.136 release yet per PyPI — cap may be precautionary). Security CVEs in unpinned fastapi versions accumulate; pinning to <0.136 without knowing what 0.136 changes means the cap may be arbitrary.
**Mechanism:** Read requirements.txt comment, check pypi.org/project/fastapi for latest stable, verify the starlette compat note, file GH issue with: current version in use, latest available, reason for cap from comment, recommended investigation path and risk classification.
**Confidence:** MEDIUM — cap comment says "fastapi 0.136.x incompatible with pinned starlette pair" but 0.136.x doesn't appear to exist yet on PyPI; cap may be prophylactic. Needs web verification to confirm whether the cap is blocking real security patches.

---

## Idea 3: Keys Koffee Silent Widget Diagnostic GH Issue
**Category:** Customer Value
**Evidence:** Keys Koffee widget silent 39+ days. No business hours configured. No bookings. Widget silence = no leads captured = 0 ROI for tenant. 39 days with no conversation is a strong churn signal. Customer may have already churned or may be a free/test account. No GH issue filed.
**Mechanism:** File GH issue `[Keys Koffee] Widget silent 39+ days — investigation checklist` with specific diagnostic steps: (a) query `widget_configs` for Keys Koffee tenant — check `active=true`, `greeting_message` set, `booking_enabled`, `booking_link` not empty; (b) check `conversations` table for last row for this tenant; (c) check if there's an API error in the last conversation; (d) check if their subscription is active.
**Confidence:** HIGH — GH issue creation is a safe autonomous action. Steps are deterministic. Brings the silent widget to human attention with a concrete investigation plan.

---

## Idea 4: Managed Agents Phase 0 Kickoff GH Issue
**Category:** Customer Value / Operational
**Evidence:** `plans/managed-agents-rollout_plan.md` created (ab1a7c2) but Phase 0 not started. All run endpoints return 503. `managed_agents_registry.py` references `MANAGED_AGENTS_ENVIRONMENT_ID` which is not set in Railway. The rollout plan exists but no tracking issue exists to push Phase 0 forward.
**Mechanism:** File GH issue `[Managed Agents] Phase 0 kickoff checklist` with concrete steps: (1) provision Anthropic Managed Agents environment via platform.anthropic.com, (2) set MANAGED_AGENTS_ENVIRONMENT_ID + LEAD_QUALIFIER_AGENT_ID in Railway env vars, (3) run smoke test: `GET /api/managed-agents/health` should return 200, (4) test lead qualifier on one real tenant. Links to rollout plan.
**Confidence:** HIGH — GH issue only; no code change. Directly tracks the next growth lever.

---

## Idea 5: email_sequences Auth Test Failures — Classification GH Issue
**Category:** Code Health
**Evidence:** 8 pre-existing auth test failures in email_sequences suite flagged in nightly review (ab1a7c2) as "pre-existing auth fixture issues (reproduce on pre-split HEAD), not regressions." But "pre-existing" ≠ acceptable. 8 failing tests in CI = 8 regression blind spots. No GH issue tracking them. The split into email_crud/enrollment/processor makes the failure locus clearer now — fixture vs real auth bug can be distinguished.
**Mechanism:** File GH issue `[email_sequences] 8 pre-existing auth test failures — classify and fix` with: test names from the failure output, hypothesis (auth fixture not setting up test tenant correctly vs real multi-tenant auth bug), proposed fix path (mock the auth fixtures properly per pattern in other routers), and acceptance criteria (8 tests green).
**Confidence:** HIGH — GH issue only. The test failures are real and tracked. Naming them in a GH issue forces classification and eventual fix.
