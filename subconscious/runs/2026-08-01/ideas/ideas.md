# Candidate Ideas — Run 103 (2026-08-01)

## Evidence Summary
- **Step 9G**: Implemented (on `subconscious/run-2026-07-31` branch, not yet merged). First fire: pending merge.
- **Step 9I**: Recommended by run 102, NOT yet in SKILL.md. First carry-forward cycle.
- **KB staleness**: ~19 days (GH Actions spending limit blocks kb-autopopulate.yml — Day 12+ of GH #500).
- **VOYAGE_API_KEY**: Missing from GH Actions secrets (known Step 9G failure path). No issue filed.
- **GH #399** (CRITICAL, 23d): AUTOPILOT_GH_TOKEN expired — 30+ ai-ready issues stalled.
- **GH #536** (HIGH, 11d): INTEGRATIONS_ENC_KEY missing in Railway — migration 176 blocked.
- **GH #500** (12d+): GH Actions spending limit — blocks CI, kb-autopopulate, autopilot loop.
- **Nightly log**: CLEAN, only ops commits. No code shipped since 8e78f5b (2026-07-28).
- **PR dedup violation**: 4 subconscious DRAFT PRs existed before dedup guard landed in run 99. Pattern still manifests.

---

## Idea 1: Step 9I — Daily GH #500 Spending Limit Escalation (carry-forward from run 102)
**Category:** operational / nightly-automation
**Effort:** XS (~20 bash lines in SKILL.md)
**Evidence:** GH #500 has received ZERO automated escalation comments across 12 days. Step 9G will fail silently on GH Actions spending limit — its diagnostic comment goes to GH #403, not GH #500. Run 102 winning concept is fully specified with implementation sketch. Same SKILL.md autonomous channel proven across Steps 9B–9G.
**Impact:** Daily nightly comments on GH #500 with cumulative day count + pipeline-wide impact framing (CI blocked + Step 9G blocked + 3 paying tenants on degraded KB). Resolving GH #500 unblocks CI, Step 9G, autopilot loop, and Dependabot batch all at once.
**Status:** First carry-forward. Implementation sketch exists in `subconscious/runs/2026-07-31-pm/winning-concept.md`.

---

## Idea 2: VOYAGE_API_KEY GH Issue — Document Known Step 9G Failure Path
**Category:** operational / issue-tracking
**Effort:** XS (one GH issue via mcp__github__)
**Evidence:** KB compile logs show "Embeddings SKIPPED (no credentials; FTS fallback covers retrieval)" — VOYAGE_API_KEY missing from GH Actions secrets is the root cause. Step 9G's failure diagnostic names ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN as the likely suspects. No GH issue exists for VOYAGE_API_KEY specifically.
**Impact:** Creates an actionable issue for the human to provision VOYAGE_API_KEY in GH Actions Secrets. When combined with GH #500 resolution, unblocks full Step 9G success. Autonomous action — can file this run.
**Status:** Bonus action, no prior recommendation needed.

---

## Idea 3: Tenant Silence Detection via REST API (GH #610)
**Category:** customer_value / revenue
**Effort:** M-L (new Python logic + nightly SKILL.md step)
**Evidence:** GH #610 filed 2026-07-29 (3 days ago). Keys Koffee silent 5+ weeks undetected cost trust. Supabase MCP unavailable in headless (confirmed runs 87/88/90/100). Workaround: hit Supabase REST API directly with anon key (publicly available from frontend config — already in widget code).
**Risk:** Supabase anon key in bash script = visible in nightly log. RLS should protect row-level data but anon key exposure still requires care. Not enough cycles to design this safely.
**Status:** Parking lot. Too early (3 days since issue filed). Architecture unclear. Defer to run 105+.

---

## Idea 4: PR Dedup Guard Hardening — Pre-Run Script
**Category:** workflow / meta
**Effort:** S (new `scripts/subconscious_dedup_guard.sh` + SKILL.md Phase 8 reinforcement)
**Evidence:** 4 separate DRAFT subconscious PRs created (#577, #606, #611, #613) despite dedup guard in SKILL.md since run 99. Cron sessions read SKILL.md but the guard is in Phase 8 (end of run) — by the time cron reaches Phase 8, it may be confused about branch state and create a new one anyway. Root cause: guard checks GitHub state but commits first, then checks, causing race.
**Impact:** Prevents future duplicate PRs. Meta-fix. Medium value.
**Status:** Parking lot. Not the highest value per cycle. Run 104+ after Step 9I ships.

---

## Idea 5: Nightly ai-ready Issue Count Visibility
**Category:** operational / visibility
**Effort:** S (~15 bash lines in SKILL.md, or nightly log section)
**Evidence:** GH #399 blocks 30+ ai-ready issues. The exact count has never been automatically tracked — "30+" is a stale estimate from run 99. Adding a step to `gh issue list --label ai-ready --state open` and log the count would give nightly visibility without human review.
**Impact:** Tracks queued work behind #399 passively. Low urgency — helpful but not critical.
**Status:** Parking lot. Clean addition but outweighed by Step 9I priority.
