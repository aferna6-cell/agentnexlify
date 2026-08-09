# Winning Concept — 2026-08-09-pm (Run 102)

## Recommendation
Add Step 9H to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9G: when ≥1 subconscious draft PR is open AND either (a) the count changed since last nightly OR (b) the oldest PR has been open >7 days and no Step 9H alert has fired in the last 7 nightly logs, post a summary comment on the oldest open PR and log the alert date.

## Why This, Why Now
Run 102 governance mandate explicitly directs re-raising Step 9H with idempotent design after confirming the PR pile condition met (4 open PRs, oldest 12 days). Human currently has zero automated signal about PR pile age — no existing step in the nightly skill checks open PR count or age. The once-weekly idempotency (last-7-logs grep) prevents the design flaw that killed the prior concept ("fires every nightly indefinitely"). The SKILL.md bash-block channel is the proven autonomous implementation path for all Steps 9A–9G; Step 9H fits the same class with identical risk surface.

## Implementation Sketch

Insert after the Step 9G block in `.claude/skills/nightly-commit-review/SKILL.md` (after the "Log: Step 9G..." line, before Step 10):

```
9H. (Subconscious PR Pile Alert — Idempotent) Check for stale open subconscious PRs:
    1. **Query open subconscious PRs:**
       Run: `gh pr list --repo aferna6-cell/agentnexlify --state open --search "head:subconscious" --json number,title,createdAt`
       Parse JSON: count open PRs; identify oldest PR (min createdAt); calculate age_days for oldest.
       If count == 0: log "Step 9H: no open subconscious PRs — skip" and continue to step 10.
    2. **Idempotency check:**
       Grep last 7 nightly logs for "Step 9H: alert sent":
       `grep -r "Step 9H: alert sent" ops/routines/logs/ | tail -7`
       If match found within last 7 logs AND count unchanged from last nightly: skip (idempotency guard).
       Proceed if: (a) count increased since last nightly log OR (b) oldest PR age > 7 days AND no 9H alert in last 7 logs.
    3. **Post alert comment on oldest PR:**
       Via `mcp__github__add_issue_comment`:
         issue_number: <oldest PR number>
         body: "**Subconscious PR pile: {count} open draft PR(s).** Oldest: #{oldest_number} — {age_days} days open (created {oldest_date}). Please review, merge, or close to unblock the subconscious improvement loop."
       If comment fails: log "Step 9H: comment failed — PR pile at {count} PRs, oldest {age_days} days"
    4. **Log:**
       Log: "Step 9H: alert sent — {count} open PRs, oldest #{oldest_number} ({age_days}d). Comment on PR #{oldest_number}."
       (This log entry is the idempotency sentinel for future 9H checks.)
```

**Bonus action** (include in same PR, low risk): Add `.eq("tenant_id".*client_id` to Step 3's grep targets for `tenant_api_keys` table — catches 5th recurrence of most-frequent bug class. One additional grep line in the existing Step 3 block.

## What This Replaces
No active step covers PR pile monitoring. Steps 9F/9G handle KB staleness. Step 9H is a net-new addition, not a replacement. It extends the same autonomous signaling pattern to cover the PR lifecycle gap.

## Confidence
**HIGH** — Governance mandate is explicit and unambiguous. Evidence confirmed (4 PRs open, oldest 12 days). SKILL.md bash-block channel proven across 7 prior steps (9A–9G). Idempotency design is simple (log grep, safe failure mode = alert, not silent). Debate verdict: SURVIVES without weakening.
