# Improvement Backlog — 2026-07-29 (Run 103)

## Active (pending implementation)

### Step 9G CORRECTED — CCR Routine Health Check
**Status:** DIRECTLY IMPLEMENTED this run (subconscious/run-2026-07-28 branch, same commit)
**Where:** `.claude/skills/nightly-commit-review/SKILL.md` after Step 9F
**Summary:** When KB staleness >7 days, check `git log --since="48 hours ago" -- knowledge-base/`. If no recent KB commits → post CCR stall alert to GH #403. Replaces original Step 9G (gh workflow run, obsolete).
**Bundle:** Step 9F diagnostic text corrected in same commit (points to CCR Routine, not GH Actions).

### feature-docs-trio SKILL.md
**Status:** PENDING — 2nd carry-forward
**Where:** `.claude/skills/feature-docs-trio/SKILL.md` (new file) + `.claude/skills/feature-build/SKILL.md` (+3 lines)
**Evidence:** 3 occurrences in 7 days (717c7f3, 14ebe8e, d50d1e8). 30-45 min saved per feature.
**Carry-forward rule:** Run 104 = 3rd carry-forward → DIRECT IMPLEMENTATION by subconscious.
**Full content:** embedded in `winning-concept.md` (this run) and `subconscious/runs/2026-07-28/winning-concept.md`.

---

## Parking lot

### Silent-green tenant heartbeat (Step 9H)
**Status:** PARKED — prerequisite unmet
**Prerequisite:** verify SUPABASE_URL + SUPABASE_SERVICE_KEY in nightly CCR bash environment
**Summary:** Nightly query of conversations table — alert if any paid tenant has 0 conversations/7d. Keys Koffee-class churn prevention. Use `client_id`, NOT `tenant_id`.
**Promote when:** owner confirms env vars are available in nightly bash.

### LoopHealthPage.jsx promotion
**Status:** PARKED — tenant count condition not met (current: 2-3 tenants)
**Promote when:** Agent OS active tenants > 5.

### widget-ai-marker-add SKILL.md
**Status:** PARKED — LOW urgency
**Evidence:** 2 occurrences (HANDOFF_REQUESTED historical, SHOW_BOOKING_PANEL 2026-07-23). ~1/month frequency.
**Promote when:** Next AI marker addition request arrives.

### round-iteration-loop SKILL.md
**Status:** PARKED — LOW urgency
**Evidence:** 3 occurrences in 7 days (rounds 6, 7, 8 of Agent OS). Pattern active during Agent OS sprints.
**Promote when:** Next Agent OS round begins.

---

## Retired / Obsolete

### Step 9G ORIGINAL (gh workflow run kb-autopopulate.yml)
**Retired run 101** — CCR Routine deployed 2026-07-23 handles KB autopopulate. GH Actions broken (#500). Original design would trigger failing workflow and post incorrect diagnostic.

### MCP Step 9H monitoring
**Killed run 100** — 1 tenant only, can't auth-test without tenant mcp_ key. Revisit when MCP tenant count > 5.

---

## Governance notes

- GH #500 (Actions billing): still down. Any idea requiring `gh workflow run` is blocked until resolved.
- GH #399 (AUTOPILOT_GH_TOKEN): still open. Issue-to-pr-loop stalled on ~30 ai-ready issues.
- PR #577 (original Steps 9G + 9H): do NOT merge as-is. Step 9G obsolete. See comment 5110254199.
- PR #606 (this branch): consolidates runs 101-103 on `subconscious/run-2026-07-28`.
