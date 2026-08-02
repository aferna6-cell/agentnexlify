# Subconscious Run 101 — 5 Candidate Ideas
**Date:** 2026-08-02-pm
**Evidence gathered:** nightly-commit-review-2026-08-02.md, governance.json (run_101_mandate), memory.jsonl (runs 95–100), bug-patterns.md, knowledge-base/log.md, sms_agent.py, prospecting.py, EscalationsPage.jsx, gmail_connector.py

---

## Idea 1 — Step 9G: KB Self-Healing Trigger in Nightly SKILL.md (CARRY-FORWARD from run 100)

**Category:** workflow_efficiency
**Effort:** XS (1 SKILL.md edit, ~10 lines)
**Impact:** HIGH
**Confidence:** 0.95

**Evidence:**
- `grep -c "9G\|kb_autopopulate\|kb-autopopulate" .claude/skills/nightly-commit-review/SKILL.md` returns 0 — Step 9G is ABSENT
- `knowledge-base/log.md`: last run 2026-07-23, currently 10 days stale (>7d alert threshold)
- Step 9F (run 99) fires staleness alert but cannot self-repair — it only comments a GH issue
- `scripts/daily/kb-autopopulate.sh` and `.github/workflows/kb-autopopulate.yml` both exist (mechanism proven)
- run_101_mandate item #1: "Step 9G present in SKILL.md? (0 occurrences per grep)"
- run_101_mandate item #2: "KB freshness since 2026-07-13?" — currently stale 10 days

**The fix:** Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md` — after the Step 9F staleness check, if the KB is stale AND the GH workflow for kb-autopopulate is not currently running, trigger `gh workflow run kb-autopopulate.yml`. This closes the gap between "alert fires" and "repair happens autonomously."

**Why it wins:** Run 100 recommended this. The KB is currently stale. The mechanism exists. The only missing piece is the nightly routine wiring it up. Zero new infrastructure required.

---

## Idea 2 — Connector Token Expiry Health Check (Step 9H candidate)

**Category:** operational
**Effort:** S (nightly script + Step 9H block in SKILL.md, ~30 lines)
**Impact:** MEDIUM
**Confidence:** 0.80

**Evidence:**
- `backend/services/gmail_connector.py` (518L, new from b67710c) — OAuth tokens with 10-min state expiry for OAuth flow, but long-term `access_token`/`refresh_token` in `gmail_integrations` table not monitored for expiry
- `backend/services/connector_registry.py` (314L) — centralized connector status; has `last_checked` and `status` fields but no staleness scan in nightly
- `docs/dev-knowledge/bug-patterns.md`: "Silent-green automation" pattern — Keys Koffee widget dark 5+ weeks unnoticed. Connector tokens silently expiring = same failure class
- governance.json run_101_mandate item #6: "MCP tenant count (Step 9H revisit condition >5)" — separate concern but suggests Step 9H is in the pipeline

**The fix:** Add Step 9H to nightly SKILL.md: query `connector_registry` + `gmail_integrations` for rows where `last_refreshed` > 30d and `status = active`. If found, post GH issue with tenant list. Fires before tenants notice dead connectors.

**Why it doesn't win over Idea 1:** Idea 1 is already a proven mechanism at zero infra cost. Idea 2 requires schema knowledge of `gmail_integrations` columns (not fully verified), whereas Idea 1 is a pure SKILL.md edit with known command (`gh workflow run`).

---

## Idea 3 — Inbox Triage AI Cost Guard

**Category:** operational / code_health
**Effort:** S (guard in inbox_triage.py + possibly nightly per-tenant alert, ~40 lines)
**Impact:** MEDIUM
**Confidence:** 0.78

**Evidence:**
- `backend/services/inbox_triage.py` (455L, new from b67710c) — calls Claude to triage every incoming email for all tenant inboxes
- `backend/services/sms_agent.py`: has `sms_rate_limiter.check_sms_rate_limit(tenant_id, plan)` at line 385 — rate limiting already implemented for SMS
- `backend/services/ai_usage_guard.py` (`PLAN_BASELINE_TOKENS`) — per-plan token budget framework exists
- No equivalent rate-limit guard visible in inbox_triage.py (grep confirms 0 occurrences of `rate_limit` or `ai_usage_guard` in inbox_triage.py)
- High-volume inbox tenant (e.g., 500 emails/day) at ~500 tokens/triage call = 250k tokens/day per tenant — could blow per-tenant budget

**The fix:** Add `ai_usage_guard` check to `inbox_triage.py` inbox processing loop, matching the pattern in `sms_agent.py`. Cap daily triage calls per tenant. Degrade gracefully (skip LLM, apply keyword-only rule) when budget exceeded.

**Why it doesn't win over Idea 1:** Idea 1 is XS effort + already mandated from run 100. Idea 3 requires reading inbox_triage.py in full + careful integration with ai_usage_guard. Idea 1 is more atomic and more urgent (KB currently stale).

---

## Idea 4 — Social Publisher Post-Delivery Receipt / Failure Alert

**Category:** operational
**Effort:** S (~20 lines in social_publisher.py + nightly check)
**Impact:** MEDIUM-LOW
**Confidence:** 0.72

**Evidence:**
- `backend/services/social_publisher.py` — new from b67710c, posts to Facebook/Instagram
- `bug-patterns.md`: "Silent-green automation" — Keys Koffee widget dark 5+ weeks unnoticed; same pattern risk here
- No `delivery_status`, `delivered_at`, or failure alerting column visible in the social_posts table (from migration scan during nightly review)
- PWA push infrastructure live (c5a5a62) — could fire push notification to owner when post fails

**The fix:** After `social_publisher.py` posts, record delivery status in `social_posts.delivery_status`. If API returns error, write `failed` + trigger `send_owner_push` notification. Add Step to nightly: scan for `social_posts` rows with `delivery_status = failed` in last 24h, post GH issue if found.

**Why it doesn't win over Idea 1:** Delivery receipt requires migration (new column) — higher effort and blast radius than a SKILL.md edit. Idea 1 is XS, already mandated, and closes the current KB staleness gap. Idea 4 is valid but can follow after Idea 1 lands.

---

## Idea 5 — PWA Install Prompt in Dashboard

**Category:** customer_value
**Effort:** M (frontend component + UX logic)
**Impact:** LOW-MEDIUM
**Confidence:** 0.65

**Evidence:**
- PWA infrastructure live (c5a5a62): push_subscriptions table, send_owner_push, manifest icons (192/512px)
- `frontend/src/pages/EscalationsPage.jsx` exists (dashboard page is the natural install-prompt surface)
- PWA install event (`beforeinstallprompt`) must be intercepted in browser — requires React hook + banner component
- Customer gap: getting escalation push notifications requires PWA installed — without prompt, users miss the workflow

**The fix:** Add `usePWAInstall` hook + install banner in dashboard. Show once per user per device. On install, subscribe to push notifications automatically.

**Why it doesn't win:** This is M effort with UX/frontend work, not XS automation. The subconscious recommends atomic operational wins, not feature builds. Customer_value ideas require user approval + compound-engineering pipeline. Idea 1 is XS + mandated + already deferred from run 100. Idea 5 is a good candidate for a future feature sprint.

---

## Ranking Summary

| Rank | Idea | Category | Effort | Impact | Block? |
|------|------|----------|--------|--------|--------|
| 1 | Step 9G: KB self-healing trigger | workflow | XS | HIGH | None |
| 2 | Connector token expiry check (9H) | operational | S | MEDIUM | Schema verify |
| 3 | Inbox triage AI cost guard | operational | S | MEDIUM | Deep read |
| 4 | Social publisher delivery receipt | operational | S | MED-LOW | Migration needed |
| 5 | PWA install prompt | customer_value | M | LOW-MED | Feature scope |

**Top 3 for debate:** Ideas 1, 2, 3.
