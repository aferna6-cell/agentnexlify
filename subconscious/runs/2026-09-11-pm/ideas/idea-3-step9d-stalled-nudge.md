# Idea 3: Step 9D stalled issues auto-nudge (14d threshold)

**Evidence:**
- 3 ai-ready issues stalled: GH #728 (10d), #669 (22d), #660 (27d). No linked PRs.
- GH #669 (95 routers missing block_demo_role) stalled 22 days — security gap.
- Run 119 parking lot: "Step 9D stalled issues nudge (14d)".
- Step 9D currently reports stalled issues in nightly log but does NOT auto-comment on the GH issues themselves.

**Action:**
Edit Step 9D in SKILL.md: after logging stalled issues, add nudge comment to each stalled issue with no linked PR after 14 days:
"Automated nudge: this ai-ready issue has no linked PR after {N} days. If the autopilot loop is stalled, the likely cause is AUTOPILOT_GH_TOKEN expiry. Action: rotate token in Railway → GitHub Secrets."

**Impact:**
GH issue subscribers get email notification. Human attention drawn to stalled security issues.

**Weakness:** Historical evidence: autonomous comments on GH #413 (5 comments) produced zero human action. Same auto-nudge mechanism proven low ROI for driving human response. Loop root cause is AUTOPILOT_GH_TOKEN — comments don't fix that.

**Category:** workflow_efficiency

**Effort:** S

**Confidence:** LOW — mechanism proven ineffective historically.
