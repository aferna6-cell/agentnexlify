# Run 103 — Winning Concept (2026-08-12-pm)

## Create `.claude/skills/pr-backlog-triage/SKILL.md`

**Category:** workflow_efficiency
**Effort:** S (~20 min to write well)
**Confidence:** HIGH
**Status:** RECOMMENDED — awaiting human approval before execution

---

## Problem

AgentNexLiFy's daily routines surface PR pile-up repeatedly but have no invokable triage playbook:

- 10 open PRs as of 2026-08-12: 5 subconscious drafts, 4 Dependabot (2-9 days), 1 active
- 4 Dependabot PRs (#649 2d, #629 9d, #630 9d, #631 9d) contain security patches sitting unmerged
- Morning digest flags Dependabot pile-up as Top 3 priority on consecutive days — no autonomous action follows
- Nightly Step 9D surfaces the pile-up but has no structured classification protocol; same re-derivation cost paid each session
- skill-discovery-2026-08-10 explicit proposal: `pr-backlog-triage` as ~20 min/triage saved

Without a SKILL.md, every session that encounters the pile-up reinvents classification from scratch. The "safe to merge vs flag for human" logic is not persisted anywhere — it lives only in morning digest prose.

---

## Proposed SKILL.md Content

```markdown
# PR Backlog Triage

## Trigger
- Morning digest or nightly shows 5+ open PRs
- Dependabot PRs aging >3 days without action
- Subconscious draft PRs aging >7 days without human review  
- User invokes `/pr-triage` or asks "clean up pull requests"

## What this skill does
Classifies open PRs by type and age, provides a structured action recommendation for each,
and outputs a triage summary table. Does NOT merge or close autonomously by default.

## Prerequisites
- MCP GitHub tools available (mcp__github__list_pull_requests, mcp__github__pull_request_read)
- For autonomous merge (opt-in): `TRIAGE_AUTOMERGE_DEPENDABOT=true` env var + MCP merge scope verified

## Step 1 — Inventory open PRs
List all open PRs: number, title, author, days open, draft status, last commit date, CI status.

```bash
# MCP call
mcp__github__list_pull_requests(owner="aferna6-cell", repo="agentnexlify", state="open", per_page=25)
```

For each PR with CI needed:
```bash
mcp__github__actions_list(owner="aferna6-cell", repo="agentnexlify", branch=<head_branch>)
```

## Step 2 — Classify each PR

### Class A: Dependabot dependency updates
Criteria: author is `dependabot[bot]`, title starts with "Bump " or "Update "
Safe-to-merge criteria (all 3 required):
1. CI status = "success" on latest commit (not stale — check run timestamp within 24h)
2. Version bump is minor or patch (not major version — semver first segment unchanged)
3. No PR conflict flag (mergeable: true)

Action: Recommend MERGE if all 3 criteria met. Flag HUMAN-REVIEW if major version bump.

### Class B: Subconscious draft PRs
Criteria: title contains "subconscious:" or "ops:", draft = true
Review winning-concept.md Status field for corresponding run directory.
- Status "RECOMMENDED — awaiting human approval" → action: HOLD (pending human approval)
- Status "AUTONOMOUS-EXECUTABLE" → action: Recommend MERGE
- PR age >14 days + no human activity (no reviews, no comments from non-bot) → action: CLOSE

### Class C: Active feature/fix PRs
Criteria: non-bot author, non-draft, last commit within 7 days
Action: Flag HUMAN-REVIEW. Add label `needs-review` if label missing.

### Class D: Stale feature/fix PRs
Criteria: last commit >14 days ago, CI not passing OR no CI run
Action: Comment on PR requesting status update. Flag HUMAN-DECISION (close or update).

## Step 3 — Output triage table

Format:
```
| PR # | Title (truncated) | Class | Age | CI | Recommendation |
|------|-------------------|-------|-----|----|----------------|
| #653 | subconscious: run... | B | 0d | — | HOLD (pending approval) |
| #649 | Bump axios | A | 2d | ✓ | MERGE |
| #631 | Bump lodash | A | 9d | ✓ | MERGE |
| #630 | Bump vite | A | 9d | ✓ | MERGE |
| #629 | Bump ...types | A | 9d | ✓ | MERGE |
| #626 | ... feature | D | 10d | — | CLOSE or UPDATE |
```

Post table as output to session terminal. If running in nightly context, append to ops log.

## Step 4 — Take action (opt-in gates only)

**Default posture: SUMMARIZE ONLY.** No autonomous action.

To enable autonomous Dependabot merge (Class A only):
- Set: `TRIAGE_AUTOMERGE_DEPENDABOT=true`
- When set: merge all Class A PRs meeting all 3 safe-to-merge criteria
- After merge: post summary comment listing merged PRs and reason

To enable autonomous stale-close (Class D):
- Set: `TRIAGE_AUTOCLOSE_STALE=true`  
- When set: post close-comment + close PRs with age >14d and no recent activity
- Comment format: "Closing stale PR — reopen if active again. Last commit [date]."

## Step 5 — Log action
Append triage summary to `ops/routines/logs/pr-triage-YYYY-MM-DD.md`:
```
Date: YYYY-MM-DD
PRs inventoried: N
Class A (Dependabot): N (N recommend-merge, N flag-human)
Class B (Subconscious): N (N hold, N recommend-merge)
Class C (Active): N (N needs-review)
Class D (Stale): N (N flag-decision)
Actions taken: [none | list of merges/closes]
```

## Canonical reference
`ops/routines/logs/morning-digest-*.md` — daily PR inventory for comparison to prior day.
`subconscious/runs/*/winning-concept.md` — Status field governs Class B decisions.

## Anti-patterns
- Never merge without CI status verified within 24h (stale CI is unsafe)
- Never merge major version Dependabot bumps autonomously — flag for human
- Never close a feature PR without a comment explaining why
- Never merge subconscious drafts without "AUTONOMOUS-EXECUTABLE" status confirmed in winning-concept.md
- Never invoke autonomous gates without verifying MCP merge scope first
```

---

## Why This Wins

1. **Evidence density:** skill-discovery-2026-08-10 explicit proposal + consecutive morning digest Top 3 flag + 4 Dependabot PRs aging 2-9 days = strongest multi-source pattern this run.
2. **No existing coverage:** No SKILL.md covers PR triage. Step 9D (nightly) surfaces pile-up but has no action playbook.
3. **Unblocked:** Primary function (classify + summarize) requires only MCP read access — works regardless of AUTOPILOT_GH_TOKEN expiry status.
4. **Conservative by design:** Autonomous action gated behind explicit env vars. Default is summary-only. Passed P1 parking lot debate (run 102).
5. **Atomic:** One new file. No existing code touched. No implementation risk.
6. **Subsumes killed Idea 3:** Dependabot auto-merge (Step 9H debate kill) is handled as an opt-in gate in this SKILL.md — no separate nightly step needed.

---

## Next Action (for human approval)

Write `.claude/skills/pr-backlog-triage/SKILL.md` with the content above.

This is a documentation-only change. Does not modify any backend code, nightly SKILL.md, or governance state beyond what run 103 persists. Creates one new skill file.

Estimated effort: 20 minutes including validation pass.
