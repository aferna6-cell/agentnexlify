# Ideas — Run 128 (2026-09-24)

## Evidence Summary

nightly-2026-09-24 IMPLEMENTED Step 9E P0 tier (run 127 winner, 7th carry resolved). P0 comment posted on GH #399 (8 days to AUTOPILOT_GH_TOKEN expiry 2026-10-02). GH #893 closed "not_planned" by owner — token NOT rotated per GH #399 still open (19 comments, 0 human action). Step 9G gh→MCP fix confirmed in SKILL.md from nightly-2026-09-23. KB: 29 days stale (last: 2026-08-26) — ANTHROPIC_API_KEY (#403) and VOYAGE_API_KEY (#618) block compile. os_tool_executions.py: 783 lines, GH #881 filed (ai-ready). Step 9J: 17/19 Dependabot PRs skipped every run (token budget depleted before Step 9J processes all). 45 AI metering violations in GH #827. Repo: 2 ops commits in last 3 days, 0 production code changes.

---

## Idea 1: Step 9J Priority Queue — Process Oldest 5 Dependabot PRs First

**Evidence:** 7+ consecutive nightly runs show 17/19 Dependabot PRs skipped. Step 9J lists all 19 PRs from search_pull_requests and iterates sequentially until token budget runs out (~2 PRs processed). Oldest PRs (#885-#891, some 7d+) carry highest CVE risk but are not guaranteed to be processed first.

**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9J.1: change search query to add `sort:created-asc` and cap `perPage=5`. This retrieves only the 5 oldest Dependabot PRs per run, ensuring the highest-CVE-age PRs are always processed within the token budget. Add log entry: "Step 9J: {N} oldest PRs checked (sort:created-asc), {M} merged, {R} rebase-triggered, {K} skipped."

**Impact:** Security patches on oldest CVE-risk PRs within 24h of CI passing vs multi-week delay. Fixes the core failure mode of Step 9J without reordering nightly steps.

**Category:** workflow_efficiency

---

## Idea 2: os_tool_executions.py Split Spec — GH Issue Body Enhancement

**Evidence:** GH #881 filed (ai-ready label) but body may lack sufficient split spec for issue-to-pr-loop to execute when GH #399 resolves. 783 lines. 7 consecutive subconscious mentions. Stable 8+ days (0 commits).

**Action:** Read GH #881 body; if split spec incomplete (missing module names, public API contracts, migration path), post an enhancing comment with the spec. Unblocks issue-to-pr-loop auto-implementation when AUTOPILOT_GH_TOKEN rotates.

**Impact:** Ensures the split executes correctly when the loop resumes. Prevents a second round of subconscious attention for spec clarification.

**Category:** code_health

---

## Idea 3: Credential Rotation Liveness Test (Step 9O)

**Evidence:** AUTOPILOT_GH_TOKEN expires 2026-10-02 (8 days). Current Step 9E detects expiry by days-since-rotation but cannot detect early revocation (e.g., permission change, manual revoke). GH #399 title now shows token as "P0" — the concern is real. The brain connector also failed on the same date as the last expiry event (runs 79+), suggesting coordinated credential events.

**Action:** Add Step 9O to nightly SKILL.md: make a test API call using the token (e.g., list_commits with limit=1) and check for 401/403. Log: "Step 9O: AUTOPILOT_GH_TOKEN liveness — VALID" or "REVOKED — investigate immediately." XS effort SKILL.md addition.

**Impact:** Catches unexpected early revocation before automation goes dark. Complements Step 9E's schedule-based detection.

**Category:** operational

---

## Idea 4: Step 9M — AI Metering Violation Trend Tracking

**Evidence:** 45 AI metering violations in GH #827 (Step 9L). Issue-to-pr-loop stalled (GH #399). No visibility into whether violations are growing or shrinking week-over-week. If violations grow 10%/week, the metering gap compounds silently.

**Action:** Add a weekly Step 9M block to nightly SKILL.md: read GH #827 last 4 comments for violation counts, compute delta, log trend. If trend is positive (growing violations), post a "growing gap" comment on GH #827.

**Impact:** Provides trend signal for prioritization. If violations shrink post-loop restart, confirms Step 9L is working. If they grow, elevates priority.

**Category:** code_health

---

## Idea 5: GH #403 / #616 / #618 Consolidation Issue

**Evidence:** 3 separate open GH issues block KB autopopulate: GH #403 (ANTHROPIC_API_KEY, critical + human-action-required), GH #616 (ANTHROPIC_API_KEY — same issue, different title), GH #618 (VOYAGE_API_KEY). Having 3 separate issues for the same root cause (KB blocked) fragments human attention and may cause dedup confusion.

**Action:** Post a consolidation comment on GH #403 (the oldest, highest-priority one) that references #616 and #618 as related, and provides an exact checklist: (1) set ANTHROPIC_API_KEY, (2) set VOYAGE_API_KEY, (3) close #616 and #618 after step 1. This reduces 3 issues to 1 focused action item.

**Impact:** Reduces cognitive load for human. More likely to prompt action than 3 separate issues. One GitHub comment from the current session.

**Category:** operational
