# Handoff — 2026-04-16 post-analytics-split session

**Paste into a fresh chat to continue.** Session ran from codebase analysis → lead-parser Phase 4b cleanup + Phase 5 rollout audit → analytics router split → HTTP smoke test → prod verification. All 4 commits live on main. Next session's job is the remaining HIGH-priority items.

---

## 1. What we were working on

Close out the open items surfaced in [audits/audit-architecture-2026-04-16.md](../audits/audit-architecture-2026-04-16.md). The last session shipped 4 commits and left the god-class backlog shorter by one file. Next session owes: auth router split, Phase 5 rollout flip, widget_helpers split, scheduled_jobs split.

## 2. Decisions made last session

| # | Decision | Why |
|---|---|---|
| 1 | Lead-parser Phase 4b — tag regex-origin leads `enrichment_source='regex'` | Migration 105 documented `'regex' \| 'ai' \| NULL` but code only wrote `'ai'`; dashboard regex-count was silently 0. Fix in widget_helpers.py:1239. |
| 2 | Do NOT tag `'regex'` on update path — only on INSERT | Preserves first-writer-wins; update path runs for existing AI-enriched leads and would clobber `'ai'` tag. |
| 3 | Analytics router split via package + shim pattern, mirrored `automation_engine` split (754a02c) | Proven pattern. 2,023 lines → 7 files, 14 endpoints preserved. |
| 4 | `dashboard.py` (628) + `control_center.py` (606) intentionally above 600-line threshold | Each is one concern. Splitting further = over-abstraction. Re-audit later if needed. |
| 5 | `.venv/Scripts/python.exe` is canonical for local pytest; system `python` is Python 3.14 missing google-auth | Installed pytest + pytest-asyncio into .venv this session. Plan file ghost-blocker note (pyiceberg) corrected. |
| 6 | Push direct to main (no PR) | Project norm per recent git log (`3612c2d chore(ai): auto-commit`). User confirmed this session. |
| 7 | Em-dash daily_briefing test failure spawned as separate task; auto-fixed by spawned agent (commit 8449c0a) | Out-of-scope for lead-parser work. Cross-platform `%-I` strftime issue. |

## 3. Files changed + key paths (this session's 3 commits on main)

### [888cc35](https://github.com/aferna6-cell/agentnexlify/commit/888cc35) — Regex tag + Phase 5 rollout audit
- [backend/routers/widget_helpers.py:1239](../backend/routers/widget_helpers.py) — `"enrichment_source": "regex"` added to `_capture_leads_from_session` insert payload
- [backend/tests/test_lead_regex_tag.py](../backend/tests/test_lead_regex_tag.py) — new regression test (asserts insert payload contract; patches downstream hooks; runs via .venv stand-alone)
- [audits/audit-lead-parser-rollout-2026-04-16.md](../audits/audit-lead-parser-rollout-2026-04-16.md) — Phase 5 runbook: MTOptions flag-flip SQL, 24h monitor queries, success gates, rollback

### [1f69417](https://github.com/aferna6-cell/agentnexlify/commit/1f69417) — Analytics router split
- Deleted `backend/routers/analytics.py` (2,023 lines)
- Created package `backend/routers/analytics/` with 7 files:
  - `__init__.py` (16 LOC) — combines 5 sub-routers under `prefix="/api/v1/analytics"`, exposes `.router` for `main.py:746`
  - `_common.py` (181 LOC) — shared cache, constants, helpers (`_period_to_days`, `_date_range`, `_pct_change`, etc.)
  - `dashboard.py` (628 LOC) — `/overview`, `/conversations`, `/leads`, `/widget`, `/health`, `/snapshot`
  - `operations.py` (304 LOC) — `/response-times`, `/missed-opportunities`, `/missed-calls`
  - `insights.py` (331 LOC) — `/ai-insights`, `/lead-sources`, `/kpi-deltas`
  - `control_center.py` (606 LOC) — `/control-center`
  - `recovery.py` (86 LOC) — `/recovery-stats`

### [35bb66e](https://github.com/aferna6-cell/agentnexlify/commit/35bb66e) — Smoke test
- [backend/tests/test_analytics_split_smoke.py](../backend/tests/test_analytics_split_smoke.py) — 15 tests via ASGI client + JWT auth, asserts route count == 14 + each path reaches handler (no 404/401/403/405)

### Related (not mine, landed same day): [8449c0a](https://github.com/aferna6-cell/agentnexlify/commit/8449c0a) — em-dash cross-platform fix

### Memory file landed this session
- `~/.claude/projects/C--Users-aidan-Downloads-agentnexlify-main/memory/reference_dev_env.md` + MEMORY.md

## 4. Open questions / blockers

### Must resolve before Phase 5 rollout execution
- **MTOptions `client_id` UUID** — needed to flip the flag. Check via `SELECT id, business_name FROM clients WHERE business_name ILIKE '%mtoption%';` in Supabase SQL editor or via mcp__supabase__execute_sql. Runbook is in the audit doc.

### Architecture hotspots still breaching Rule 9 (>600 lines)
| File | Lines | Type | Risk if split |
|---|---|---|---|
| `backend/routers/auth.py` | 1,896 | **SECURITY-CRITICAL** — JWT validation + branding co-located | HIGH — do NOT refactor casually. Needs grill-me + ultrareview. |
| `backend/routers/widget_helpers.py` | 1,632 (approx, just added 4 lines) | Mixed — regex parser + enrichment helper + chat history + capture flow | MEDIUM — touched recently, contract is tested |
| `backend/routers/local_seo.py` | 1,552 | Local SEO endpoint cluster | LOW — contained surface |
| `backend/services/automation/scheduled_jobs.py` | 2,024 | 13 send/check cron functions (newly split out from automation_engine 2026-04-16) | LOW — already clean split by concern, could further divide by send-type |

### Minor / speculative
- `backend/routers/analytics/dashboard.py` (628) and `control_center.py` (606) slightly over Rule 9 threshold. Acceptable — one concern each. Future audit may split dashboard → summary + entities.
- `docs/dev-knowledge/schema-log.md` last snapshot stops around migration 028 per earlier read. Live state is migration 105. Worth a reconciliation pass someday.
- `backend/tests/` pytest.ini emits `PytestConfigWarning: Unknown config option: timeout` — either install `pytest-timeout` or delete the option.

## 5. Concrete next steps (pick one to start)

### Option A — Auth router split (HIGH impact, HIGH risk)
Mirror the analytics split pattern. `backend/routers/auth.py` 1,896 lines → package `backend/routers/auth/` with sub-modules:
- `auth/__init__.py` — combines sub-routers, exposes `.router` + `_get_current_tenant` dependency (many files import this by name — preserve the export)
- `auth/login.py` — login, logout, token refresh
- `auth/branding.py` — widget_config, tenant branding, `update_widget_config`
- `auth/_deps.py` — `_get_current_tenant`, `verify_tenant` wrappers, JWT helpers

**MUST-DO gates before touching auth:**
1. Grill-me skill (security-critical = mandatory 40+ Q walkthrough per .claude/rules/daily-skills.md)
2. `grep -rn "from backend.routers.auth import" backend/` → list every importer of symbols (not just `router`)
3. Preserve `_get_current_tenant` re-export — it's imported by every analytics sub-router and likely many others
4. `/ultrareview` before commit (rules/ultrareview.md — mandatory for auth/tenant code)
5. Full pytest must stay green (190/0/24)

### Option B — Phase 5 lead-parser rollout (ops)
1. Look up MTOptions client_id (see above)
2. Flip flag: `UPDATE widget_configs SET enable_structured_lead_parser = true WHERE client_id = '<mtoptions>'`
3. Watch 24h per queries in [audits/audit-lead-parser-rollout-2026-04-16.md](../audits/audit-lead-parser-rollout-2026-04-16.md)
4. Gate on success metrics (≥95% lead-field completion, 0 crash delta, cost ≤$1.50/tenant/mo)
5. Expand to 4 remaining testers if green

### Option C — widget_helpers split (MEDIUM impact)
`backend/routers/widget_helpers.py` 1,632 lines. Natural split: chat history loader / regex parser / enrichment helper / lead capture / notifications. Has tests already covering enrichment + regex tag → safe refactor surface.

### Option D — scheduled_jobs further split (LOW impact, clean)
`backend/services/automation/scheduled_jobs.py` 2,024 lines, 13 functions. Split by send-type: appointment reminders / marketing (digest, intelligence briefs) / reviews (CSAT, review req) / invoice (reminders, recurring) / onboarding / birthday. Lowest risk — pure mechanical.

### Recommended sequence
**C → D → A → B.** Reasons:
- C + D are mechanical refactors, low-risk, get 2 more files out of >600 territory
- A last because it's security-critical — do it after you've warmed up on the safer splits
- B runs in parallel with any of the above — it's ops, not code

## 6. How to resume

1. Start fresh chat
2. Paste this doc's Section 1 + 4 + 5 (or just link to `.claude/agent-comms/handoff-2026-04-16-post-analytics-split.md`)
3. Use `.venv/Scripts/python.exe -m pytest backend/tests/ -q` as the local gate (should be 190 passed / 24 skipped / 0 failed on clean main)
4. Prod smoke probe still works: `httpx.get('https://agentnexlify-production.up.railway.app/api/health')` → 200

## 7. Guardrails carried forward (don't re-learn)

- Push direct to main (project norm)
- Caveman mode default
- `client_id` not `tenant_id` for leads + conversations
- No `from __future__ import annotations` in any FastAPI router file
- Shim-and-package split pattern works: see `backend/services/automation/` + `backend/services/automation_engine.py`
- Opus 4.7 rules live: self-verification line every task, `/ultrareview` before merging >20 LOC, task-budgets on long agents, 3x-vision for screenshots
- User rules (1–12) in [.claude/rules/user-rules.md](../.claude/rules/user-rules.md) — plan first, ask when unsure, honor CLAUDE.md, no half migrations, factor god classes, don't change tests, additive wins only in-scope files, new files over bloat
