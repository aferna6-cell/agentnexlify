# Ideas — Run 2026-08-17-pm

## Evidence Digest

**What changed (last 3 days):**
- run 105 implemented git push fix + route-security-guard-audit SKILL.md (autonomous-executable, both done)
- nightly-2026-08-16: SUPABASE_ACCESS_TOKEN section added, GH #661 filed (scoring_config.py block_demo_role)
- No product code commits in 3+ days
- Skill discovery 2026-08-17: `dependabot-merge-runner`, `stale-autonomy-pr-closer`, `orphaned-commit-recovery` proposed

**Critical signals:**
- GH #661 (security) + GH #643: same class bug (missing block_demo_role) filed twice in 6 days. Pattern = new routers added without security dependency.
- GH #660 (ai-ready): scoring_config.py fix — demo tenants can write/delete scoring factors TODAY.
- 10 open PRs: 4 Dependabot ready (7-14 days), 6 draft subconscious accumulating (20d oldest).
- KB staleness: 25 days. GH #403 (ANTHROPIC_API_KEY missing in GH Actions) — blocking Step 9G.
- GH #399: AUTOPILOT_GH_TOKEN expired, Day 37+. Blocks issue-to-pr-loop.
- route-security-guard-audit SKILL.md: EXISTS (created run 105). run_106_mandate says: if verified, propose Step 9I.
- Morning digest #1 priority: merge GH #660 (scoring_config.py security fix).

**Mandate checks (run 106):**
1. git push origin HEAD in SKILL.md Phase 8: PASS (2 occurrences confirmed)
2. route-security-guard-audit SKILL.md in origin: PASS (file exists)
3. KB staleness: FAIL — 25 days, GH #403 unresolved
4. GH #661 PR status: NO PR yet (ai-ready issue exists; loop stalled)
5. SUPABASE_ACCESS_TOKEN last_rotated: NOT filled in by human
6. Step 9I mandate: TRIGGERED — route-security-guard-audit verified, propose Step 9I

---

### Idea 1: Step 9I — Add nightly demo-role security sweep to nightly-commit-review SKILL.md
**Evidence:** GH #643 (appointment_briefs.py missing block_demo_role, 2026-08-11) + GH #661 (scoring_config.py missing block_demo_role, 2026-08-16) — same class bug filed twice in 6 days. run_106_mandate explicitly: "propose Step 9I if route-security-guard-audit SKILL.md verified." route-security-guard-audit SKILL.md verified PASS. Morning digest #1 priority is this class of bug.
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` to add Step 9I block: grep `backend/routers/` for mutating endpoints (POST/PUT/DELETE) missing `block_demo_role` Depends; if found, check whether GH issue already open; if not, file one with `security` + `ai-ready` labels.
**Impact:** Closes the router-security discovery gap from "whenever someone notices" (6-day gap for GH #661) to "next nightly run." Prevents entire class of recurring bug. Same autonomous-executable channel as Steps 9C/9F/9G — high implementation confidence.
**Category:** code_health

### Idea 2: Post targeted GH #403 comment with exact ANTHROPIC_API_KEY setup instructions
**Evidence:** KB 25 days stale. Step 9G triggers kb-autopopulate.yml but ANTHROPIC_API_KEY missing in GH Actions secrets blocks actual compile. Morning digest calls this a "one-minute fix" — yet #403 has been open 37+ days. No comment with exact GitHub UI steps exists on the issue.
**Action:** Post comment on GH #403 via mcp__github__add_issue_comment with verbatim steps: GitHub repo → Settings → Secrets and variables → Actions → New repository secret → Name: ANTHROPIC_API_KEY → Value: [from Railway]. Unblocks KB autopopulate immediately.
**Impact:** Unblocks 25-day KB staleness. All KB-dependent systems (AI chat, semantic search, typed notes) get fresh data. One-off but high-value.
**Category:** operational

### Idea 3: Create dependabot-merge-runner SKILL.md
**Evidence:** Skill discovery 2026-08-17 proposed this with 3+ consecutive morning digest citations. Same 4 Dependabot PRs (#629, #630, #631, #649) flagged every day for 7-14 days — zero merge action. Security dep bumps left unmerged = growing exposure window.
**Action:** Create `.claude/skills/dependabot-merge-runner/SKILL.md` per skill discovery proposal: list Dependabot PRs, check CI status, merge if green + no requested changes, comment with `blocked-ci` label otherwise.
**Impact:** 15+ min saved per batch, recurring. Security dep bumps merged faster. PR debt reduced.
**Category:** workflow_efficiency

### Idea 4: Post fix sketch on GH #660 to pre-load issue-to-pr-loop
**Evidence:** GH #660 is ai-ready security fix for scoring_config.py block_demo_role (4 mutating endpoints). Morning digest #1 priority. Demo tenants writing/deleting scoring factors NOW. Issue-to-pr-loop stalled (GH #399) but when AUTOPILOT_GH_TOKEN rotated, loop needs a good fix sketch to execute immediately.
**Action:** Post comment on GH #660 with exact fix: add `Depends(block_demo_role)` to all 4 mutating endpoints in `backend/routers/scoring_config.py`. Include test case in `test_plan_gating_new_plans.py`.
**Impact:** When GH #399 resolved (loop unblocked), GH #660 executes immediately — saves 1-2 day delay for issue-to-pr-loop to research and implement.
**Category:** code_health

### Idea 5: Create stale-autonomy-pr-closer SKILL.md
**Evidence:** Skill discovery 2026-08-17 proposed this. 6 draft subconscious PRs accumulating (#606 20d, #611 18d, #613 17d, #626 15d, #648 7d, #653 5d). Morning digest flags stale PRs every day. PR #606 almost certainly superseded by newer work.
**Action:** Create `.claude/skills/stale-autonomy-pr-closer/SKILL.md` per skill discovery proposal: list draft PRs by autonomy authors, check age + file overlap, close superseded ones with comment.
**Impact:** Reduces reviewer cognitive load. PR list stays actionable. Prevents stale work confusing future agents.
**Category:** workflow_efficiency
