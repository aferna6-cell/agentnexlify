# Debate Log — Run 101 (2026-07-30)

Top 3 ideas ranked by impact: Idea 1 (CI alerter), Idea 4 (Tenant silence alerter), Idea 2 (Step 9G PR escalation).

---

## Idea 1: Step 9H — GH Actions CI Systematic Failure Alerter

### Challenge Round 1
**Attack:** The human already knows about the current spending limit block (#500, 11 days, #1 priority per morning digest). Adding an alert on a problem that's already manually discovered and flagged is redundant noise for the current incident. This is rearranging deck chairs.

**Defend:** The value is NOT for the current incident — the human knows. The value is for the NEXT occurrence. GH Actions billing limits can be silently hit any month when AI pipeline costs spike. Without the check, the next instance is discovered manually on day 7, 9, or 11 again. The current 11-day block is the proof-of-concept that the check is needed.

### Challenge Round 2
**Attack:** The check can't reliably distinguish a billing-limit failure from a systematic code regression. If 3 tests break in a bad PR, ALL workflow runs fail. The check would false-positive on a bad deploy.

**Defend:** The check is narrowable to detect "universal failure across ALL distinct workflows, ZERO successes in last 48h." A bad PR breaks tests but not unrelated workflows (dependency scans, nightly, etc.). A spending limit hits EVERYTHING simultaneously. The signal is the intersection: ALL workflows × ZERO successes × ≥48h duration. That intersection is essentially impossible from a code regression alone.

### Challenge Round 3
**Attack:** The mechanism (nightly SKILL.md bash block) requires `gh run list` which needs GITHUB_TOKEN. If the nightly runner loses its token (like GH #399 with AUTOPILOT_GH_TOKEN), the check itself silently fails — same failure class.

**Defend:** Step 9D (issue-to-pr-loop health check) already uses `gh run list` inside nightly and it works. The nightly runner has its own token separate from AUTOPILOT_GH_TOKEN. The spending limit blocks workflow EXECUTION, not API reads. `gh run list` is a read-only API call that works even when the spending limit stops new runs from starting. This is a different failure class.

**Verdict: SURVIVES** — clear future-preventing evidence, narrowable false-positive risk, proven mechanism unaffected by the failure class it's detecting.

---

## Idea 4: Paying Tenant Silence Alerter

### Challenge Round 1
**Attack:** Run 87-88 proved Supabase MCP is unavailable in headless nightly sessions. Querying `conversations` table requires Supabase access. This idea can't be implemented in the nightly bash channel.

**Defend:** The action can be scoped to filing a GH issue NOW (autonomous subconscious action via mcp__github__issue_write) containing the SQL query for human to add to a monitoring dashboard or scheduled GH Actions job. Same pattern as run 88 (Booking Diagnostic GH issue).

### Challenge Round 2
**Attack:** Filing a GH issue is a Bonus action, not a Winner. The pattern of "file GH issue for human to do the thing" has yielded 0 human responses across runs 88-93 for booking/referral activation. Adding another "human please do this" issue into an already-crowded backlog has low expected impact.

**Defend:** The difference here is the BUG IS DOCUMENTED (bug-patterns.md 2026-07-23) with an explicit fix pattern. The booking/referral issues had implementation ambiguity. The tenant silence check is a clear 10-line SQL query. The payoff is also clearer: it's a retention-and-revenue signal, not an activation feature. That said, the mechanism mismatch (Supabase unavailable) means this idea can't be the autonomous winner.

### Challenge Round 3
**Attack:** Is this the highest-leverage thing right now? Keys Koffee's widget was the silent outage. It's already being tracked (#573). 3 tenants total. The monitoring setup is a good idea but does it beat CI health detection for the codebase's overall health?

**Defend:** No convincing defense on highest-leverage comparison. CI health is a more acute blocker affecting all 40+ ai-ready issues, all PRs, all automations.

**Verdict: WEAKENED** — correct idea, wrong mechanism for autonomous execution. Demoted to Bonus B: file GH issue with tenant silence SQL query for human to add to monitoring setup.

---

## Idea 2: Step 9G PR Escalation (Bonus A candidate)

### Challenge Round 1
**Attack:** Runs 90-93 showed that posting escalation comments on GH issues yielded 0 human responses across 7 autonomous comments on GH #413 (referral activation). The human's absence from GitHub for 11 days (GH Actions block unanswered) suggests they may not be checking GitHub regularly. A PR comment won't break through.

**Defend:** PR #577 is different from GH #413: morning digest 2026-07-29 explicitly identified it as #2 priority action and explicitly said "SKILL.md only, safe to merge even with red CI." The morning digest is a decision-support surface the human DOES review (morning digest is read daily per the routine). The comment on PR #577 reinforces what morning digest already said. This isn't redundant — it's signal amplification at the right surface.

### Challenge Round 2
**Attack:** Is this a Winner or a Bonus action? The PR comment doesn't generate new learning for the system — it's a nudge on an already-known item. Subconscious winners should move the system forward.

**Defend:** Agreed. This is a Bonus A action, not a Winner. It's correctly scoped as a complementary autonomous action to the Winner, not a standalone improvement recommendation.

**Verdict: WEAKENED → Bonus A** — correct action, wrong tier for Winner. Executes as Bonus A alongside Winner.

---

## Synthesis

**Winner: Idea 1 — Step 9H: GH Actions CI Systematic Failure Alerter**

SURVIVES all three challenge rounds. Evidence-backed by 11-day current incident. Future-preventing via proven nightly SKILL.md mechanism. False-positive risk narrowable. Not in frozen_ideas or rejected_paths.

**Bonus A (autonomous action this run):** Post comment on PR #577 (Step 9G) noting KB threshold crossed today, PR safe to merge without CI, Step 9G needed for self-repair.

**Bonus B (autonomous action this run):** File GH issue with tenant silence SQL query + implementation sketch for human to wire to monitoring.

**Parking lot:**
- Autonomy loop health check: WEAKENED (sweeper 24h old, premature daily alerting)
- graph/runtime.py size check: WEAKENED (not yet above threshold, monitor in 2 runs)
