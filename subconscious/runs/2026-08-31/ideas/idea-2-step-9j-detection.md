# Idea 2: Fix Step 9J Detection — search_pull_requests Instead of list_pull_requests

**Evidence:** nightly-2026-08-30 Step 9J: "No Dependabot PRs detected" (0 found). nightly-2026-08-31 Step 9J: "not scoped in this run." Two consecutive zero-detection failures after the rebase-trigger fix in run 112. Root cause (confirmed in run 113 mandate): `list_pull_requests(creator="dependabot[bot]")` is unreliable for bot-authored PRs in headless sessions. GitHub MCP search_pull_requests with `"is:pr is:open author:app/dependabot"` is the documented reliable alternative.

**Action:** Edit Step 9J.1 in .claude/skills/nightly-commit-review/SKILL.md: replace `mcp__github__list_pull_requests(creator="dependabot[bot]")` with `mcp__github__search_pull_requests(query="is:pr is:open author:app/dependabot")`. Same SKILL.md commit as Step 9K (bonus action).

**Impact:** Step 9J resumes detecting Dependabot PRs. 20+ aging CVE-window PRs become eligible for @dependabot rebase trigger. Security patch latency drops from weeks to 24-48h.

**Category:** workflow_efficiency
