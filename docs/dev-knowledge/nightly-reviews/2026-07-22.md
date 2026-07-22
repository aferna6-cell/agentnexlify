# Nightly Review — 2026-07-22

**Run started:** 2026-07-22 UTC (scheduled)  
**Working tree:** clean (rebased to main @ 9166b64)

---

## Commits reviewed (18 commits, last 24h, no-merges)

| SHA | Summary | Risk |
|-----|---------|------|
| 9166b64 | feat: web research sources + upgrade funnel fixes + voice-workforce bridge + routing metrics + fast-path digest + architecture audit (#557) | MEDIUM |
| b8066ad | docs(ops): backlog unblock runbook [skip ci] | LOW |
| 6dc3419 | feat(zapier): Zapier CLI app — new_lead polling trigger + API-key auth (#61) [skip ci] | MEDIUM |
| d50d1e8 | docs(zapier): KB article + 3 CRM guides + runbook + marketing copy (#62) [skip ci] | LOW |
| af2d9d3 | feat: one-click email approvals + stage-2 plan gate + suite chips + step timeline approvals + legacy token baselines + fast-path metrics (#553) | MEDIUM |
| 14ebe8e | docs(drive-kb): KB article + ADR + failures runbook (#54) [skip ci] | LOW |
| 70e3c82 | feat(ops-automation): pending_automations retry drainer + table (#118) [skip ci] | MEDIUM |
| 9d3cfa2 | feat(drive-kb): disconnect confirm + read-only KB when Drive sync active (#52) [skip ci] | MEDIUM |
| d6897df | feat(drive-kb): optional "Connect Google Drive" onboarding step (#53) [skip ci] | MEDIUM |
| 79e8398 | feat(zapier): Settings → Integrations → Zapier page (#60) [skip ci] | MEDIUM |
| c8abe98 | feat(photo-quote): pilot telemetry — feedback + error-rate + conversion (#44) [skip ci] | MEDIUM |
| 5202f82 | feat(photo-quote): widget upload UI + quote render + 3-fork handoff (#41) [skip ci] | MEDIUM |
| 55352b3 | feat: research card + 402 upsell + chat-originated projects + research-to-project + marketing gate fix (#545) | MEDIUM |
| aa040fc | fix: planner response schema needs additionalProperties false (#544) | LOW |
| b41d460 | feat: suite plan gate + chat BI fast path + research v1 + approval rollup + runner-planned projects (#543) | MEDIUM |
| a20e8fe | feat: workforce weekly digest + ask-data v2 + starter recurring tasks (#542) | MEDIUM |
| 0deab50 | fix: re-export purge_photo_quote_images_30d so the automation loop can start (#541) | LOW |
| 39b7f72 | feat: OS Projects + memory write-back + MCP context tools + workforce dashboard + loop supervisor (#540) | MEDIUM |

**Total LOC changed: >>50 (guardrail tripped — no autonomous fixes executed)**

---

## Findings

### Fixed autonomously (0)

Guardrail tripped: total LOC changed across 18 commits exceeds 50-LOC-per-run limit. No autonomous fixes executed.

### Issues opened (0 new)

Existing issues already track all identified problems. Comments added instead (see below).

### Checks performed

**Widget byte-identical:** PASS — `widget/`, `frontend/public/widget/`, `landing-page-v2/widget/` are identical (commit 5202f82).

**`from __future__ import annotations`:** No new violations in FastAPI files. `backend/tests/test_local_seo_handlers.py:8` has the import but was NOT modified in last 24h (pre-existing, test file only — no Pydantic request body impact).

**`client_id` vs `tenant_id` on leads/conversations:** PASS. New code uses `tenant_select(db, "leads", tenant_id, ...)` and `tenant_select(db, "conversations", tenant_id, ...)` which correctly maps to `client_id` column via `_TENANT_COLUMN_OVERRIDES` in `tenant_scope.py:17-18`. The variable `tenant_id` is the JWT claim value; `tenant_scope_column()` returns `"client_id"` for both tables.

**Migration 186 (pending_automations) RLS:** Enables RLS without explicit policies — matches established pattern in 9 other migrations (084, 145, 150, 151, 175, 177, 179, 180, 183). `retry_worker.py` uses service client which bypasses RLS. No bug.

**Migration 185 (photo_quote_feedback):** Correctly uses `client_id` in index on `quote_requests` table. PASS.

**os_web_sources.py SSRF:** PASS. Every URL passes `is_safe_url()` (DNS resolution, blocks private IPs, link-local 169.254.0.0/16, loopback). Redirect re-validated. 1-hop cap. Response capped at 1.5MB / 4000 chars.

**auth_billing.py changes (af2d9d3):** Minimal changes — no diff content flagged. Skipped (FORBIDDEN path per skill rules).

**Skipped (FORBIDDEN paths):** 0 commits exclusively in forbidden paths. `auth_billing.py` touched in af2d9d3 but change was minimal (9 lines shown in stat) and pre-exists known-safe pattern.

---

## Supplementary health checks

### 9A — Moratorium Status
`moratorium_active: false` — no escalation needed. 13 items in `pending_approval` state logged for reference; moratorium is inactive so no GH issue required.

### 9B — Healthz Monitor Maintenance
`ops/monitoring/healthz-alert.sh` EXISTS — no action needed.

### 9C — Brain Connector Health
Last 5 entries in `brain/INGESTION-LOG.md` show github connector OK, supabase consistently "skipped — SUPABASE_ACCESS_TOKEN not set". This is a configuration gap (never set), not consecutive errors. Consecutive failures < 3. No escalation triggered.

### 9D — Issue-to-PR Loop Health Check
- **Open ai-ready issues:** 3 (#114, #69, #70)
- **#114:** Has linked PR #517 (open draft) — NOT stalled.
- **#69, #70:** Memory-hygiene issues, both old (>24h) but pre-exist the loop failure.
- **Loop status:** STALLED — autopilot-issue-loop.yml latest run `2026-07-22T04:27:29Z`, `failure` in 4 seconds. Streak: ~18 days since 2026-07-04.
- **Existing issue:** #399 open ("autopilot-issue-loop GitHub Actions failing 5+ days — AUTOPILOT_GH_TOKEN expired"). Comment added with updated failure count.
- **Step 9D log:** 3 ai-ready issues, #114 has PR, loop last ran 2026-07-22T04:27:29Z, status: STALLED (existing issue #399)

### 9E — Credential Rotation Tracking
File `ops/credential-rotation-schedule.md` found. 3 credentials checked:
- `AUTOPILOT_GH_TOKEN`: last rotated 2026-07-04, 18 days ago — < 76 days, not approaching expiry.
- `Brain connector GitHub PAT`: last rotated 2026-07-04, 18 days ago — < 76 days, not approaching expiry.
- `SUPABASE_ACCESS_TOKEN`: last_rotated = "unknown — not yet set" — logged as unknown_state.

No credential-rotation GH issues found. Step 9E: 2 credentials checked (known rotation), 0 approaching expiry (>=76 days), 1 unknown state (SUPABASE_ACCESS_TOKEN never set).

### 9F — KB Autopopulate Staleness
Last run: `2026-07-13 20:00` (9 days ago). Threshold = 7 days. KB is STALE.
Comment added to GH #403 (existing issue: "Set ANTHROPIC_API_KEY in GitHub Actions secrets").
Step 9F: KB STALE (9 days) — comment added to GH #403.

---

## Next action

**STALLED — autopilot-issue-loop failing 18 days.** Human must rotate `AUTOPILOT_GH_TOKEN` in GitHub Actions secrets (see #399). No code changes this run. All code quality checks passed.
