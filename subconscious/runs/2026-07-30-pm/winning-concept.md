# Winning Concept — 2026-07-30-pm (Run 102)

## Recommendation
Add Step 9G-Direct to `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, attempt `gh workflow run kb-autopopulate.yml` first, then fall back to `bash scripts/daily/kb-autopopulate.sh` directly if GH Actions is unavailable (exit non-zero). Report outcome to GH #403 only on total failure. This makes KB repair independent of GH Actions spending limit.

## Why This, Why Now
KB is 7 days stale — threshold HIT TODAY (2026-07-30). Step 9G (run 100 winner) is carry-forward cycle 2 of 3. PR #577 has been open 6+ days but CI cannot validate it due to GH Actions spending limit (Day 11+). More critically: PR #577's Step 9G only has the `gh workflow run` path — which also fails when the spending limit is active. Every nightly run since 2026-07-23 could have repaired the KB but didn't, because the repair mechanism requires GH Actions.

The fallback to `bash scripts/daily/kb-autopopulate.sh` is the insight that PR #577 lacks. The script is proven (ran 2026-07-23, 2026-07-13), uses ANTHROPIC_API_KEY + VOYAGE_API_KEY (both available in nightly environment), and requires no GH Actions infrastructure. Step 9G-Direct repairs the KB **tonight** regardless of spending limit status.

## What This Changes vs PR #577
PR #577 Step 9G: `gh workflow run` only → silent failure when spending limit active.  
Step 9G-Direct: `gh workflow run` → if non-zero exit → `bash scripts/daily/kb-autopopulate.sh` → if both fail → comment on GH #403 with diagnostic.

The two designs coexist: PR #577 should be amended to add the fallback path, OR the nightly SKILL.md should add Step 9G-Direct as written here (superseding PR #577's Step 9G on merge).

## Implementation Sketch
After the existing Step 9F staleness check block in SKILL.md, add `## Step 9G-Direct` bash block:

```bash
## Step 9G-Direct — KB self-repair (GH workflow run with direct fallback)
if [ "${DAYS_STALE:-0}" -gt 7 ]; then
  echo "Step 9G-Direct: KB stale ${DAYS_STALE} days — attempting repair"

  # Path A: GH Actions workflow
  if gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify 2>/dev/null; then
    sleep 30
    CONCLUSION=$(gh run list --workflow=kb-autopopulate.yml --limit=1 \
      --json conclusion -q '.[0].conclusion' 2>/dev/null || echo "unknown")
    if [ "$CONCLUSION" = "success" ]; then
      echo "Step 9G-Direct: kb-autopopulate via GH Actions — SUCCESS"
      exit 0
    fi
    echo "Step 9G-Direct: GH Actions conclusion=${CONCLUSION}, trying direct path"
  else
    echo "Step 9G-Direct: gh workflow run failed (spending limit?), trying direct path"
  fi

  # Path B: Direct script fallback
  if bash scripts/daily/kb-autopopulate.sh; then
    echo "Step 9G-Direct: kb-autopopulate via direct script — SUCCESS"
    exit 0
  fi

  # Both paths failed — alert
  gh issue comment 403 --body \
    "Step 9G-Direct: kb-autopopulate FAILED on both paths. Check ANTHROPIC_API_KEY + VOYAGE_API_KEY. GH Actions spending limit may be active. Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    -R aferna6-cell/agentnexlify 2>/dev/null || true
  echo "Step 9G-Direct: both repair paths failed — alert posted to GH #403"
fi
```

Total: ~25 bash lines. Additive only. No node execution, no state mutation beyond KB files.

## Secondary Recommendation
Comment on PR #577 noting that: (a) the fallback path described here should be incorporated before merge, and (b) Step 9H from PR #611 should be merged first since it predates this concept. The subconscious is recommending, not implementing — the owner decides merge order.

## Escalation Status
- Step 9G: cycle 2 of 3. If NOT implemented by run 104, escalate to direct implementation.
- Step 9H: cycle 1 of 3 (PR #611, morning run 101).
- KB threshold: HIT TODAY. Urgency: CRITICAL. Implement this session or morning 2026-07-31.

## Confidence
**HIGH** — proven channel (SKILL.md bash blocks, same class as 9B–9F), both script paths verified in production, fallback pattern handles the exact failure mode blocking repair. XS effort.
