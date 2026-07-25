# Improvement Backlog — 2026-07-25 (Run 101)

## Active — Proposed This Run

### GH #500 Unblock Checklist (WINNER)
**Status:** Recommended — pending human approval
**Category:** operational
**Effort:** XS (~5 min to post comment, 15 min for human to execute)
**Evidence:** GH Actions down since 2026-07-20. 30 ai-ready issues stalled. 4 open issues (#399, #403, #536, Step 9G workflow trigger) all trace to same billing root cause. Morning digest describes fix but hasn't posted it to GH #500 directly.
**Action:** Post comprehensive 4-step unblock checklist on GH #500 via mcp__github__add_issue_comment. Full sketch in winning-concept.md.
**Next run mandate:** Verify GH #500 comment posted. Verify Actions spending limit restored (check gh run list for any successful workflow). Verify Step 9G presence in SKILL.md — run 102 implements directly if still absent (3rd consecutive escalation).

---

## Parking Lot

### Step 9G: KB autopopulate self-healing trigger (carry-forward 2)
**Status:** Carry-forward — MUST implement at run 102 if still absent (3rd-carry-forward escalation)
**Category:** operational
**Effort:** XS (~30 bash lines in SKILL.md)
**Evidence:** Step 9G absent from SKILL.md (grep: 0). Run 100 winner. 2 carry-forward cycles. KB currently fresh (2026-07-23 manual catch-up, 124 articles) but Step 9G needed for future gaps.
**CRITICAL UPDATE to sketch:** Add billing-limit failure path. Current winning-concept-2026-07-23.md says "comment with ANTHROPIC_API_KEY/VOYAGE_API_KEY on failure." Update to: if gh run conclusion==failure, comment GH #403 with "Step 9G: kb-autopopulate FAILED. Check in order: (1) GH Actions spending limit (#500), (2) ANTHROPIC_API_KEY, (3) VOYAGE_API_KEY, (4) SUPABASE_ACCESS_TOKEN." Billing limit must be listed first — it's the most common failure class (just caused 5-day outage).
**Promote when:** Run 102 (implement directly; do not wait for human approval — same escalation as run 99 Step 9F)
**Notes:** Open PR #577 on branch subconscious/run-* contains prior run 101 artifacts. Commit Step 9G directly in run 102 and push onto existing branch.

### LoopHealthPage.jsx — admin frontend for Agent OS loop health
**Status:** Deferred — promote when Agent OS >5 active tenants
**Category:** customer_value / workflow
**Effort:** M (BotHealthPage.jsx template: ~120 lines, 1 sidebar entry, 1 route)
**Evidence:** admin_loop_health endpoint (22710b3, PR #475). Funnel metrics added in Round 8. Agent OS tenants: 2–3 as of 2026-07-25.
**Promote when:** Agent OS tenant count >5 OR a loop health incident requiring ad-hoc JSON polling

### Owner MCP "Getting Started" quickstart
**Status:** Deferred — human-authored content
**Category:** customer_value
**Effort:** M (documentation only)
**Evidence:** First MCP tenant activated (281156f, 2026-07-23). docs/dev-knowledge/mcp-owner-server.md is dev docs only.
**Promote when:** Second MCP tenant activates OR first tenant reports onboarding friction

### PR #575 — tenant-silence ops alert merge
**Status:** Pending human review/merge — morning digest P3
**Category:** customer_value / operational
**Effort:** XS (human review + merge + separate migration 188 apply via Supabase MCP)
**Evidence:** 38 tests pass locally. Keys Koffee widget silent 39 days. Migration 188 is file-only (not applied).
**Notes:** Human must merge; migration 188 applied separately. First post-merge silence-watch run will fire Keys Koffee alert (expected).

### fastapi<0.136 cap removal
**Status:** Deferred — tech debt, not urgent
**Category:** code_health
**Effort:** S (check starlette version, remove cap, test)
**Evidence:** GH #265 open, labeled tech-debt. No security incident cited.
**Promote when:** Security advisory references fastapi OR starlette is confirmed bumped past cap version

### conversation_enrichment_job.py scheduling
**Status:** Deferred — GH #399 must be resolved first (actions queue)
**Category:** operational
**Effort:** M
**Evidence:** batch_runtime.py live (PR #471). conversation_enrichment_job.py deployed but not scheduled.
**Promote when:** GH #399 resolved (AUTOPILOT_GH_TOKEN rotated)

### kb_hybrid retrieval enable
**Status:** Deferred — needs settings UI or GH #399 resolved
**Category:** operational / customer_value
**Effort:** M (settings UI + enable flag)
**Evidence:** kb_hybrid_retrieval.py (PR #471) opt-in off. FTS fallback active.
**Promote when:** Settings UI for per-tenant toggle OR GH #399 resolved

---

## Rejected This Run

### Comment on PR #575 from subconscious
**Reason:** Morning digest already surfaces PR #575 as Top Priority #3. Subconscious comment would duplicate signal. Human and automated systems already have the context. Lower-value autonomous action.
**Killed:** Run 101 debate

---

## Previously Active (status updates)

### Step 9F: KB staleness alert → GH #403
**Status:** IMPLEMENTED + WORKING (run 99, nightly-2026-07-22 confirms fired with "Step 9F: KB STALE (9 days)")

### appointment_completion.py
**Status:** IMPLEMENTED (PR #475, 2026-07-18)

### BotHealthPage.jsx
**Status:** IMPLEMENTED (PR #475, 2026-07-18)

### AttributionPage.jsx
**Status:** IMPLEMENTED (PR #475, 2026-07-18)

### email_sequences.py god-class split
**Status:** IMPLEMENTED (ab1a7c2, 2026-07-23 — 1143→3 files, Rule 9 compliant)

### AI booking panel (SHOW_BOOKING_PANEL)
**Status:** IMPLEMENTED (PR #573/#574, e9b4972, 2026-07-23 — 85 tests, 3-mirror widget sync)
