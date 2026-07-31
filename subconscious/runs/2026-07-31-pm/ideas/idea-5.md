# Idea 5: Close Stale Subconscious PRs — Dedup Guard Enforcement

**Evidence:** 4 open subconscious draft PRs exist as of 2026-07-31: #577 (8 days, "Step 9G + 9H combined"), #606 (3 days, "feature-docs-trio SKILL.md"), #611 (1 day, "Step 9H GH Actions CI alerter + security fix"), #613 (0 days, this run's branch). SKILL.md dedup guard: "one PR per direction." PR #577 proposed Step 9G (now implemented directly in run 101) and Step 9H (killed in governance). PR #611 proposed "Step 9H GH Actions CI systematic failure alerter" — Step 9H was killed in run 100 governance and remains in rejected_paths. These stale PRs create reviewer confusion, contradict implemented/rejected governance decisions, and violate the one-PR-per-direction principle.

**Action:** Via `mcp__github__update_pull_request`: (1) Close PR #577 with comment: "Superseded — Step 9G implemented directly in run 101 (2026-07-31). Step 9H direction rejected in governance (run 100). See subconscious/runs/2026-07-31/winning-concept.md." (2) Close PR #611 with comment: "Rejected direction — Step 9H was killed in run 100 governance (MCP monitoring premature: 1 tenant). Will revisit when MCP tenant count >5." Keep PR #606 (different direction, not superseded). Keep PR #613 (this run's active branch).

**Impact:** Clean PR queue. Reviewers see 2 active subconscious PRs (#606, #613) instead of 4, reducing confusion. Governance and PR state are consistent. Takes ~5 minutes via GH MCP.

**Category:** workflow
