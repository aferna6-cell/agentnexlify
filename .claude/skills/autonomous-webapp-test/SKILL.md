---
name: autonomous-webapp-test
description: "Use when user says 'test everything' or wants autonomous end-to-end testing of the web app. Claude drives the whole dashboard + widget via Playwright MCP — reads the accessibility tree, clicks every button, fills every form, checks console + network for errors. Returns structured bug report. Type 2 (Product Verification) skill per the 9-type taxonomy."
version: 1.0.0
origin: claude
user_invocable: true
triggers: ["test everything", "autonomous test", "autotest", "full app test", "e2e autonomous", "point claude at the app", "crawl the app", "find all the bugs"]
allowed_tools: ["mcp__playwright__browser_navigate", "mcp__playwright__browser_snapshot", "mcp__playwright__browser_click", "mcp__playwright__browser_type", "mcp__playwright__browser_fill_form", "mcp__playwright__browser_hover", "mcp__playwright__browser_press_key", "mcp__playwright__browser_wait_for", "mcp__playwright__browser_console_messages", "mcp__playwright__browser_network_requests", "mcp__playwright__browser_take_screenshot", "mcp__playwright__browser_evaluate", "mcp__playwright__browser_navigate_back", "mcp__playwright__browser_tabs", "Read", "Write", "Bash"]
effort: high
---

# Autonomous Webapp Test

Point Claude at a running agentnexlify dev server. Claude explores the whole app on its own via Playwright MCP, exercises every feature, captures bugs, returns a structured report.

**No scripts. No maintenance. No fixtures.** One prompt: "test everything."

## When to Use

- Pre-deploy sanity check beyond unit tests
- After a big refactor that could touch UI surfaces you didn't think of
- When a customer reports "something's broken" but doesn't know what
- Weekly cron as a smoke-test replacement for stale Playwright scripts
- Before showing the app to a new tester, to find the rough edges first

## When NOT to Use

- Debugging a specific known bug (use `debug-api` or `systematic-debugging` instead)
- Unit-level testing (use `tdd-workflow`)
- Load/performance testing (Playwright MCP is single-session, not for load)
- Testing production — this skill targets localhost:5173 + localhost:8000, never prod
- When the dev server is down (skill aborts, doesn't try to fix infra)

## Prerequisites

1. Frontend running: `cd frontend && npm run dev` → listening on `http://localhost:5173`
2. Backend running: `uvicorn backend.main:app --reload --port 8000` → `http://localhost:8000`
3. Playwright MCP server available (configured in `.mcp.json` already)
4. A seeded test tenant + valid JWT in `backend/tests/fixtures/` or use a scratch account

## The Crawl Strategy

Claude doesn't follow a pre-written script. It explores like a user:

### Phase 1 — Discover surface (2 min)
1. Navigate to `http://localhost:5173`
2. `browser_snapshot` → read the full accessibility tree
3. Enumerate: sidebar links, buttons, forms, modals, cards, tabs
4. Build a mental map of the nav graph (landing → dashboard → pages)

### Phase 2 — Exercise auth (1 min)
1. Find login form via accessibility tree
2. Fill with test credentials (seeded tenant)
3. Click submit, wait for navigation
4. `browser_console_messages` → flag any JS errors
5. `browser_network_requests` → flag any 4xx/5xx requests

### Phase 3 — Exercise each dashboard page (4-8 min)
For each sidebar link:
1. Click it, wait for navigation
2. Snapshot → enumerate interactive elements
3. For each button/form: hover, then click/fill with realistic values
4. After every action: console check + network check
5. Screenshot if anything looks off (wrong layout, missing data, error text)
6. Navigate back, move to next page

### Phase 4 — Exercise widget (2 min)
1. Open widget embed (`frontend/public/widget/agentnexlify-widget.js` loaded in a test HTML)
2. Open chat
3. Send messages: greeting, factual question, contact info, handoff request
4. Verify responses appear, verify no console errors, verify network 200s

### Phase 5 — Report (1 min)
Structured Markdown report:
```
# Autonomous Test Run — YYYY-MM-DD HH:MM

## Pages tested (N)
- /dashboard — OK
- /leads — OK
- /widget — FAIL (1 issue)
- /billing — OK
...

## Issues found (N)
### CRITICAL
1. file.jsx:line — Description — Screenshot

### HIGH / MEDIUM / LOW
...

## Console errors captured (N)
1. message — source URL — stack

## Network failures (N)
1. URL — status — method — response body (truncated)

## Coverage
- Auth: tested
- Dashboard pages: N/M
- Widget flow: tested
- Forms submitted: N
- Modals opened: N

## Duration: X min
```

## Kickoff Prompt Template

Paste this into Claude Code, adjust the test tenant:

```
Run the autonomous-webapp-test skill against localhost.

Test tenant: <api_key_from_fixtures>
Test email: test+autobot@agentnexlify.com
Test password: <seeded_password>

Scope: full dashboard + widget. Skip the landing page.
Known issues to ignore: <list any pre-filed bugs>
Budget: 10 minutes max wall time.

Exit criteria: structured bug report + console + network dumps +
screenshots of any visual regression. Do NOT commit anything. Do NOT
touch production URLs.
```

## Gotchas

- **Playwright MCP is single-browser-context.** Parallel tab tests will step on each other. Stick to sequential page navigation.
- **Accessibility tree misses custom canvas/webgl.** Recharts, xyflow, and anything drawn on a canvas won't appear in `browser_snapshot`. Screenshot those separately.
- **Dark theme + low-contrast text.** Visual regressions often hide in the dark theme. Force a light-mode screenshot if anything looks off.
- **JWT expiry mid-test.** Dashboard JWT is 24h but dev fixtures may be shorter. If you see a sudden cascade of 401s, re-auth and continue.
- **Stale cache between page navigations.** `browser_navigate` doesn't hard-reload. Use `browser_press_key("F5")` or evaluate `location.reload(true)` when data looks stale.
- **React router swallows errors.** Console shows an error boundary catch, not the real stack. Use `browser_evaluate` to read `window.__NEXT_ERROR__` or React DevTools state.
- **Background API polls fire mid-test.** Dashboard polls `/api/v1/health` + websocket — these will pollute the network log. Filter by path prefix when scanning for failures.
- **Form autofill can leak credentials.** Never paste real tenant credentials. Always use the seeded `test+autobot@` account.
- **Widget runs in iframe cross-origin.** You may need to navigate to the widget's test HTML harness directly (not iframe) to use Playwright tools against it.
- **Don't run against Railway prod.** Hard-code `localhost` in the kickoff prompt. Mixing in the prod URL risks real tenant data contamination.
- **Headless mode doesn't catch all layout bugs.** If visual regression matters, run headful: `browser_navigate` with `headless: false` (Playwright MCP supports this via env var).
- **8 minutes is a soft budget.** If Claude is past 12 minutes, kill the run and see what it found — don't keep waiting.

## Comparison to the iOS tool

The iOS autonomous testing pattern (accessibility tree + screenshots + LLM-driven exploration) maps 1:1 to this skill:

| iOS | Web (this skill) |
|---|---|
| Accessibility tree from iOS simulator | `browser_snapshot` (Playwright a11y tree) |
| Screenshot for UI verification | `browser_take_screenshot` |
| XCTest UI actions | `browser_click`, `browser_type`, `browser_fill_form` |
| Debug logs scan | `browser_console_messages` + `browser_network_requests` |
| Navigate between screens | `browser_navigate`, `browser_navigate_back` |
| Structured bug summary | Report phase output |

The web version is arguably better because the accessibility tree is more structured and the network dump includes full API responses — which iOS tools can't easily grab.

## Files in This Skill

- `SKILL.md` — this file
- `scripts/kickoff.sh` — wrapper that checks prereqs (frontend + backend running, playwright MCP available) and prints the kickoff prompt

## Related

- `widget-test` — focused widget-only testing, checklist-driven
- `e2e-testing` — traditional Playwright scripts (maintenance-heavy; this skill replaces them for smoke runs)
- `verification-loop` — build/test/lint gates (not UI)
- `deploy-workflow` — pre-deploy pipeline (this skill could be a new gate in it)
