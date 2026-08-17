# Ideas — Run 105 (2026-08-17)

### Idea 1: Add `git push` to subconscious SKILL.md Phase 8
**Evidence:** nightly-commit-review-2026-08-16.md filed MEDIUM structural finding: 6 commits (ddd8e77 through fad41c2) present on local HEAD but not in origin/main. System prompt confirms container is ephemeral — reclaimed after inactivity. Subconscious SKILL.md Phase 8 currently reads only `git commit`, no push. Every run since at least 2026-08-06 has been orphaned in the cloud container.
**Action:** Append `git push origin HEAD:main` after the git commit line in `.claude/skills/subconscious/SKILL.md` Phase 8. Also check for an existing open subconscious PR (per PR dedup guard) and push to it if found.
**Impact:** Guarantees every subconscious run survives container reclamation. Eliminates the structural finding that nightly has been raising. Compounds: all future run artifacts, governance state, and SKILL.md changes become durable.
**Category:** workflow

---

### Idea 2: Write route-security-guard-audit SKILL.md (3rd carry-forward → autonomous-executable)
**Evidence:** Proposed run 102, carry-forwarded runs 103 and 104. GH #643 (appointment_briefs.py missing block_demo_role) filed 2026-08-11. GH #661 (scoring_config.py missing block_demo_role) filed nightly-2026-08-16. Pattern is recurring — new feature routers being added without the security dependency. Run 105 mandate explicitly requires escalation to autonomous-executable on 3rd carry-forward (per governance.json run_105_mandate item 2).
**Action:** Create `.claude/skills/route-security-guard-audit/SKILL.md` with 6-step checklist: (1) inventory existing guards, (2) find mutating routes missing block_demo_role, (3) find AI-invoking routes missing ai_usage_guard, (4) assess business impact, (5) add block_demo_role as Depends() pattern, (6) add structural test in test_plan_gating_new_plans.py.
**Impact:** Converts ad-hoc security findings (GH #643, #661) into a repeatable, invocable skill. Prevents future feature routers from missing the guard. Closes the 3rd-cycle escalation.
**Category:** code_health

---

### Idea 3: Post targeted ANTHROPIC_API_KEY fix comment on GH #403
**Evidence:** KB autopopulate last ran 2026-07-23 (25 days stale). Step 9G in nightly SKILL.md triggers `gh workflow run kb-autopopulate.yml` but fails. GH #403 filed; root cause is ANTHROPIC_API_KEY missing from GitHub Actions secrets.
**Action:** Post a comment on GH #403 with the exact secret name and the two-line instructions for adding it via GitHub repo settings → Secrets and variables → Actions.
**Impact:** Unblocks KB autopopulate. Reduces KB staleness from 25+ days to near-zero. However this is tactical (comment, not code) and the fix requires human action.
**Category:** operational

---

### Idea 4: Add Step 9I (demo-role security sweep) to nightly SKILL.md
**Evidence:** GH #643 and GH #661 both require block_demo_role on new feature routers. Step 9F (KB staleness) and Step 9G (KB self-healing) established the pattern of adding enforcement steps to nightly. A nightly grep for FastAPI routers missing Depends(block_demo_role) would catch new gaps before they become issues.
**Action:** Add Step 9I to `.claude/skills/nightly-commit-review/SKILL.md` that greps `backend/routers/` for mutating endpoints (POST/PUT/PATCH/DELETE) not importing block_demo_role, and files a GH issue if any found.
**Impact:** Proactive detection of the recurring gap rather than reactive filing. Follows established Step 9F/9G nightly enforcement pattern.
**Category:** workflow

---

### Idea 5: Open comprehensive GH issue for AI-to-human handoff
**Evidence:** customer-gaps.md lists AI-to-human handoff as Critical priority, relevant to all 7 industries. governance.json frozen_ideas has `ai_human_handoff` (frozen per 3+ rejections). However the frozen entry is for a specific implementation approach, not the issue itself. GH #399 (AUTOPILOT_GH_TOKEN expiry) is still blocking the issue-to-pr-loop.
**Action:** File a GH issue scoped to "spike: define data model for human handoff sessions" — smaller than prior proposals, focused only on schema, unblocked by GH #399.
**Impact:** Moves the highest-priority customer gap one step forward. Scoped to spike prevents the "too big" objection that froze prior versions. However GH #399 blocker means issue-to-pr-loop cannot action it automatically.
**Category:** customer_value
