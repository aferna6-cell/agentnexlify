# Subconscious Run 101 — Ideas (2026-07-22-pm)

**Context:** Run 100 (AM) claimed H1 plan gate gap (PR #559). This PM session picks independently from remaining evidence.

---

## Evidence anchors

- Today's nightly: 18 commits, ALL MEDIUM/LOW risk, 0 autonomous fixes — "Total LOC changed >>50 (guardrail tripped)"
- `nightly-commit-review/SKILL.md` line 110: "Max 50 LOC changed per run — larger = bail"
- Interpreted as: total LOC across all reviewed commits → bailed on everything
- Intended as (best reading): the autonomous fix itself must be <50 LOC
- GH #413 CLOSED today — 4 referral `active_directions` still show `pending_human_action`
- PR #537 (mcp_client.py wiring + Step 9F bash) conflicts with PR #559 — sequencing problem
- `scripts/daily/nightly-commit-review.sh`: remote routine path disabled, manual path calls SKILL.md directly → Step 9F fires correctly
- Two competing run-100 PRs (#537, #559) — dedup guard collision from different sessions

---

## 5 Candidate Ideas

### Idea 1 — Fix nightly LOC guardrail: per-fix vs total-batch ambiguity
**Category:** workflow_efficiency  
**Effort:** XS (2-line SKILL.md clarification)  
**Evidence:** Today's nightly fired 0 autonomous fixes on 18 MEDIUM/LOW commits because "total LOC >>50." SKILL.md line 110 says "Max 50 LOC changed per run" — ambiguous between (a) total batch LOC and (b) per-fix LOC. Nightly chose interpretation (a), which is wrong. The correct guardrail is (b): the individual fix must be <50 LOC. With (a), any active sprint day silences all autonomous patching. With (b), the nightly can safely fix a 3-line logging bug on a 2000-LOC sprint day.  
**Fix:** Clarify SKILL.md line 110 to "Max 50 LOC **in the autonomous fix itself** per run — larger fix = bail on that fix, continue reviewing others." Update line 308 to match.  
**Impact:** ~5-10 autonomous fixes per week during active development sprints.  
**Autonomous-executable:** YES — SKILL.md edit only, no code, no schema.

---

### Idea 2 — Governance correction: GH #413 referral direction update
**Category:** code_health (governance accuracy)  
**Effort:** XS (governance.json update)  
**Evidence:** GH #413 CLOSED today (morning digest p.38: "Closed today — verify if env-var was actually set in Railway"). Four `active_directions` entries for the referral reward still show `status: "pending_human_action"` with no record of the issue closure. Governance drift misleads future runs into treating this as still-open human action.  
**Fix:** Update the run-93 referral direction to note: "GH #413 closed 2026-07-22 — Railway activation (REFERRAL_REWARD_ENABLED=1) unverified per morning digest. Status: closed_unverified."  
**Impact:** LOW (governance hygiene only) — but prevents future runs repeating the same escalation on a closed issue.  
**Autonomous-executable:** YES.

---

### Idea 3 — Wire mcp_client.py into os_thread_runner.py / agent_os_bridge.py
**Category:** workflow_efficiency  
**Effort:** M (30-50 LOC addition)  
**Evidence:** mcp_client.py shipped in enterprise sprint (memory.jsonl run 98). PR #537 run-100 winner proposed this exact wiring. Agent OS threads currently can't call MCP tools.  
**Problem:** PR #537 already has this implementation and is waiting for #559 to merge first before it can be rebased. Implementing again in a new run creates a third parallel attempt.  
**Verdict:** Sequencing recommendation, not a new code task. Better captured as a governance note.  
**Autonomous-executable:** Partially — code exists in PR #537.

---

### Idea 4 — Subconscious PR dedup guard: branch sentinel file
**Category:** code_health (subconscious infrastructure)  
**Effort:** S (SKILL.md update + state file write)  
**Evidence:** Today produced two competing run-100 PRs (#537 from yesterday, #559 from AM session) on different branches with different winners. Root cause: fresh sessions check GitHub for "subconscious" PRs but then create a new branch if the existing PR's branch name doesn't match the new run's naming scheme. A sentinel file `subconscious/state/current-branch.txt` would give sessions an unambiguous canonical branch name without needing to parse PR metadata.  
**Fix:** Update SKILL.md dedup guard to (1) check `subconscious/state/current-branch.txt` first, (2) write it on every PR creation.  
**Impact:** MEDIUM — prevents future session collisions; low frequency issue (only happens when 2 sessions run same day).  
**Autonomous-executable:** YES.

---

### Idea 5 — Add Step 9F bash block to scripts/daily/nightly-commit-review.sh
**Category:** workflow_efficiency  
**Effort:** XS (20-line bash addition)  
**Evidence:** PR #537 run-101 winner proposed this. The bash script (manual-catch-up tool) lacks Step 9F. However: the remote Claude Routine invokes SKILL.md directly — Step 9F IS in SKILL.md and fired correctly today (KB stale 9 days, comment added to #403). The bash script is disabled by default (`CLAUDE_NIGHTLY_REVIEW_LOCAL=0`). Manual-path gap = LOW priority.  
**Impact:** LOW — automated path works; bash is manual-only.  
**Autonomous-executable:** YES — but low ROI given remote path works.
