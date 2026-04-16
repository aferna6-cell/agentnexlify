# Idea 2: Silent Frontend Error Audit + React Error Boundary

**Category:** reliability / dx
**Effort:** low (1–2 days)
**Impact:** Medium — removes 62 blind spots that mask real production errors

---

## Hypothesis

Replacing 62 silent `.catch(() => {})` blocks with meaningful error handling (toast notifications + console.error) and wrapping critical dashboard pages in React ErrorBoundary components will surface errors that are currently invisible. This directly enables faster debugging and prevents users from seeing blank pages or stale data without knowing why.

---

## Evidence

1. `docs/daily-logs/2026-04-03.md` line 9: "4 files with silent `.catch(() => {})` — onboarding.js, WizardStepEmbed.jsx, MarketingCampaignsPage.jsx, ClientLoginPage.jsx" — carried for 3+ consecutive days as a P2 task, never actioned.
2. Same log: "62 total `.catch(() =>` occurrences across 35 files" — the 4 fully silent ones are the worst, but 62 total means the entire frontend is running nearly blind.
3. Bug pattern from bug-patterns.md: "Lead capture silently failing — tenant_id vs client_id" — the same swallowed-error pattern at the backend level caused data loss for an unknown period. The same failure mode exists in the frontend.
4. `docs/dev-knowledge/test-coverage.md` line 52: "Frontend React components — no Vitest/Jest setup" — no automated test coverage means manual review is the only safety net, and silent catches defeat even that.
5. `docs/daily-logs/2026-04-02.md` — onboarding wizard was shipped with 27 commits in one day; velocity that high increases the chance that catch blocks were added hastily.

---

## Implementation Sketch (no code)

1. **Grep audit** — Find all `.catch(() => {})` and `.catch(err => {})` with empty bodies in `frontend/src/`
2. **Upgrade each to** `.catch(err => { console.error('[context]', err); toast.error('Something went wrong') })`
3. **Add ErrorBoundary wrapper** around the 3 highest-risk page groups (widget config, leads, appointments)
4. **Fix the 4 fully-silent files** first (highest priority): onboarding.js, WizardStepEmbed.jsx, MarketingCampaignsPage.jsx, ClientLoginPage.jsx
5. **No new dependencies** — use existing toast library already in use

---

## Success Metric

- 0 fully-silent `.catch(() => {})` remaining in frontend/src/
- ErrorBoundary wraps at least the top 5 page components
- Daily health check `Silent frontend .catch(() => {})` count drops from 4 to 0
