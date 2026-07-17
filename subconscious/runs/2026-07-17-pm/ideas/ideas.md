# Ideas — Run 98 (2026-07-17-pm)

## Evidence Digest (200 words max)

50 commits in 3 days. PR #471 (180b19e) lands major AI infrastructure: `batch_runtime.py` (Batch API, 50% cost reduction for offline jobs), `kb_reranker.py` (Haiku-based KB reranker, opt-in off), `kb_hybrid_retrieval.py` (FTS+semantic hybrid, opt-in off), prompt caching, structured outputs, updated `conversation_enrichment_job.py`. Two loop_health_scan bugs fixed same day: `26f7829` (blind pagination) + `6391bd3` (issues:write permissions). KB last run 2026-07-13 (4 days ago — within 7-day threshold, currently healthy). GH #399 (AUTOPILOT_GH_TOKEN) OPEN Day 16+, 30 ai-ready issues stalled. GH #413 (REFERRAL_REWARD_ENABLED=1) NOT SET Day 27+. notify_common.py 12 tests cover IdempotencyGuard + dispatch branching by contract (safe_send_email swallows failures by design — mandate item 7 effectively resolved). **Critical mandate check: Step 9F ABSENT from nightly SKILL.md** — mandate check 1 from run 97 fails. conversation_enrichment_job.py is the first wired caller of batch_runtime but has no cron schedule — dead code until scheduled.

---

## Idea 1: Step 9F Carry-Forward — KB Staleness Check in nightly SKILL.md

**Evidence:** Mandate check 1 from run 97 fires: `grep -c "Step 9F" .claude/skills/nightly-commit-review/SKILL.md` returns 0 — ABSENT. KB last run 2026-07-13 (4 days, currently healthy by 7-day threshold). Steps 9B/9C/9D/9E all implemented in 1 nightly cycle each via same SKILL.md-edit channel. Next KB staleness gap is prevented only by this guard.

**Action:** Add Step 9F bash block (verbatim from subconscious/runs/2026-07-17/winning-concept.md) to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9E. Block reads `knowledge-base/log.md` last entry date, calculates days_stale, logs result, comments on GH #403 if >7 days.

**Impact:** Daily KB health signal in every nightly log. Alerts within 7 days of next staleness gap instead of 72+ days. Zero false positives (guard wraps all failure paths).

**Category:** workflow

---

## Idea 2: File GH Issue to Schedule conversation_enrichment_job.py

**Evidence:** PR #471 (180b19e, 2026-07-17) lands `conversation_enrichment_job.py` updated to call `batch_runtime.py` (50% cheaper than real-time). batch_runtime.py docstring: "Good candidates: nightly compiles, batch re-scoring, periodic classification jobs already running on a scheduler tick." No `.github/workflows/conversation-enrichment*.yml` exists. Without scheduling, `run_pending_enrichment_batch()` is never called. KB enrichment improves AI response quality over time.

**Action:** File GH issue with ai-ready label: "feat(batch): schedule conversation_enrichment_job via GitHub Actions — first wired caller of batch_runtime.py runs 0 times without a cron." Include: schedule `0 3 * * *` UTC (daily off-peak), secrets needed (`ANTHROPIC_API_KEY`), script pattern from `kb-autopopulate.yml`.

**Impact:** Activates 50% cost reduction on conversation enrichment. Queues for issue-to-pr-loop once GH #399 resolved. Zero autonomous execution risk (GH issue only).

**Category:** operational

---

## Idea 3: Enable kb_hybrid_retrieval for Keys Koffee Pilot Tenant

**Evidence:** PR #471 ships `kb_hybrid_retrieval.py` (FTS+semantic merge) gated behind `widget_kb_hybrid_enabled` setting (default off). KB log 2026-07-13 shows `coffee-shop-cafe-faqs` compiled and validated with "do you have oat milk" — exact keyword query that FTS would catch but semantic might miss. Keys Koffee is the most active AI-interaction tenant right now. `widget_configs.widget_kb_hybrid_enabled` SQL UPDATE is the only action needed.

**Action:** File human-action GH issue: "feat(tenants/kb): enable widget_kb_hybrid_enabled for keys-koffee pilot — SQL: UPDATE widget_configs SET widget_kb_hybrid_enabled=true WHERE slug='keys-koffee'." Labels: tenant-config, human-action-required.

**Impact:** Improves KB grounding for Keys Koffee AI widget. FTS catches keyword misses semantic search drops. Validates hybrid retrieval before broader rollout. Zero code change.

**Category:** customer_value

---

## Idea 4: Verify notify_common.py dispatch_owner_alert failure-mode coverage (Mandate Item 7 Resolution)

**Evidence:** Run 97 mandate item 7: "notify_common.py: read 12 new tests — do they cover dispatch_owner_alert failure modes?" Test file contract: "safe_send_email / safe_send_sms swallow every provider failure" and "dispatch_owner_alert fires the email branch only with an owner_email and the SMS branch only when enabled AND a phone is set." The `safe_send_email` swallows all failures by design — `dispatch_owner_alert` never propagates exceptions by contract. Need to confirm test coverage matches the contract statement.

**Action:** Read `backend/tests/test_notify_common.py` fully. Confirm tests exist for: (a) `dispatch_owner_alert` returns normally when `safe_send_email` raises internally; (b) `dispatch_owner_alert` with `owner_email=None` skips email branch silently. Close mandate item 7 in run 98 governance.

**Impact:** Mandate closure. Confirms notify_common.py is production-safe for all 5 services that call it (conversation_notify, os_approval_notify, os_failure_notify, os_opportunity_notify, os_push_notify).

**Category:** code_health

---

## Idea 5: Add Admin Frontend for /api/admin/loop-health (BotHealthPage.jsx)

**Evidence:** PR #463 (22710b3) ships `admin_loop_health.py` — `/api/admin/loop-health` endpoint with 5 vitals (drafts pending >16d, suggestion rot, KB staleness, loop health, tenant counts). 261 tests green. No frontend wired — admins have no visibility without curl. GH issue filed (Bonus B, run 96). Pattern: AdminFunnelPage.jsx already ships similar admin diagnostics. L-effort but now backend is complete.

**Action:** Build `frontend/src/pages/admin/BotHealthPage.jsx` — 5 vitals cards, last-updated timestamp, auto-refresh 60s. Wire to `/api/admin/loop-health`. Add route in `App.jsx` + sidebar entry.

**Impact:** Admin visibility into automation loop health without curl. Surfaces stale drafts, suggestion rot, KB freshness daily. L-effort (4-6 hours).

**Category:** workflow
