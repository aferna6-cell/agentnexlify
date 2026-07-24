# Run 101 — Candidate Ideas (2026-07-24)

## Evidence Summary
- **Step 9G ABSENT** from nightly-commit-review SKILL.md (mandate item 1 FAILS — carry-forward 2)
- **KB freshness**: PASS — e9b4972 ran compile 2026-07-24, 124 articles (was 114)
- **New critical bug pattern**: Keys Koffee widget silent for 39 days (2026-07-23 in bug-patterns.md)
- **AI booking panel shipped** (e9b4972 CLEAN, MEDIUM) — booking CTA now native, not plain-text link
- **email_sequences.py split done** (ab1a7c2 CLEAN) — god-class factored to 3 routers
- **GH #399 still open** — AUTOPILOT_GH_TOKEN expired, blocking 30 ai-ready issues
- **GH #403 still open** — kb-autopopulate GH Actions dead (ANTHROPIC_API_KEY missing)

---

## Idea 1: Step 9G — KB Autopopulate Self-Healing Trigger (CARRY-FORWARD 2)

**Category:** Workflow Efficiency
**Evidence:** Run 100 winner concept exists at `subconscious/runs/2026-07-23/winning-concept.md`. Step 9G grep returns 0 in SKILL.md (confirmed absent). Mandate item 1 FAILS. This is cycle 2; escalation policy: implement directly at cycle 3 (run 102) if not implemented here.
**Action:** Add ~30-line bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9F block (line 305). Block: check DAYS_STALE > 7; if true, run `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`; sleep 30; parse conclusion from `gh run list`; comment on GH #403 on failure. Exit 0 on success or in-progress.
**Impact:** HIGH — KB autopopulate has been dead due to GH Actions secret failure; self-healing catches the class of secret-rotation failures silently masked by `continue-on-error: true`. Prevents 63-day stale gaps (previously experienced).
**Effort:** XS — proven autonomous channel (SKILL.md bash block); same shape as Steps 9B/9C/9D/9E/9F, each implemented in 1 cycle.
**Channel:** Autonomous (SKILL.md edit — no human approval needed for this category per governance.json).

---

## Idea 2: Step 9H — Per-Tenant Zero-Conversation Heartbeat Alert

**Category:** Customer Value / Operational
**Evidence:** Keys Koffee widget embed dropped ~2026-06-14, discovered 2026-07-23 — 39 days silent failure. Paying tenant with zero widget conversations for 39 days. Pattern now in bug-patterns.md: "Silent-green automation: paying tenant's widget missing for 5+ weeks, nobody noticed." Prevention requires per-tenant conversation-count check with alert on zero for paying tenants.
**Action:** Add Step 9H to nightly-commit-review SKILL.md. Query Supabase for paying tenants with zero conversations in last 7 days. Alert on GH issue with tenant list.
**Impact:** HIGH — prevents revenue-risking silent failures across all paying tenants. Keys Koffee class of failure would be caught in <7 days instead of 39.
**Effort:** MEDIUM — Supabase MCP required for conversation count query. Supabase MCP unavailable in headless bash sessions (confirmed limitation). Blocks direct implementation; must be a GH issue recommendation only.
**Channel:** GH issue (can't implement autonomously due to Supabase MCP headless limitation).

---

## Idea 3: First Booking Conversion Verification Post AI-Panel Fix

**Category:** Customer Value
**Evidence:** e9b4972 (2026-07-24, MEDIUM/CLEAN) shipped native booking panel triggered by AI. This is the first deployment of the SHOW_BOOKING_PANEL marker → `show_booking=True` flow. No confirmation yet that a real booking was completed through the new panel by a live tenant.
**Action:** Add nightly check: query `appointments` table for bookings created in last 7 days with `source='widget'`. Log count to nightly report. Alert if zero for >7 days post-deployment.
**Impact:** MEDIUM — catches zero-conversion bugs early. But: Supabase MCP unavailable in headless sessions — same blocker as Idea 2.
**Effort:** MEDIUM — same Supabase MCP blocker. GH issue only.
**Channel:** GH issue.

---

## Idea 4: GH #399 Token Rotation Escalation

**Category:** Operational
**Evidence:** GH #399 open: AUTOPILOT_GH_TOKEN expired, blocking 30 ai-ready issues and kb-autopopulate GH Actions. Step 9E (credential-rotation check) should be alerting on this. Issue has been open for multiple cycles. Automations remain blocked.
**Action:** Verify Step 9E fires correctly for AUTOPILOT_GH_TOKEN. If not — patch the credential name list in SKILL.md to include it. Add comment to GH #399 with current days-expired count.
**Impact:** MEDIUM — unblocks 30 queued issues once token is rotated. But: rotation requires human action (can't rotate GH tokens autonomously). This is an escalation alert, not a fix.
**Effort:** XS — verification + comment. Step 9E already handles the comment flow.
**Channel:** Human action required for token rotation. Alert only via Step 9E.

---

## Idea 5: GH Actions KB Credentials Diagnostic Issue

**Category:** Workflow Efficiency / Operational
**Evidence:** GH #403 open: kb-autopopulate.yml fails silently because ANTHROPIC_API_KEY missing from GH Actions Secrets. This is the exact failure class Step 9G's failure-path comment would diagnose. Step 9G includes: "comment on GH #403 with: Check ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GH Actions Secrets."
**Action:** Step 9G already absorbs this diagnostic. No separate idea needed — this is a sub-component of Idea 1.
**Impact:** Absorbed by Idea 1.
**Effort:** Zero — part of Idea 1.
**Channel:** Autonomous (via Idea 1 implementation).
