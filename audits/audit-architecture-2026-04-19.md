# Architecture Audit — 2026-04-19

## Scope
- 30 commits since 2026-04-12 (widget-helpers split 8b089c4, Phase 2/3 canonical skill pattern 080098b + 0f1d23a, obsidian-sync docs 5f11559, test restoration c0aef59, etc.)
- Top churn files (last 7d):
  - `research-skill-graph/projects/is-white-label-reseller-distribution-gohighlevel-*` (5)
  - `knowledge-base/log.md` (2)
  - `knowledge-base/PENDING.md` (2)
  - `research-skill-graph/research-queue.md` (1)
  - `research-skill-graph/knowledge/{data-points,concepts}.md` (1 each)
  - `knowledge-base/wiki/competitors/{intercom,birdeye}-*.md` (1 each)
  - `knowledge-base/wiki/ai-llm/{effective-context-engineering,agent-skills-anthropic}.md` (1 each)
- Engineering churn this window is overwhelmingly knowledge-base + skill-meta, not product code. Code surface stable.
- Trigger: weekly cadence per `.claude/rules/daily-skills.md` Rule 5.
- Input: `python3 .claude/skills/improve-architecture/scripts/audit.py` — ran cleanly, 64 raw issues.

## Pass 1 — File bloat (god classes)

Script flagged 24 files >600 lines. Ranked by severity below; recent splits excluded.

### Recent wins (do not re-flag)
- `widget_helpers.py`: 1673 → **96 lines** post-split (commit 8b089c4). `widget_chat_helpers.py` (824) and `widget_lead_helpers.py` (833) are the split targets — both under the 1000-line follow-up threshold, expected to stay until their own concerns outgrow their modules.

### CRITICAL bloat (>1000 lines, router layer — highest blast radius)
- `backend/routers/local_seo.py` — **1552 lines**
- `backend/routers/auth.py` — **1487 lines** (security-critical, split carries risk)
- `backend/tests/test_managed_agents.py` — **1333 lines** (test file; pain is review time not prod risk)
- `backend/routers/invoices.py` — **1211 lines**
- `backend/routers/calls.py` — **1175 lines**
- `backend/routers/leads.py` — **1158 lines** (touches client_id invariant — split must preserve)
- `backend/routers/widget_chat.py` — **1119 lines** (tenant-widget hot path)
- `backend/routers/onboarding.py` — **1084 lines**
- `backend/routers/email_sequences.py` — **1065 lines**
- `backend/routers/booking_page.py` — **1065 lines**
- `widget/agentnexlify-widget.js` — **2043 lines** (byte-identical with `frontend/public/widget/agentnexlify-widget.js` — any split needs to ship to both simultaneously; widget split is HIGHEST friction)

### HIGH bloat (600–1000 lines)
- `backend/models/schemas.py` (998), `backend/main.py` (907), `backend/routers/billing.py` (875), `backend/services/automation/rule_engine.py` (875), `backend/routers/bids.py` (858), `backend/routers/forms.py` (860), `backend/routers/client_portal.py` (830), `backend/services/automation/scheduled_jobs_ext.py` (792), `backend/routers/marketing_campaigns.py` (721), `backend/routers/admin_analytics.py` (690), `backend/routers/sequences.py` (679), `backend/routers/appointments.py` (648), `backend/routers/analytics/dashboard.py` (628), `backend/services/booking.py` (622), `backend/routers/pipeline.py` (619), `backend/routers/social_media.py` (618), `backend/services/branding_service.py` (609), `backend/routers/channels_facebook.py` (607), `backend/routers/analytics/control_center.py` (606).

Pattern: the router layer is where the bloat lives. Services + analytics already show the split pattern (`analytics/_common.py`, `analytics/dashboard.py`, etc.). Routers have not caught up.

## Pass 2 — Layer violations

- **False positive** (script over-matches): `backend/routers/conversation_inbox.py:217,244` — comment text says "session_id from frontend" which the regex interprets as a frontend import. Verified inline; no `from frontend` statement exists. Script could be tightened to skip comment-only lines, but not a code fix.
- **Real violation**: `backend/services/branding_service.py:161` imports `_filter_branding_for_plan, _sanitize_*` from `backend.routers.widget_helpers`. Service pulling from router = reverse dep. Widget-helpers was just split; this import likely went stale against the 96-line stub. Must either move the helpers into `services/` or resolve to the new split module.

## Pass 3 — Dead code signals

28 dead-import hits. Worst-offender cluster is `backend/routers/analytics/_common.py` with **9 unused imports** on a shared-helper module — indicates `_common.py` was seeded with imports "for later" that never got used. Also worth fixing:
- `backend/routers/widget_chat.py:131` unused `agent_sdk_client` — this is the Managed Agents SDK; signals that the Agent SDK wiring may have been reverted or forgotten mid-refactor. Confirm intent before deleting.
- `backend/routers/auth.py:335` unused `INDUSTRY_FAQS` — dead branch after a feature flag flip, candidate for removal.
- `backend/routers/widget_helpers.py:23` unused `get_service_supabase` — leftover from the 1673→96 split; the helper now delegates and no longer hits the DB directly.

Rest are one-liners across 10+ files — mechanical cleanup, safe to batch.

## Pass 4 — Schema drift

- Latest migration file: `migrations/107_refund_request_id.sql`.
- `docs/dev-knowledge/schema-log.md` last entry covers migration **105** (applied 2026-04-15).
- **Gap: migrations 106 + 107 are committed to `migrations/` but not logged in schema-log.md.** Unclear whether they were applied to the live DB or just staged. Must confirm via Supabase MCP `list_migrations` and then backfill schema-log.md either way. This is exactly the "no half migrations" Rule 8 failure mode.

## Pass 5 — Dependency rot

Quick read of `backend/requirements.txt`:
- All core pins recent: `fastapi>=0.115.6`, `anthropic>=0.95.0`, `supabase==2.28.3`, `pydantic>=2.11.7`, `httpx==0.28.1`, `uvicorn==0.34.0`.
- No obvious 2024-era pins. Full CVE/upgrade scan is out of scope for this weekly — defer to `.claude/skills/dependency-auditor/SKILL.md` in a dedicated session.

## Pass 6 — Performance hotspots

`grep -n "time.sleep\|requests.get\|requests.post" backend/**/*.py`:
- 5 `time.sleep` hits, all in retry/backoff paths:
  - `backend/services/managed_agents.py:145,187,503,526` — exponential-backoff on Managed Agents SDK retries
  - `backend/services/llm_runtime.py:255` — same pattern for Claude API retries
- Zero `requests.get` / `requests.post` in request paths.
- All clean. Sleeps are out-of-band retry loops, not in-request blocking.

## Ranked fix list

| Rank | Severity | Effort | Location | Issue |
|------|----------|--------|----------|-------|
| 1 | CRITICAL | S | `migrations/106_launch_risk_guardrails.sql`, `migrations/107_refund_request_id.sql` vs `docs/dev-knowledge/schema-log.md` | Migrations 106 + 107 not documented. Verify applied state + backfill log (Rule 8 no half-migrations) |
| 2 | CRITICAL | M | `backend/services/branding_service.py:161` | Service imports `_filter_branding_for_plan`, `_sanitize_*` from `backend.routers.widget_helpers`. Reverse dep + likely broken after widget_helpers split to 96-line stub |
| 3 | HIGH | M | `backend/routers/auth.py` (1487 lines) | God class + security-critical surface. Split by concern: session, password, OAuth, 2FA |
| 4 | HIGH | M | `backend/routers/local_seo.py` (1552 lines) | Largest router. Split by feature: GBP sync, citations, on-page audit, reports |
| 5 | HIGH | S | `backend/routers/widget_chat.py:131` | Unused `agent_sdk_client` import — confirm whether Agent SDK wiring was reverted or forgotten |
| 6 | HIGH | L | `widget/agentnexlify-widget.js` (2043 lines) | God class, but byte-identical rule means split must happen in both widget mirrors simultaneously. High friction. Keep parked until a feature requires editing it |
| 7 | MEDIUM | S | `backend/routers/analytics/_common.py:6-17` | 9 unused imports in a shared helper — suggests the module was pre-populated then never used. Delete all |
| 8 | MEDIUM | M | `backend/routers/leads.py` (1158 lines), `backend/routers/widget_chat.py` (1119 lines) | Next-tier router splits. Both touch `client_id` invariant — must preserve during split |
| 9 | MEDIUM | S | `backend/models/schemas.py` (998 lines) | Split by domain (auth, leads, conversations, billing) — pure Pydantic, low risk |
| 10 | MEDIUM | S | 26 dead-import hits across 15 files | Batch cleanup pass — safe additive work |
| 11 | LOW | S | `.claude/skills/improve-architecture/scripts/audit.py` | Layer-violation regex flags comment text (false positive at `conversation_inbox.py:217,244`). Tighten to skip `#` comments |

Severity: CRITICAL (prod risk or invariant break), HIGH (imminent maintenance pain), MEDIUM (quality debt), LOW (nice-to-have).
Effort: S (<1hr), M (1–4hr), L (>4hr, needs compound-engineering pipeline).

## Recommended next session

Top 3 picks for the next compound-engineering session:

1. **Rank 1 — Migration 106/107 schema-log backfill** (S, ~30min)
   - Rationale: Rule 8 violation in flight. If 106/107 are applied but undocumented, any future schema-guard pass misses them; if unapplied, production code may be calling columns that don't exist in live DB.
   - Blast radius: 2 files (`schema-log.md` + possibly `mcp__supabase__apply_migration`). Zero test risk.
   - Additive win (Rule 11): yes — backfilling docs is reversible and in-scope for any session touching migrations.

2. **Rank 2 — branding_service → widget_helpers reverse dep** (M, ~2hr)
   - Rationale: Service importing from router post-split is almost certainly broken or fragile. The 96-line widget_helpers.py stub may no longer export `_filter_branding_for_plan` / `_sanitize_*`. Silent import error risk.
   - Blast radius: `backend/services/branding_service.py`, `backend/routers/widget_helpers.py`, `widget_chat_helpers.py`, `widget_lead_helpers.py`. Tests covering branding flow at risk.
   - Proper migration (Rule 8): yes — move shared helpers into `backend/services/branding_helpers.py` or similar, update both the service and router importers in one PR.

3. **Rank 7 + Rank 10 combined — dead-import batch cleanup** (S, ~45min)
   - Rationale: 28 dead imports identified by audit.py, 9 clustered in `analytics/_common.py`. Cheap compounding win — clean file = clean review next time.
   - Blast radius: 15 files, all import-only edits. Zero runtime risk. Tests should be untouched.
   - Additive win (Rule 11): yes — purely reversible, one commit per cluster if desired.

Ranks 3, 4, 6 (auth/local_seo/widget.js god classes) are deliberately parked. They are real debt but each is a Large-effort compound-engineering pipeline of its own — not a weekly-cadence fix. Surface them to user for a dedicated multi-session plan.

## Out of scope for this audit

- Fixing anything here (separate sessions per daily-skills Rule 5)
- Widget byte-identical check (covered by pre-push hook; manual `wc -l` confirmed 2043=2043)
- Full CVE scan (defer to `dependency-auditor`)
- Running tests (green on last push per pre-push hook)

Verified: `wc -l audits/audit-architecture-2026-04-19.md` — PASS (under 300-line bound, actionable top-3).
