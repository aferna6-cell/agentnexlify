# Improvement Backlog — Run 98 (2026-07-17-pm)

## Active Direction

### Step 9F: KB Autopopulate Staleness Check (run 97 winner → run 98 carry-forward)
**Status:** pending_autonomous (2nd cycle, still ABSENT)
**Effort:** XS
**Confidence:** HIGH
**Autonomous-executable:** YES — nightly-commit-review SKILL.md-edit channel
**Action:** Add Step 9F bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9E. Full block in `subconscious/runs/2026-07-17/winning-concept.md` and `subconscious/runs/2026-07-17-pm/winning-concept.md`.

---

## Parking Lot

### appointment_completion.py (GH #454, runs 95+96 winner — mechanism blocked)
**Status:** Queued as ai-ready GH issue. Nightly channel CANNOT create new service files.
**Unblock:** GH #399 (AUTOPILOT_GH_TOKEN) resolved → issue-to-pr-loop picks up GH #454.
**Do NOT re-debate until GH #399 resolved.**

### conversation_enrichment_job.py scheduling (NEW — run 98 debate, WEAKENED)
**Status:** Good idea, wrong timing. GH #399 blocks execution queue — any ai-ready GH issue competes with 30+ stalled items.
**Unblock:** GH #399 resolved. Then file GH issue: schedule `0 3 * * *` UTC, `ANTHROPIC_API_KEY` needed, pattern from `kb-autopopulate.yml`.
**Re-evaluate:** Run 99+ after GH #399 cleared.

### kb_hybrid_retrieval enable (NEW — run 98 debate, WEAKENED)
**Status:** Parked. Two blockers: (1) Supabase MCP unavailable in headless sessions, (2) no settings UI for widget_kb_hybrid_enabled flag.
**Unblock:** Settings UI for new widget_configs feature flags, OR GH #399 resolved so issue-to-pr-loop can build the settings toggle.
**Re-evaluate:** After settings UI exists or GH #399 resolved.

### BotHealthPage.jsx frontend (GH issue filed, Bonus B run 96)
**Status:** GH issue filed. No ai-ready label until GH #399 resolved. L-effort.
**Unblock:** GH #399 resolved.

### notify_common.py failure-mode tests (mandate item 7 — RESOLVED)
**Status:** CLOSED. safe_send_email swallows all failures by contract (design, not oversight). dispatch_owner_alert never propagates exceptions by contract. 12 new tests in test_notify_common.py verify this contract. No additional tests needed.

### GH #399 (AUTOPILOT_GH_TOKEN) — Day 16+
**Status:** OPEN. Single Railway Variables action unblocks 30 ai-ready issues. Subconscious cannot act — human-only.
**Impact if resolved:** conversation_enrichment_job.py scheduling, kb_hybrid settings UI, appointment_completion.py, BotHealthPage.jsx, Lead Source Analytics, 25+ other queued items all become executable.

### GH #413 (REFERRAL_REWARD_ENABLED=1) — Day 27+
**Status:** NOT SET. 5 autonomous comments posted across runs 90-95. 10/10 checklist items complete (PR #429 2026-07-14). 2-minute Railway Variables flip. Human-only.

### GH #415 (Keys Koffee business hours) — Day 24+
**Status:** 0 human responses. Keys Koffee has 0 business_hours rows — blocks all bookings for that tenant. Sole operational blocker for first booking.
