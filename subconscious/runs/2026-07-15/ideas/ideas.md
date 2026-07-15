# Run 94 Ideas — 2026-07-15

## Evidence Summary

**Primary:** nightly-2026-07-15 flagged `backend/services/widget_guard.py:141` — `_SESSION_TURN_COUNTS: dict[str, int]` grows indefinitely per worker. Stale session IDs accumulate with no eviction. Not immediately breaking but unbounded over weeks of continuous uptime.

**PR #431 context (a485743, shipped yesterday):** 5 new backend services (bot_health, photo_triage, quote_builder, widget_guard, attribution). No BotHealthPage.jsx or AttributionPage.jsx exists yet. Tests 77% → 86%.

**Mandate carry-forward:** GH #413 (REFERRAL_REWARD_ENABLED) — still 0 human responses, Day 23. Keys Koffee GH #415 — still 0 human responses. GH #399 + #403 — OPEN Day 12+, 40 ai-ready issues blocked, KB 72+ days stale. widget_guard wiring: CONFIRMED (widget_chat.py lines 34 + 684) — Bonus A resolved, no issue needed.

---

### Idea 1: Fix widget_guard._SESSION_TURN_COUNTS unbounded in-memory dict
**Evidence:** nightly-2026-07-15.md:77 — named exact file + line (`backend/services/widget_guard.py:141`). PR #431 shipped widget_guard.py yesterday — code is fresh, minimal re-reading needed. No TTL or eviction logic currently present.
**Action:** Replace `_SESSION_TURN_COUNTS: dict[str, int] = {}` with a bounded structure — either `cachetools.TTLCache(maxsize=10_000, ttl=3600)` (if cachetools available) or a hand-rolled `dict` with `_SESSION_LAST_SEEN: dict[str, float]` + periodic eviction in `check_turn_budget()`. Add `requirements.txt` entry if needed.
**Impact:** Eliminates unbounded memory growth in long-running Railway workers. Prevents OOM in high-traffic scenarios. Small autonomous-executable fix (nightly code-change channel).
**Category:** code_health

---

### Idea 2: Add BotHealthPage.jsx dashboard frontend
**Evidence:** PR #431 shipped `backend/services/bot_health.py` (329 lines) + `backend/routers/bot_health.py` + migration 170 — full backend, zero frontend. No `/bot-health` route in `frontend/src/App.jsx`. User has no way to see bot health scores in the dashboard.
**Action:** Create `frontend/src/pages/BotHealthPage.jsx` showing per-tenant bot health score, issue timeline, and recommended fixes. Add route in `App.jsx` + sidebar entry in `Sidebar.jsx`.
**Impact:** Makes the biggest new service from PR #431 visible to operators. Potential upsell: tenant health monitoring dashboard as premium feature.
**Category:** customer_value

---

### Idea 3: File GH issue for attribution dashboard frontend gap
**Evidence:** PR #431 shipped `backend/services/attribution.py` + migration 172 (lead attribution schema). `docs/dev-knowledge/customer-gaps.md` lists "Lead source analytics" as High Priority, Low Effort. No `AttributionPage.jsx` exists. Attribution data is in prod DB but invisible to users.
**Action:** File single GH issue with `ai-ready` label: "feat(frontend): attribution dashboard — surface lead source breakdown from attribution.py + migration 172." Include: acceptance criteria, files to create (`AttributionPage.jsx`, route + sidebar entry), API endpoint reference (`/api/attribution/summary`).
**Impact:** Queues attribution visualization for issue-to-pr-loop when GH #403 resolves. Closes a documented High Priority customer gap. Low effort to file; high leverage when loop resumes.
**Category:** workflow_efficiency

---

### Idea 4: Add Step 9F to nightly-commit-review SKILL.md — infrastructure issue staleness check
**Evidence:** GH #399 + #403 both open Day 12+. 40 ai-ready issues blocked. KB 72+ days stale. Current nightly review (Steps 9A-9E) monitors commits, widget sync, credential rotation, booking audit, and test coverage — but does NOT check for stale infrastructure-blocking GH issues. The pattern: issues go stale for 2+ weeks before subconscious notices (only twice-daily).
**Action:** Add Step 9F to `.claude/skills/nightly-commit-review/SKILL.md`: "Check list of infrastructure-blocking issues (GH #399, #403, and any labeled `infra-blocker`). If any open and >7 days old: post escalation comment with current staleness count."
**Impact:** Escalates infrastructure blockers daily (not just twice-daily via subconscious). First escalation catches Day 7 instead of Day 12+. Compounds prior Steps 9A-9E pattern.
**Category:** workflow_efficiency

---

### Idea 5: Add manual KB refresh command for headless sessions
**Evidence:** KB 72+ days stale (last compiled 2026-05-05). GH #403 (ANTHROPIC_API_KEY in GH Actions) blocks `kb-autopopulate.sh` via CI. Six new wiki articles added manually won't appear in pgvector semantic search until recompile. The blocker is CI-only; local environment has API key available.
**Action:** Write `scripts/kb-refresh-local.sh` that calls the same compile pipeline as `kb-autopopulate.sh` but runs in the local Railway session environment (where API key is set). Add `npm run kb:refresh-local` script to `package.json`.
**Impact:** Unsticks KB semantic search for all sessions while GH #403 awaits human resolution. 114 articles + 6 manual additions become searchable again. Autonomous-executable (no human approval needed).
**Category:** operational
