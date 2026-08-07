# Winning Concept — 2026-08-07 (Run 102)

## Recommendation
Amend the `Step 9G` block in `.claude/skills/nightly-commit-review/SKILL.md` at case (a) (`conclusion == "success"`) to add a KB freshness check. When kb-autopopulate.yml exits 0 ("success") but `knowledge-base/log.md` last entry is still > 1 day old, post a specific diagnostic comment on GH #403 identifying the silent-green failure class.

**Escalation status: RECOMMENDATION — autonomous SKILL.md channel, XS effort, proven path.**

## Why This, Why Now

Run 102 mandate item #2 directly verifies this gap: nightly-2026-08-07 confirms GH Actions runs #269-#271 all show `conclusion: success` but KB last entry is 2026-07-23 (15 days stale). The nightly itself diagnoses the mechanism: "workflow exits 0 via `continue-on-error:true` despite missing ANTHROPIC_API_KEY / VOYAGE_API_KEY / SUPABASE_ACCESS_TOKEN."

Step 9G (run 101 winner) correctly triggers the workflow but has a blind spot: its "success" branch (SKILL.md line 318-319) logs "SUCCESS" without verifying the KB was actually updated. This produces a false-positive signal: the nightly thinks KB repair succeeded, but KB is still stale.

The amendment closes this gap with 4-5 additional lines in the existing Step 9G block.

## Verbatim SKILL.md change

**Current Step 9G case (a) (line 318-319):**
```
       a. If conclusion == "success":
          Log: "Step 9G: kb-autopopulate triggered — SUCCESS"
```

**Replace with:**
```
       a. If conclusion == "success":
          Reuse days_stale from Step 9F.
          If days_stale <= 1:
            Log: "Step 9G: kb-autopopulate triggered — SUCCESS (KB freshness confirmed)"
          Else (days_stale > 1 after a 'success' run — silent-green detected):
            Add comment via `mcp__github__add_issue_comment`:
              issue_number: 403
              body: "**Step 9G: kb-autopopulate.yml exited 0 (success) but KB still stale ({days_stale} days, last entry: {last_kb_date}).** Silent-green detected — workflow likely exiting 0 despite internal step failures (continue-on-error pattern). Check ANTHROPIC_API_KEY, VOYAGE_API_KEY, SUPABASE_ACCESS_TOKEN in GitHub Actions Secrets. Run URL: {url}. See: .github/workflows/kb-autopopulate.yml"
            If GH comment fails: log "Step 9G: comment failed — KB stale despite 'success' exit, check GH #403 manually"
            Log: "Step 9G: kb-autopopulate SUCCESS-BUT-STALE — silent-green detected, comment posted to GH #403"
```

## What This Changes

- **Before:** Step 9G alerts on failure/cancelled/timed_out only. Silent-green (success exit, no KB update) is invisible.
- **After:** Step 9G alerts on success-but-stale, posting a specific diagnostic comment on GH #403 with the mechanism identified (continue-on-error silent failure) and the exact secrets to check.

## Why Not Idea 2 (Fix the Workflow)

Fixing `kb-autopopulate.yml` to exit 1 when KB isn't updated is the correct root-cause fix. But:
1. Workflow changes are S effort + require human review (non-autonomous)
2. The SKILL.md observer check is more resilient — catches future silent failures even if the workflow changes
3. Both can coexist: observer for immediate detection, workflow fix for long-term correctness

File a GH issue (human-action-required, medium-risk) requesting the kb-autopopulate.yml fix in parallel. That is Idea 2 demoted to a bonus action, not the winner.

## Implementation Path

**Autonomous channel (nightly-commit-review SKILL.md edit):**
File: `.claude/skills/nightly-commit-review/SKILL.md`
Lines to replace: 318-319 (Step 9G case (a))
Content: verbatim block above

**Bonus (not autonomous — file as GH issue):**
Request human to review `.github/workflows/kb-autopopulate.yml` for `continue-on-error: true` on KB compilation steps and add exit-1 verification step.

## Confidence
**HIGH** — Same channel (SKILL.md amendment) proven across Steps 9A-9G. Evidence is direct and specific (nightly-2026-08-07 names exact run IDs and mechanism). Amendment is 4-5 lines in an existing step — zero blast radius outside Step 9G. Failure surface: GH comment fails → log fallback catches it (existing pattern, line 324).
