# Winning Concept — Run 83 (2026-07-08-pm)

## Recommendation
Add Step 9D to `.claude/skills/nightly-commit-review/SKILL.md` — check for `ai-ready` GitHub issues with no PR opened in >24h and confirm issue-to-pr-loop GH Actions last-run timestamp is recent (<4h ago). If stalled, add a diagnostic comment to the issue and create a GH issue flagging loop dormancy.

## Why This, Why Now
Run 83 mandate: "verify issue-to-pr-loop opened a draft PR for SMS Compliance Dashboard (#385)." Morning digest (2026-07-08) says "issue-to-pr-loop should have triggered" — passive phrasing, no PR confirmed. ai-ready label was applied during nightly-2026-07-08 (~2:37 AM UTC). Five-plus hours elapsed before the morning digest was generated, giving the loop 20+ poll cycles (15-min interval) to open a PR. No PR appeared.

The silence follows the exact pattern that let brain connectors fail 8 days (Step 9C caught it after 4 days — run 79) and KB autopopulate fail 63 days. Both were fixed by adding permanent monitoring steps. Without Step 9D, the next stalled ai-ready issue goes undetected until someone notices manually.

Step 9B monitors backend healthz. Step 9C monitors brain connector ingestion. Step 9D closes the third silent-failure gap: the feature delivery pipeline (issue → PR).

## Implementation Sketch

### 1. Add Step 9D to `.claude/skills/nightly-commit-review/SKILL.md`

After the existing Step 9C (brain connector health check), insert:

```
### Step 9D — Issue-to-PR Loop Health Check

1. **Check for stalled ai-ready issues:**
   - Use `mcp__github__list_issues` on `aferna6-cell/agentnexlify` with label `ai-ready`
   - For each open ai-ready issue, check if a PR exists referencing it:
     - Search PRs with `mcp__github__search_pull_requests` for issue number in body/title
   - If any ai-ready issue has been open >24h with no linked PR → flag as stalled

2. **Check loop execution health:**
   - Use `mcp__github__actions_list` to list recent runs of `autopilot-issue-loop.yml`
   - If last successful run > 4h ago → flag as dormant
   - If workflow shows repeated failures → flag as erroring

3. **If stalled issue found:**
   - Add comment to GH issue via `mcp__github__add_issue_comment`:
     "Step 9D health check: ai-ready issue open >24h with no linked PR. 
      Loop last ran: {timestamp}. Loop status: {status}. 
      Possible causes: workflow disabled, GITHUB_TOKEN scope issue, 
      no ANTHROPIC_API_KEY in workflow env."
   - Create GH issue (or comment on #394) flagging issue-to-pr-loop dormancy
     with label `human-action-required` if loop has been dormant >4h

4. **Log result:**
   - Add to nightly commit log: "Step 9D: {N} ai-ready issues, {M} stalled, loop last ran {timestamp}"
```

### 2. Confirm #385 Status This Run
Before the permanent step lands, the nightly should manually check:
- Does a draft PR exist for SMS Compliance Dashboard (#385)?
- If not: add diagnostic comment to #385 explaining loop appears stalled

### 3. Sequence Note
Step 9D runs after Step 9C (brain connector). Both are read-only GH API calls + optional comment/issue creation. Neither blocks other nightly operations.

### 4. Autonomous Executable?
**YES** — editing SKILL.md is additive, reversible, zero-risk. No schema changes, no auth changes, no production code modified. Nightly can execute without human approval. Mark: `autonomous_executable: true`.

## What This Replaces / Extends
Run 82 winner (kb-autopopulate.yml) and run 80 winner (Step 9C) followed the same pattern: evidence of silent failure → permanent monitoring gate added. This run extends the pattern to the third pillar of the autonomous pipeline (issue → PR delivery).

## Confidence
**MEDIUM-HIGH** — the evidence is unambiguous (no PR after 5+ hours and 20+ loop cycles). Implementation is concrete (same GH API pattern as Step 9C). One uncertainty: whether issue-to-pr-loop is stalled vs just slow to trigger on first attempt for this specific issue type. Step 9D's 24h threshold is conservative enough to avoid false positives.

## Autonomous Executable?
**YES** — SKILL.md edit is zero-risk. Commit tonight.
