# Winning Concept — 2026-08-06 (Run 101)

## Recommendation
Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`, check the workflow conclusion after 30 seconds, and comment on GH #403 with a specific failure diagnostic if the run did not succeed.

**This is the 4th consecutive carry-forward of Step 9G (recommended run 100, PRs #625/#626 created but not merged). Governance precedent: run 99 implemented Step 9F directly on 3rd carry-forward. This recommendation is escalated to direct implementation authority — nightly-commit-review or this session should apply the verbatim block below without waiting for PR review.**

## Why This, Why Now
KB last ran 2026-07-23 (14 days stale as of 2026-08-06). Step 9F fires correctly — morning digest confirms "Step 9F: KB STALE" comments on GH #403 — but alert-only posture leaves the KB dark indefinitely. Step 9G adds self-repair: trigger the workflow, check outcome, escalate to human only if secrets are invalid. Two PRs (#625, #626) contain the implementation but neither is merged on main. The KB feeds all 3 live tenants' AI chat answers directly; 14 days of staleness is a live product quality issue.

## Verbatim Block to Insert (after Step 9F block in SKILL.md)

Insert the following block immediately after the `## Step 9F` block (after the closing `fi` and the `fi` for the outer log check):

```bash
# Step 9G: KB autopopulate self-healing trigger
# Condition: KB staleness already computed by Step 9F as DAYS_STALE
# Reuse the DAYS_STALE variable — only run if Step 9F's staleness check was executed
if [ -n "$DAYS_STALE" ] && [ "$DAYS_STALE" -gt 7 ]; then
  log_info "Step 9G: KB stale ${DAYS_STALE} days — triggering kb-autopopulate workflow"
  if gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify 2>/dev/null; then
    sleep 30
    RUN_CONCLUSION=$(gh run list --workflow=kb-autopopulate.yml \
      -R aferna6-cell/agentnexlify \
      --limit=1 \
      --json conclusion,url \
      --jq '.[0]' 2>/dev/null || echo '{}')
    CONCLUSION=$(echo "$RUN_CONCLUSION" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('conclusion',''))" 2>/dev/null || echo "")
    RUN_URL=$(echo "$RUN_CONCLUSION" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('url',''))" 2>/dev/null || echo "")
    if [ "$CONCLUSION" = "success" ]; then
      log_info "Step 9G: kb-autopopulate triggered — SUCCESS"
    elif [ -z "$CONCLUSION" ]; then
      log_info "Step 9G: kb-autopopulate triggered — still running after 30s (status check pending)"
    else
      log_warn "Step 9G: kb-autopopulate triggered but CONCLUSION=${CONCLUSION}"
      gh issue comment 403 \
        -R aferna6-cell/agentnexlify \
        --body "**Step 9G automated report:** kb-autopopulate.yml triggered (KB stale ${DAYS_STALE} days) but run concluded with status \`${CONCLUSION}\`. Check ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GH Actions Secrets. Run: ${RUN_URL}" \
        2>/dev/null || log_warn "Step 9G: failed to comment on GH #403"
    fi
  else
    log_warn "Step 9G: gh workflow run failed — check GH Actions permissions"
    gh issue comment 403 \
      -R aferna6-cell/agentnexlify \
      --body "**Step 9G automated report:** gh workflow run kb-autopopulate.yml failed to dispatch (KB stale ${DAYS_STALE} days). Check that kb-autopopulate.yml has workflow_dispatch trigger and nightly token has workflow scope." \
      2>/dev/null || true
  fi
fi
```

## Placement in SKILL.md
- Find `## Step 9F` section (currently at ~line 265–305)
- Insert the Step 9G block immediately after the closing `fi` of the Step 9F block
- The `$DAYS_STALE` variable must be set by Step 9F's staleness calculation before Step 9G runs — confirm Step 9F sets it with `export DAYS_STALE=...` or equivalent

## What This Replaces
Step 9F's alert-only posture. Both steps coexist: Step 9F fires the human alarm AND logs to GH #403; Step 9G attempts repair first and only escalates to human if `gh workflow run` fails or the run concludes with non-success. The 63-day stale gap in early 2026 was caused by empty secrets with `continue-on-error: true` masking failure silently — Step 9G surfaces that exact failure class with a specific diagnostic.

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across Steps 9B–9F, all shipped in one cycle each. `gh workflow run` uses `workflow_dispatch`; nightly already holds write-side GH API permissions. Failure surface limited: silent failure impossible (status check + comment on #403 catches every outcome). 14-day stale window makes this immediately load-bearing.

## Bonus: bug-patterns.md Update (XS, include in same commit)
Update `docs/dev-knowledge/bug-patterns.md` top entry (2026-08-01 connector_awareness bug):
- Add `tenant_api_keys` to the list of tables covered by the `client_id` invariant
- Record that the fix was applied in `connector_registry.py` (not `connector_awareness.py`)
- Change "Files Changed: none yet" to "Files Changed: backend/services/connector_registry.py"
