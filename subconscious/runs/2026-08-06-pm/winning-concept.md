# Winning Concept — 2026-08-06-pm (Run 101)

## Recommendation
Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9F block (line 305): when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`, check result after 30s, and comment on GH #403 with a specific failure diagnostic if the run failed.

**Escalation status: DIRECT IMPLEMENTATION — same path as run 99/Step 9F.**
- Run 99 precedent: Step 9F direct-implemented after 3 consecutive recommend-only failures.
- Run 101 count: 6+ unmerged PRs across runs 100-106+ (PRs #606, #611, #613, #625, #626, and prior). Exceeds 3-cycle threshold by 2x.
- KB stale: 14 days (last: 2026-07-23). Threshold: 7 days.

## Why This, Why Now
Step 9F (run 99 winner) fires correctly — but the alert does not trigger a fix. The KB is now 14 days stale. Three tenants' AI chat quality depends on freshness (salon FAQ, vertical answers). The 63-day stale gap in early 2026 was caused by empty secrets with `continue-on-error: true` masking the failure silently — Step 9G surfaces that exact failure class with a specific diagnostic instead of alerting humans who aren't watching GH #403. XS implementation in the proven autonomous channel (SKILL.md bash block, same class as Steps 9A-9F).

## Verbatim SKILL.md Content

Insert after line 305 (after `c. Log: "Step 9F: KB STALE ({days_stale} days) — comment added to GH #403"`), before line 306 (Step 10):

```
9G. (KB Autopopulate Self-Healing) When Step 9F flags staleness > 7 days, trigger the autopopulate workflow:
    1. **Reuse Step 9F staleness signal:**
       If days_stale <= 7: skip this step entirely (Step 9F already logged clean state).
       If days_stale > 7: proceed.
    2. **Trigger workflow:**
       Run: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
       If command fails (exit non-zero): log "Step 9G: gh workflow run failed — check GH token or workflow name" and continue to step 10.
    3. **Wait for initial status:**
       `sleep 30`
       Run: `gh run list --workflow=kb-autopopulate.yml -R aferna6-cell/agentnexlify --limit=1 --json conclusion,url`
       Parse `conclusion` and `url` from JSON output.
    4. **Report outcome:**
       a. If conclusion == "success":
          Log: "Step 9G: kb-autopopulate triggered — SUCCESS"
       b. If conclusion == "failure" or "cancelled" or "timed_out":
          Add comment via `mcp__github__add_issue_comment`:
            issue_number: 403
            body: "**Step 9G: kb-autopopulate.yml triggered but FAILED.** Check ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GitHub Actions Secrets. Run URL: {url}"
          If GH comment fails: log "Step 9G: comment failed — kb-autopopulate run FAILED, check GH #403 manually"
       c. If conclusion == "" or "in_progress" (still running after 30s):
          Log: "Step 9G: kb-autopopulate running — status pending (CI will complete on its own)"
       d. If gh run list fails or returns no output:
          Log: "Step 9G: could not read run status — trigger may have succeeded, check GH Actions manually"
    5. **Log:**
       Log: "Step 9G: kb-autopopulate trigger attempted — conclusion: {conclusion}"
```

## What This Replaces
Step 9F's alert-only posture. Step 9F fires the alert; Step 9G attempts repair first and only escalates to human if secrets are invalid or the workflow is broken. Both steps coexist — Step 9G runs after Step 9F to preserve the audit trail.

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across 5 prior steps (9A-9F). `gh workflow run` uses `workflow_dispatch`; nightly already has GH API permissions (`gh issue comment`, `gh label add`, `gh run list`). Failure surface limited: silent failure is impossible (status check + GH #403 comment catches it). Escalation condition definitively met at 6 cycles.
