# Winning Concept — 2026-07-31-pm (Run 102)

## Recommendation
Add Step 9I to `.claude/skills/nightly-commit-review/SKILL.md`: when no GH Actions workflow has run successfully in the past 24 hours, post a daily escalation comment on GH #500 naming the combined pipeline-wide impact (CI blocked, Step 9G blocked, KB staying stale for paying tenants).

## Why This, Why Now
GH #500 (GH Actions spending limit) has been blocking CI and scheduled workflows for 11 days. Step 9G (added run 101 today) uses `gh workflow run kb-autopopulate.yml` — `workflow_dispatch` triggers still consume billed minutes and are blocked when the spending limit is exhausted. Tonight's nightly will fire Step 9G for the first time; it will likely exit with a non-zero code and log the spending-limit diagnostic, but that diagnostic comments on GH #403 (KB health issue) — not on GH #500 (spending limit issue). GH #500 has received zero nightly escalation comments across 11 days. The Step 9D/9E precedent proves that automated daily pressure with specific impact framing (N days, N blocked issues, specific tenant impact) is more effective than one-shot issue filing. Step 9I adds the cross-system framing that Step 9G cannot: "CI blocked + KB blocked + Step 9G blocked = 3 paying tenants on degraded AI chat." XS effort (~15-20 bash lines), same SKILL.md autonomous channel proven across Steps 9B–9G.

## Implementation Sketch

Add the following `## Step 9I` bash block to `.claude/skills/nightly-commit-review/SKILL.md`, immediately after the Step 9G block:

```bash
## Step 9I: GH Actions spending limit check

# Check for any GH Actions workflow activity in the past 24 hours
LAST_RUN_JSON=$(gh run list --repo aferna6-cell/agentnexlify --limit=1 --json status,conclusion,createdAt 2>/dev/null || echo "[]")
LAST_RUN_DATE=$(echo "$LAST_RUN_JSON" | python3 -c "
import sys, json
from datetime import datetime, timezone, timedelta
data = json.load(sys.stdin)
if not data:
    print('NONE')
else:
    created = datetime.fromisoformat(data[0]['createdAt'].replace('Z', '+00:00'))
    age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
    print(f'{age_hours:.1f}h')
" 2>/dev/null || echo "UNKNOWN")

if [[ "$LAST_RUN_DATE" == "NONE" || "$LAST_RUN_DATE" == "UNKNOWN" ]]; then
  log "Step 9I: GH Actions spending limit check — cannot determine last run"
elif python3 -c "import sys; exit(0 if float('${LAST_RUN_DATE%.h*}') > 24 else 1)" 2>/dev/null; then
  # No workflow activity in 24h — spending limit likely exhausted
  GH_SPENDING_AGE=$(($(date +%s) - $(gh issue view 500 --repo aferna6-cell/agentnexlify --json createdAt --jq '.createdAt' | xargs -I{} date -d {} +%s 2>/dev/null || echo $(date +%s))))
  GH_SPENDING_DAYS=$((GH_SPENDING_AGE / 86400))
  gh issue comment 500 --repo aferna6-cell/agentnexlify --body "**Step 9I: GH Actions spending limit check (Day ${GH_SPENDING_DAYS}):**

No GH Actions workflows have run successfully in the past 24 hours.

**Pipeline-wide impact:**
- CI blocked → PRs cannot be validated or safely merged
- \`kb-autopopulate.yml\` (Step 9G self-healing trigger) blocked → KB staying stale → AI chat quality degraded for all 3 paying tenants
- \`autopilot-issue-loop.yml\` blocked → 30+ ai-ready issues remain stalled
- PR validation blocked → Dependabot batch (#593–#598) cannot be merged

**Fix:** Increase spending limit in GitHub organization billing settings, or wait for billing cycle reset. Actions → Billing and plans → Spending limit.

*Automated escalation from nightly-commit-review Step 9I.*" 2>/dev/null && \
  log "Step 9I: GH #500 spending limit — Day ${GH_SPENDING_DAYS} escalation comment posted" || \
  log "Step 9I: GH #500 comment failed (check gh auth)"
else
  log "Step 9I: GH Actions spending limit check — workflows active (last run ${LAST_RUN_DATE} ago)"
fi
```

**Total new lines:** ~25 bash lines. Idempotent (posts comment each nightly cycle while spending limit exhausted). No new dependencies.

**Condition for no-op:** spending limit resolved → last run <24h ago → Step 9I logs "workflows active" and posts nothing.

## What This Replaces
No prior active direction covers GH #500 spending limit escalation. Steps 9D/9E monitor credential rotation and loop health; Step 9G adds KB self-healing. Step 9I closes the monitoring gap for the spending limit blocker that sits above all of them.

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across Steps 9B–9G, all shipped in 1 cycle each. `gh run list` and `gh issue comment` are both already used in the nightly context (Step 9D uses `gh run list --workflow=`; Step 9F/9G use `gh issue comment`). Failure surface limited: if `gh` auth fails, the comment fails silently and logs the error — no nightly crash. Day 11 urgency with zero automated pressure makes this immediately load-bearing.
