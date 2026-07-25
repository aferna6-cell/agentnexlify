# Winning Concept — 2026-07-25-pm (Run 102)

## Recommendation
Implement Step 9G directly in `.claude/skills/nightly-commit-review/SKILL.md`: when KB staleness exceeds 7 days, trigger `gh workflow run kb-autopopulate.yml`, check status after 30s, and comment on GH #403 with a specific diagnostic (including GH #500 spending limit as candidate cause) if the run failed or errored.

## Why This, Why Now
Step 9G was selected at run 100 (2026-07-23) and has carried forward through 3+ consecutive cycles without implementation. The 3rd carry-forward escalation rule (established by run 99/Step 9F precedent) mandates direct SKILL.md implementation — no human approval required for autonomous SKILL.md bash block additions. GH #500 (Actions spending limit) is currently active, making the GH #500-aware failure diagnostic branch immediately load-bearing: when `gh workflow run` fails, Step 9G must surface the spending limit as a candidate cause rather than silently continuing. KB is currently fresh (2026-07-23) but a 10-day gap preceded it — Step 9G prevents the next gap from going unrepaired.

## Implementation Sketch
- After the existing Step 9F block (currently ends at line 305 of SKILL.md), before Step 10 (line 306), insert `## Step 9G` bash block
- Condition: reuse `DAYS_STALE` variable from Step 9F; fire when `DAYS_STALE -gt 7`
- Action 1: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify` — attempt to trigger the workflow
- If `gh workflow run` exits non-zero (permission error, spending limit, token expired): immediately comment on GH #403 with diagnostic: "Step 9G: kb-autopopulate.yml trigger FAILED (exit code: $?). Possible causes: (1) GH Actions spending limit hit — check GH #500. (2) AUTOPILOT_GH_TOKEN expired — check GH #399. (3) Workflow dispatch disabled." Then exit with log.
- Action 2: `sleep 30` — allow GH Actions to queue and start
- Action 3: `gh run list --workflow=kb-autopopulate.yml --limit=1 --json conclusion,createdAt,url` → capture `CONCLUSION` and `RUN_URL`
- If `CONCLUSION == "success"`: log "Step 9G: kb-autopopulate triggered — SUCCESS ($RUN_URL)" and exit 0
- If `CONCLUSION == "failure"` or `"cancelled"`: comment on GH #403: "Step 9G: kb-autopopulate.yml triggered but FAILED. Check: (1) ANTHROPIC_API_KEY in GH Actions Secrets. (2) VOYAGE_API_KEY in GH Actions Secrets. (3) SUPABASE_ACCESS_TOKEN. (4) GH Actions spending limit — check GH #500. Run URL: $RUN_URL"
- If `CONCLUSION` still empty (run in progress after 30s): log "Step 9G: kb-autopopulate running — status pending" and exit 0 (CI completes on its own)
- Total new lines: ~35 bash, same template class as Step 9F block

## What This Replaces
Step 9F's alert-only posture. Step 9F fires the human alarm; Step 9G attempts repair first and only escalates to human if secrets are invalid or Actions are spending-limited. Both steps coexist — Step 9G runs after Step 9F. Audit trail preserved.

## Confidence
**HIGH** — Same channel (SKILL.md bash block) proven across 5 prior steps (9B–9F). `gh workflow run` uses `workflow_dispatch`; nightly already has write-side GH API permissions. GH #500-aware failure branch prevents silent failure. Carry-forward escalation mandate is binding per established precedent.
