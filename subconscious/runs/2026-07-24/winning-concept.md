# Winning Concept — 2026-07-24 (Run 101)

## Recommendation
Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify` and report outcome (success / failure with secret names / in-progress) to GH #403.

## Why This, Why Now
Step 9F (run 99 winner) fires the human alarm. Step 9G closes the loop — it attempts repair first and only escalates to human if secrets are invalid. Step 9G has been the recommended winner since run 100 and is still absent from SKILL.md after 1 carry-forward cycle. Governance policy: implement directly at cycle 3 (run 102). Implementing at cycle 2 now to preserve the pattern. The KB was compiled 2026-07-24 (e9b4972 batch), but the GH Actions workflow remains dead (GH #403) — next stale window will arrive without self-healing unless Step 9G ships.

## Implementation Sketch
After the existing Step 9F block in SKILL.md (line 305), insert a new `9G.` section:

```
9G. (KB Autopopulate Self-Healing) If Step 9F found days_stale > 7, attempt to trigger the workflow:
    1. **Trigger workflow:**
       Run in Bash: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
       If command fails (non-zero exit — token expired or workflow not found):
         Add comment to GH #403: "Step 9G: kb-autopopulate.yml trigger FAILED (gh exit non-zero). Check: (1) ANTHROPIC_API_KEY in GH Actions Secrets. (2) VOYAGE_API_KEY in GH Actions Secrets. (3) SUPABASE_ACCESS_TOKEN in GH Actions Secrets. (4) AUTOPILOT_GH_TOKEN may be expired (#399)."
         Log: "Step 9G: trigger FAILED — comment added to GH #403"
         Continue to step 10.
    2. **Wait and parse:**
       Run in Bash: `sleep 30`
       Run in Bash: `gh run list --workflow=kb-autopopulate.yml --repo aferna6-cell/agentnexlify --limit=1 --json conclusion,createdAt,url`
       Parse JSON: extract `conclusion` and `url`.
    3. **Report result:**
       If conclusion == "success":
         Log: "Step 9G: kb-autopopulate triggered — SUCCESS ({url})"
         Continue to step 10.
       If conclusion == "failure" or conclusion == "cancelled":
         Add comment to GH #403: "Step 9G: kb-autopopulate.yml triggered but FAILED (conclusion: {conclusion}). Check: (1) ANTHROPIC_API_KEY in GH Actions Secrets. (2) VOYAGE_API_KEY in GH Actions Secrets. (3) SUPABASE_ACCESS_TOKEN in GH Actions Secrets. Run URL: {url}"
         Log: "Step 9G: kb-autopopulate FAILED — comment added to GH #403"
         Continue to step 10.
       If conclusion is empty or null (run still in progress after 30s):
         Log: "Step 9G: kb-autopopulate triggered — run in progress (conclusion pending). URL: {url}"
         Continue to step 10.
```

Total new lines: ~30 bash/prose, same template as Step 9F block. Insertion point: between line 305 and line 306 in current SKILL.md.

## What This Replaces
Step 9F's alert-only posture on KB staleness. Step 9F fires the human alarm; Step 9G attempts repair first. Both coexist — Step 9G runs only when Step 9F's staleness condition is met.

## What Goes to Parking Lot
- **Step 9H per-tenant zero-conversation heartbeat** — GH issue to file: "Alert when paying tenant has zero widget conversations for >7 days (Keys Koffee class of silent failure)." Requires Supabase query + baseline logic not available in headless nightly bash context. GH issue only this cycle.
- **GH #399 token rotation** — human action required; Step 9E already handles credential-rotation alerts. No new autonomous action available.

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across 5 prior steps (9B/9C/9D/9E/9F). `gh workflow run` uses `workflow_dispatch`; nightly has write-side GH API permissions confirmed by prior mcp__github__add_issue_comment usage. Failure surface limited: trigger failure → diagnostic comment on #403; run failure → diagnostic comment on #403; in-progress → neutral log. No silent failure path.
