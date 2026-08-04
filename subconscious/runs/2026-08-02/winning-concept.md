# Winning Concept — 2026-08-02 (Run 101)

## Recommendation
Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml`, wait 30s, check the run conclusion, and report success or failure (with specific secret names) as a comment on GH #403.

## Why This, Why Now
Step 9F fires correctly — nightly-2026-07-22 proves it: "Step 9F: KB STALE (9 days) — comment added to GH #403." But GH #403 has received multiple alert comments over months with zero human action. The KB is now 10 days stale (last run 2026-07-23), and the 3 live tenants' widget AI quality depends on freshness: stale KB = wrong or missing answers on vertical FAQs, booking hours, and service descriptions. Step 9G closes the loop: alert-only becomes alert-and-attempt-repair. If secrets are valid, kb-autopopulate.yml runs automatically. If secrets are expired or empty, the diagnostic comment on GH #403 names the exact variables to rotate — changing a vague "KB stale" alarm into an actionable "set ANTHROPIC_API_KEY in GH Actions Secrets, 2-minute fix." This is a 1st-carry-forward of run 100's winner, the same mechanism class as Steps 9B–9F (all implemented in 1 cycle each), and the KB staleness is currently load-bearing for chat quality.

## Implementation Sketch

Add the following block to `.claude/skills/nightly-commit-review/SKILL.md` **immediately after the Step 9F block**:

```markdown
### Step 9G — KB Autopopulate Self-Heal
If Step 9F reports KB stale (`DAYS_STALE -gt 7`):
1. Trigger the workflow:
   ```bash
   gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify || true
   ```
2. Wait for the run to start:
   ```bash
   sleep 30
   ```
3. Check conclusion:
   ```bash
   CONCLUSION=$(gh run list --workflow=kb-autopopulate.yml --repo=aferna6-cell/agentnexlify --limit=1 --json conclusion --jq '.[0].conclusion // "pending"')
   RUN_URL=$(gh run list --workflow=kb-autopopulate.yml --repo=aferna6-cell/agentnexlify --limit=1 --json url --jq '.[0].url // "unknown"')
   ```
4. Branch on conclusion:
   - `success`: log `Step 9G: kb-autopopulate triggered — SUCCESS. KB staleness will resolve within 1h.`
   - `failure` or `cancelled`: post GH #403 comment: "Step 9G: kb-autopopulate.yml triggered but FAILED. Check GH Actions Secrets: ANTHROPIC_API_KEY (required), VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN (optional). Run: $RUN_URL"
   - `pending` (still running): log `Step 9G: kb-autopopulate triggered — run in progress at $RUN_URL`
   - error dispatching (gh workflow run failed): log `Step 9G: workflow dispatch failed — actions:write permission may be missing from GH token`
```

The Step 9F staleness variable (`DAYS_STALE`) is already computed by Step 9F; Step 9G reuses it. No new bash tooling needed — `gh run list` already used in Step 9D.

## What This Replaces
Step 9F's alert-only posture. Step 9F fires the alarm; Step 9G attempts repair first and only escalates to human if secrets are invalid. Both steps coexist — Step 9G runs after Step 9F to preserve the audit trail. The pattern follows Step 9D → Step 9E → Step 9F progression: each Step adds a capability layer (detect → escalate → alert → repair).

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across 5 prior steps (9B, 9C, 9D, 9E, 9F), all shipped in 1 cycle each. `gh run list` already in Step 9D. Permission risk handled: if `gh workflow run` fails (no actions:write), the catch logs a diagnostic instead of crashing nightly. Current KB stale window (10 days) makes this immediately load-bearing. Failure path is explicit and non-silent for every branch.
