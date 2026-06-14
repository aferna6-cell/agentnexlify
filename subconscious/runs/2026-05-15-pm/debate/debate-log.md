# Debate Log — Run 18 (2026-05-15-pm)

Top 3 ideas ranked by impact × governance priority: Idea 1 (mandated), Idea 3 (new workflow),
Idea 4 (highest-ROI parking lot).

---

## Idea 1: Automated Moratorium Escalation Hook

### Challenge Round 1
**Objection:** GH CLI (`gh`) is not available in the execution environment (confirmed: `which gh`
returns empty). The nightly-commit-review SKILL.md step 8 says "open via `gh issue create`".
If this same env limitation applies to the skill, the escalation step would silently fail.

**Defense:** The nightly-commit-review SKILL.md already acknowledges this: "gh CLI
unauthenticated → skip issue creation, write findings to report only." The script invokes
Claude Code (`claude -p`), not `gh` directly. Claude Code has `mcp__github__` MCP tools
available. The SKILL.md Scheduled Task Prompt should be updated to use
`mcp__github__create_issue` (MCP tool) not `gh issue create` (CLI command). This is
exactly the right fix — align the implementation with what Claude Code actually has.

### Challenge Round 2
**Objection:** Is this the highest-leverage thing? The moratorium exists because the human
hasn't approved/implemented items. Creating GH issues won't change capacity constraints.
The real blocker is human time, not notification channel.

**Defense:** We don't know if the human is aware that the same recommendation has been
made 4 consecutive times across 21 days. The current notification mechanism
(commit messages, PDF files in subconscious/) has low conversion — it requires intentionally
looking at the repo. GH issues push to email notifications and appear in the Issues tab
where implementation work is tracked. The JS Silent Catch Guard precedent (5 moratorium
runs, May 4 implemented) suggests persistence works — the mechanism here is to add a
second, higher-friction notification channel. Even if capacity is the constraint, visible
GH issues accelerate prioritization decisions.

### Challenge Round 3
**Objection:** Adding moratorium tracking to the nightly review skill creates scope
bloat. The nightly review is for bugs, not workflow meta-tasks.

**Defense:** The nightly review SKILL already includes "Pre-Existing Tracked Issues"
and "Subconscious Moratorium Status" sections in its reports (confirmed in 3 consecutive
nightly reviews May 13-15). The behavior is already there in prose; we're just adding
the GH issue creation step. The skill evolves with the project's needs — governance
alerting is within its remit.

**Verdict: SURVIVES → WINNER**
Governance mandate enforced. Technical feasibility confirmed (mcp__github__ not gh CLI).
Defense holds on all 3 challenges. Strongest evidence base of any candidate this run.

---

## Idea 3: PR Queue Auto-Merge for Safe Patch Deps

### Challenge Round 1
**Objection:** Auto-merging PRs, even "safe" patch bumps, violates security principles.
Supply chain attacks target exactly these "minor" dependency updates. The project has
explicit supply-chain-risk-auditor plugin installed (Trail of Bits). Auto-merge bypasses
human review for a known attack vector.

**Defense:** All 4 PRs are already Dependabot-style bumps, likely already reviewed by
any CI automation. Patch-only semver means no API changes. CI is green.

### Challenge Round 2
**Objection:** Moratorium protocol overrides. The moratorium exists because there are 4
pending approvals, 1 at 29 days. Adding new automation (morning-digest skill update)
while 4 existing approvals sit unimplemented is exactly the pattern moratorium prevents:
"build more system" instead of "implement approved items."

**Defense:** These are independent concerns — PR merges vs governance items.

### Challenge Round 3
**Objection:** This is project management (decide which PRs to merge), not platform
improvement. The subconscious brief says improvement categories are: code health,
workflow efficiency, agent performance, customer value, operational. Auto-merging
deps is ops, but it puts autonomous merging behavior into a digest tool that shouldn't
be making security decisions autonomously.

**Verdict: KILLED**
Three strong independent objections: supply chain risk, moratorium protocol override,
scope (autonomous security decisions in a digest tool). The morning-digest should flag
and recommend; humans should execute merges.

---

## Idea 4: Email Sequences N+1 Query Fix

### Challenge Round 1
**Objection:** Moratorium protocol is active. Current pending_approvals = 4 > threshold = 3.
The moratorium governance is categorical: parking lot items cannot be elevated to winner
while moratorium is active. This applies regardless of ROI score.

**Defense:** ROI 2.3 is real, GH #112 is 13 days old, email automation is in active sprint.

### Challenge Round 2
**Objection:** No customer escalation. No production incident. The N+1 only bites at scale
that hasn't been reached yet. Recommending this as winner while 4 governance items (some
29 days old) await implementation would be selecting technical polish over workflow health.

**Defense:** The fix is bounded M-effort and prevents future pain.

### Challenge Round 3
**Objection:** Selecting this over the mandated Escalation Hook would directly undermine
the governance system this run established. The governance mandate exists precisely because
"good ideas" keep displacing boring-but-critical items. Violating it on run 18 resets the
accountability mechanism to zero.

**Verdict: KILLED**
Moratorium protocol is categorical. Run 17 mandate is binding. Track in parking lot.
Promote when moratorium exits (pending ≤ 3).

---

## Summary

| Idea | Verdict | Reason |
|------|---------|--------|
| Automated Moratorium Escalation Hook | **SURVIVES → WINNER** | Governance mandate + sound technical impl |
| Widget 3-Copy Sync Guard | N/A (governance override) | Demoted to Bonus step |
| PR Queue Auto-Merge | **KILLED** | Supply chain risk + moratorium protocol |
| Email Sequences N+1 | **KILLED** | Moratorium protocol categorical |
| Wire check_project_invariants.py | N/A (active direction) | Bonus B |
