# Improvement Backlog — 2026-04-25-pm

## Active
- **Wire check_project_invariants.py into pre-commit** — Call `python3 scripts/check_project_invariants.py` from `scripts/hooks/pre-commit`. Blocks commits with naming violations. S-effort, zero deps. See `winning-concept.md`.

## Implementation Lag Alert — MORATORIUM TRIGGERED
Run 8 is the run where the moratorium threshold is met (per run 7 mandate: "escalate directly if not by run 8").

| Winner | Run | Days Pending | Status |
|--------|-----|-------------|--------|
| Add Lead Source Analytics Chart | 2 | 19+ | unimplemented |
| JS Silent Catch Pre-commit Guard | 3 | 14+ | **unimplemented (escalated)** |
| AI-to-Human Handoff (Explicit Trigger v1) | 4 | 9+ | unimplemented |
| Widget 3-Copy Sync Guard | 7 | 1+ | unimplemented (script not created) |
| widget_helpers split QA | 5 | 7+ | implemented_unverified |

→ `moratorium_config.moratorium_active = true` set in governance.json.
→ Run 9 should synthesize from the oldest unimplemented winner, not generate fresh ideas, UNLESS 2+ items above are cleared.

## Parking Lot

- **widget_helpers Split Smoke Tests** [ROI 2.0] — WEAKENED this run. Only `implemented_unverified` governance item. Write `backend/tests/test_widget_helpers_smoke.py`: import each of 3 split modules + call one function. Promote to run 9 winner if widget Hot-Zone Regression Suite Playwright path is confirmed.

- **JS Silent Catch Pre-commit Guard** [ROI 2.4] — Run 3 winner, 14+ days. Still pending_approval. Add Check 9 to `scripts/hooks/pre-commit`. Known violations: `AuthContext.jsx:89`, `MarketingDashboardPage.jsx:96`, `LocalSEOPage.jsx:262`. Moratorium forces implementation before run 9.

- **Widget 3-Copy Sync Guard** [ROI 2.3] — Run 7 winner. `scripts/check-widget-sync.sh` not created. `037865f` touched all 3 widget copies (likely in sync now — good time to lock in guard). S-effort.

- **AI-to-Human Handoff (Explicit Trigger v1)** [ROI 3.0] — Run 4 winner. 1.5-2 day build. Infrastructure exists. Critical gap all 7 industries. Highest ROI in backlog.

- **Add Lead Source Analytics Chart** [ROI 2.67] — Run 2 winner. source column exists, Recharts installed. Low effort. Oldest unimplemented winner.

- **Widget Hot-Zone Regression Suite** [ROI 2.1] — Still blocked on Playwright. Confirm `npx playwright install` then promote.

- **Bug-patterns.md Split by Month** [ROI 1.8] — 2,204 lines, auto-logger appends daily. Split into monthly files + INDEX.md. M-effort.

- **Stripe Billing Smoke Tests** [ROI 2.2] — 821f660 touched 16 billing files, zero test coverage. Frame as billing constants + plan-tier contract tests.

- **Moratorium Governance Self-Enforcing Threshold** — Add `moratorium_config: { max_pending_approvals: 3, max_pending_age_days: 14 }` to governance.json. Auto-triggers moratorium when threshold exceeded. Already partially implemented this run via manual flag.

- **Managed Agents Automated Integration Tests** [ROI 1.5] — 5 HTTP endpoints, test_managed_agents.py exists but limited coverage.

- **Migration Safety Net Pre-Push Check** [ROI 1.8] — Add after apply-migration helper exists.

- **Small Business SaaS KB Category Seed** [ROI 1.5] — `/kb-discover` on 3 SMB queries. KB INDEX shows sparse coverage.

- **Fix health-check.sh morning grep drift** [ROI 1.3] — morning=0, evening=9 on same script. find vs glob expansion.

## Rejected This Run
_(No ideas killed outright — Idea 1 survived, Ideas 2 and 3 weakened to parking lot.)_

## Questions for Run 9
1. **Has check_project_invariants.py been wired into pre-commit (this run's winner)?** Verify with `grep "check_project_invariants" scripts/hooks/pre-commit`.
2. **Are any pending winners now implemented?** Count pending approvals in governance.json. If ≤3, lift moratorium.
3. **Is Playwright installed?** `npx playwright install` — open since run 2. Required for Widget Hot-Zone Regression Suite.
4. **Has the compromised API key been rotated?** Day 22+. This is HUMAN ACTION REQUIRED — not agent-actionable.
5. **Is check_project_invariants.py producing false positives?** Check git log for any "revert" commits related to the invariant guard.
