# Improvement Backlog — 2026-08-08 (Run 102)

## Active — Winner This Run

### Nightly Detached HEAD Guard (WINNER — AUTONOMOUS-EXECUTABLE)
**Status:** PENDING NIGHTLY IMPLEMENTATION
**Category:** operational
**Effort:** XS (~10 lines bash in SKILL.md)
**Evidence:** nightly-2026-08-07 committed on detached HEAD — 3 commits orphaned, production MEDIUM bug unpatched 24h. SKILL.md Scheduled Task Prompt lacks branch check before `git pull`. Fix: insert branch check at step 1.5.
**Implementation:** See `winning-concept.md` for verbatim SKILL.md patch. Autonomous-executable via SKILL.md-edit channel.
**Next run mandate:** Verify step 1.5 is present in SKILL.md (grep "CURRENT_BRANCH\|Branch check PASS"). Verify nightly-2026-08-09 log shows "Branch check PASS" line.

---

## Parking Lot

### Step 9F/9G zero-commit path coverage (WEAKENED from debate — verify first)
**Status:** Parking lot — needs verification before implementation
**Category:** operational
**Effort:** XS (2-line condition change in SKILL.md if gap confirmed)
**Evidence:** nightly-2026-08-08 had 0 commits. Step 4 says "If zero commits: write empty report, exit." Unclear if Step 9F/9G executes before or after this exit in practice. KB 16 days stale.
**Action:** In run 103, check if a zero-commit nightly log contains "Step 9F:" line. If absent: patch SKILL.md to move Step 9F/9G before the zero-commit early-exit.
**Promote when:** nightly log confirms Step 9F/9G is missing from zero-commit nights.

### Grandfathered plan gate audit (promoted from run 101 parking lot)
**Status:** Parking lot — revenue integrity, no new urgency signal
**Category:** code_health / revenue
**Effort:** S (grep + read files + file GH issues)
**Evidence:** 2869124 fixed AI Workforce gate missing grandfathered plans (growth/autopilot/professional/enterprise). Class-of-bug may recur on new gates.
**Action:** `grep -rn 'plan.*==.*"agent_os"\|plan.*in.*\["agent_os"\]' backend/` — verify each hit includes grandfathered plans. File GH issue per gap. Labels: `revenue`, `medium-risk`.
**Promote when:** Morning digest or next subconscious run elevates this. Or when a grandfathered customer reports feature access issue.

### response_score.py ai_usage_guard routing audit (promoted from run 101 parking lot)
**Status:** Parking lot — cost protection
**Category:** code_health
**Effort:** XS (read file + grep ai_usage_guard routing)
**Evidence:** e0e9be6 (2026-08-06) ships response_score.py (151 lines, Claude-calling). Nightly reviewed at MEDIUM risk but did NOT verify ai_usage_guard routing. widget_guard.py precedent (run 94) shows this class matters.
**Action:** Add to nightly Step 5 (security/cost review) criteria: "Verify new Claude-calling services route through ai_usage_guard." Also: manually read response_score.py and grep for ai_usage_guard import.
**Promote when:** Next nightly commit review fires OR response_score.py receives >1 tenant call-site.

### Step 9H redesign — idempotent subconscious PR pile-up alerter (re-promoted)
**Status:** Parking lot — needs idempotent design
**Category:** operational/workflow
**Effort:** S (~20 lines in SKILL.md + governance.json tracking field)
**Evidence:** 4 open subconscious draft PRs as of 2026-08-08: #626, #613, #611, #606. Prior design rejected (fires every nightly — noise). New design: track `last_pile_alert_count` in governance.json; only alert when count INCREASES.
**Design:** Step 9H block in SKILL.md: list open `subconscious` PRs, compare count to governance.last_pile_alert_count, alert on increase only, update field.
**Promote when:** PR pile grows further OR human explicitly asks about it. 4 open is already concerning.

### Typed KB notes discovery prompt (from run 101)
**Status:** Parking lot — customer_value, no technical blocker
**Category:** customer_value
**Effort:** S (~30 lines in KnowledgeSourcesPage.jsx + backend dismiss flag)
**Evidence:** 4853c31 (2026-08-04, PR #632) ships typed KB notes. 3 existing tenants won't discover without in-app notification. No one-time banner pattern exists in dashboard.
**Action:** Dismissible info banner at top of KnowledgeSourcesPage.jsx. Dismiss state stored as per-tenant backend flag (CLAUDE.md Rule 6: no localStorage).
**Promote when:** Human merges PR #632 to main AND this surfaces in morning digest as top gap.

---

## Previously Active (carried forward, all implemented)

### Step 9G: KB autopopulate self-healing trigger
**Status:** IMPLEMENTED (run 101 winner, direct escalation to main)
**Notes:** Working. Step 9G triggered nightly-2026-08-07 (KB 15d stale). Workflow conclusion "pending" — likely silent failure via continue-on-error. Human action required: verify ANTHROPIC_API_KEY, VOYAGE_API_KEY, SUPABASE_ACCESS_TOKEN in GH Actions Secrets.

### Step 9F: KB Autopopulate Staleness Check
**Status:** IMPLEMENTED (run 99 winner, nightly-2026-07-22 confirmed firing)
**Notes:** Working as designed. Step 9G escalates it.

---

## Rejected

### ai_human_handoff (FROZEN — 3+ rejections)
**Status:** FROZEN — do not re-propose

### Step 9H v1 — naive PR comment on count >3 (KILLED run 100)
**Status:** KILLED — fires every nightly, no convergence. Redesign needed (idempotent version in parking lot above).
