# Improvement Backlog — Run 101 (2026-07-22-pm)

Ranked by impact × effort. Ideas that lost the debate included for future reference.

---

## Rank 1 (WINNER) — Fix nightly LOC guardrail: per-fix vs total-batch

**Impact:** HIGH | **Effort:** XS | **Autonomous:** YES  
SKILL.md line 110 ambiguity causes total-batch LOC to silence all autonomous fixes during sprint days. Clarify to per-fix cap. Restores ~5-10 fixes/week.  
→ See `winning-concept.md` for full spec.

---

## Rank 2 — Wire mcp_client.py into os_thread_runner.py / agent_os_bridge.py

**Impact:** HIGH | **Effort:** M | **Autonomous:** YES (code exists in PR #537)  
mcp_client.py shipped in enterprise sprint but not called from Agent OS execution path. Agent OS threads can't use MCP tools until wired in. **Blocked by PR sequencing:** merge PR #559 (H1 plan gate) first, then rebase PR #537, then merge. Do not create a 3rd implementation.  
**Recommended action:** After PR #559 merges, rebase PR #537 onto main and merge.

---

## Rank 3 — Governance correction: GH #413 referral direction update

**Impact:** LOW | **Effort:** XS | **Autonomous:** YES  
GH #413 closed 2026-07-22. Four referral `active_directions` entries still show `pending_human_action`. Update run-93 direction to note closure and pending Railway verification.  
**Note:** Applied directly to governance.json in this run (see governance update in run commit).

---

## Rank 4 — Subconscious PR dedup guard: branch sentinel file

**Impact:** MEDIUM | **Effort:** S | **Autonomous:** YES  
Two competing run-100 PRs (#537, #559) from different sessions. A sentinel file `subconscious/state/current-branch.txt` would give sessions an unambiguous branch name without PR title parsing. Low-frequency problem (only triggers when 2 sessions run same day). Deferred.

---

## Rank 5 — Add Step 9F bash block to nightly bash script

**Impact:** LOW | **Effort:** XS | **Autonomous:** YES  
`scripts/daily/nightly-commit-review.sh` lacks Step 9F but the automated path (remote Claude Routine → SKILL.md) works correctly. Bash script is manual-only and disabled by default. Step 9F confirmed firing today. Lowest-priority item in this batch.

---

## PR sequencing note (from debate)

Current state:
- PR #559 (run 100 AM, H1 plan gate) — open, ready for human review
- PR #537 (run 100 yesterday, mcp_client + Step 9F bash) — open, conflicts with #559

Correct sequence:
1. Human reviews + merges PR #559 (H1 revenue fix)
2. PR #537 rebased onto main post-merge
3. PR #537 merged (mcp_client.py wiring + Step 9F bash addition)
4. Subconscious run 102+ can pick novel improvements
