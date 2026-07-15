# Nightly Commit Review — 2026-07-15

**Window:** last 24h (since 2026-07-14 ~00:00 UTC)  
**Commits reviewed:** 15  
**Critical issues:** 0  
**Issues filed:** 0  
**Low-risk fixes applied:** 0  
**Status:** PASS — no action required

---

## Commit Triage

### LOW — docs / brain / KB / ops

| SHA | Summary | Risk |
|-----|---------|------|
| `7f497bd` | subconscious run 2026-07-14-pm — referral checklist 10/10 complete | LOW |
| `b08f421` | docs: auto-log bug fix from 82283ea | LOW |
| `4285572` | brain: frontier round 2 (vision, quoting, GEO, evals) | LOW |
| `fbd8318` | brain: mark 6 shipped AI moves + frontier update | LOW |
| `6635a23` | brain: add AI Product Opportunities map | LOW |
| `2dc472a` | kb: knowledge-base graph generator + committed graph | LOW |
| `6a502ef` | kb: frontier AI refresh — model landscape H2 2026 | LOW |
| `811037c` | KB: add frontier_ai discovery category | LOW |
| `30c8191` | ops: morning-digest 2026-07-14 | LOW |
| `5043a59` | brain: scheduled refresh from GitHub + Supabase | LOW |
| `617c2ae` | docs: log migrations 165/166/167 as applied to prod | LOW |
| `886b8f6` | fix: renumber migrations (collision with main) | LOW |
| `66c6898` | Merge remote-tracking branch | LOW |

### LOW — Code cleanup

| SHA | Summary | Risk |
|-----|---------|------|
| `8f4c12e` | fix(voice): remove duplicate KB-grounding block (18 lines, merge collision) | LOW |
| `0a8700f` | feat: legacy reminder job honors appointment_reminders_enabled toggle | LOW |

### MEDIUM — Feature PRs (already merged)

| SHA | Summary | Risk |
|-----|---------|------|
| `82283ea` | Merge PR #430: voice KB dedupe hotfix + brain frontier | MEDIUM |
| `65f5986` | Merge PR #411: pre-launch fixes + Instantly MCP + 6 product moves | MEDIUM |
| `a1a9e1e` | feat(referral+ops): grant email, demo widget seeds, error-sink digest (#429) | MEDIUM |
| `64e16f2` | feat: ship 6 product moves (proactive widget, reminders, confidence gate, KB voice, review AI) | MEDIUM |

### MEDIUM — Big ship (PR #431)

| SHA | Summary | Risk |
|-----|---------|------|
| `a485743` | Ship recommended builds: Sonnet 5, Bot-Health, photo-triage/quoting, attribution, guard (#431) | MEDIUM |

---

## Deep Review: a485743 (PR #431)

Largest commit this window. 38 files, +3,413 lines. New services: `bot_health`, `photo_triage`, `quote_builder`, `widget_guard`, `attribution`. New routers: `bot_health`, `intake_ai`. Migrations 170–172 applied.

### Checks run

| Check | Result |
|-------|--------|
| `widget/` ↔ `frontend/public/widget/` byte-identical | ✅ PASS |
| `widget/` ↔ `landing-page-v2/widget/` byte-identical | ✅ PASS |
| `from __future__ import annotations` in new FastAPI files | ✅ NONE |
| `tenant_id` on `leads`/`conversations` tables | ✅ NONE — uses `client_id` correctly |
| `lead_stage` / `service_interest` column refs | ✅ NONE |
| New routers registered in `main.py` | ✅ both `bot_health.router` + `intake_ai.router` |
| Model IDs | ✅ `claude-haiku-4-5-20251001`, `claude-sonnet-5` — both valid |
| `widget_guard` fail-open contract | ✅ timeout=8s, all error paths allow=True |
| `quote_builder` no invented prices guard (`_sanitize_tier`) | ✅ present |
| `attribution.py` no-I/O sanitize helper | ✅ clean |

### Minor LOW note (no fix required)

`backend/services/widget_guard.py:141` — `_SESSION_TURN_COUNTS: dict[str, int]` grows indefinitely per worker. Over weeks of continuous uptime, stale session IDs accumulate (each is just a string key → negligible per-entry size, but unbounded). Not an immediate problem; a TTL-based LRU cache would be cleaner. Log for future improvement.

---

## Critical Invariants — All Passed

- `client_id` (not `tenant_id`) on `leads` + `conversations` ✅
- `status` (not `lead_stage`) for lead status ✅
- No `from __future__ import annotations` in FastAPI files ✅
- Widget JS byte-identical across all 3 locations ✅
- No secrets in commits ✅
- Schema changes via numbered migration files ✅ (170, 171, 172)

---

## Fixes Applied

None. No LOW-risk bugs found requiring auto-fix.

---

## Summary

Clean night. The big PR #431 shipped 5 new backend services + 2 routers with solid test coverage (77% → 86%) and passed all critical invariant checks. No schema discipline violations, no forbidden imports, widget byte-identical everywhere. Only note is an unbounded in-memory dict in widget_guard that's worth cleaning up in a future sprint.
