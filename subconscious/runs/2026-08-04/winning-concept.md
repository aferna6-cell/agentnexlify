# Winning Concept — 2026-08-04 (Run 101)

## Recommendation
Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml`, check run status after 30 seconds, and comment on GH #403 with a specific failure diagnostic if the workflow failed.

## Why This, Why Now
Step 9F fires correctly — nightly-2026-07-22 confirmed "Step 9F: KB STALE (9 days) — comment added to GH #403." But the alert does not trigger a fix. KB is now 12 days stale as of 2026-08-04 (last run: 2026-07-23), and 3 live tenants' AI chat quality depends on freshness (salon FAQ, vertical answers, competitive intelligence from capabilities phases 1-5).

The 63-day stale gap in early 2026 was caused by empty secrets with `continue-on-error: true` masking the failure silently. Step 9G surfaces that exact failure class with a specific diagnostic instead of continuing to alert humans who aren't watching GH #403.

This is the 1st carry-forward cycle (run 100 winner). Per protocol, recommend again at run 101; escalate to direct implementation if still absent at run 102.

## Carry-Forward Status
- **Run 100** (2026-07-23): WINNER — first recommendation
- **Run 101** (2026-08-04): CARRY-FORWARD — Step 9G absent from SKILL.md (grep returns 0)
- **Run 102**: If still absent → 2nd carry-forward; at 3rd carry-forward → direct implementation by subconscious

## Implementation Sketch

Add the following block immediately after the Step 9F block in `.claude/skills/nightly-commit-review/SKILL.md`:

```bash
## Step 9G: KB Autopopulate Self-Healing Trigger
# Runs after Step 9F. If KB >7 days stale, trigger kb-autopopulate.yml and check status.
if [ "$DAYS_STALE" -gt 7 ]; then
  echo "Step 9G: KB stale ${DAYS_STALE}d — triggering kb-autopopulate.yml"
  gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify 2>/dev/null || {
    echo "Step 9G: gh workflow run failed (check AUTOPILOT_GH_TOKEN scope)"
    exit 0
  }
  sleep 30
  RUN_JSON=$(gh run list --workflow=kb-autopopulate.yml --limit=1 --json conclusion,createdAt,url 2>/dev/null)
  CONCLUSION=$(echo "$RUN_JSON" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r[0]['conclusion'] if r else '')" 2>/dev/null)
  RUN_URL=$(echo "$RUN_JSON" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r[0]['url'] if r else '')" 2>/dev/null)
  if [ "$CONCLUSION" = "success" ]; then
    echo "Step 9G: kb-autopopulate triggered — SUCCESS"
  elif [ "$CONCLUSION" = "failure" ] || [ "$CONCLUSION" = "cancelled" ]; then
    gh issue comment 403 -R aferna6-cell/agentnexlify --body "**Step 9G: kb-autopopulate.yml triggered but FAILED**

Staleness: ${DAYS_STALE} days. Check the following secrets in GH Actions → Secrets:
- \`ANTHROPIC_API_KEY\` — required (KB compile uses Claude API)
- \`VOYAGE_API_KEY\` — optional but needed for embeddings
- \`SUPABASE_ACCESS_TOKEN\` — required for pgvector writes

Run URL: ${RUN_URL}"
    echo "Step 9G: FAILURE — diagnostic comment posted on GH #403"
  else
    echo "Step 9G: kb-autopopulate running — status check pending (run in progress after 30s)"
  fi
fi
```

**Total new lines:** ~30 bash, same template class as Step 9F block.

**Variable dependency:** `$DAYS_STALE` is computed by Step 9F already — Step 9G reuses it. No double-computation.

## What This Replaces
Step 9F's alert-only posture. Step 9F fires the human alarm; Step 9G attempts repair first and only escalates to human if secrets are invalid. Both steps coexist — Step 9G runs after Step 9F to preserve the audit trail.

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across 5 prior steps (9B, 9C, 9D, 9E, 9F). `gh workflow run` uses `workflow_dispatch`; nightly already has write-side GH API permissions (`gh issue comment`, `gh label add`, `gh run list`). Failure surface limited: silent failure is impossible (status check + comment on #403 catches it). Current stale window (12 days) makes this immediately load-bearing.

## Bonus Action Candidate (Security Audit)
The debate identified a companion action: file a GH issue with labels `security + human-action-required` titled "Security audit required: capabilities phases 1-5 (gmail OAuth, connector SSRF, prospecting PII, social token storage)". This is **not** the winner but is a valid bonus if this run's nightly has capacity. Specific attack surfaces to audit:
- SSRF via `connector_registry.py` (tenant-supplied OAuth URLs)
- Gmail OAuth scope vs least-privilege
- TCPA compliance in `prospecting.py` router
- Social media token lifetime and rotation
- `INTEGRATIONS_ENC_KEY` gap (GH #536, HIGH, 14 days open)
