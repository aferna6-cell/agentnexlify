# Winning Concept — Run 101
**Date:** 2026-08-02-pm
**Winner:** Step 9G — KB Self-Healing Trigger in Nightly SKILL.md

---

## The Problem

Step 9F (implemented run 99) detects KB staleness and files a GH issue. It does NOT self-repair. GH #403 has been open since run 100 with no human action. The KB is currently 10 days stale (last run: 2026-07-23, threshold: 7 days).

Step 9F generates an alert. Nobody acted on it. The alert is not enough.

## The Fix

Add Step 9G to `.claude/skills/nightly-commit-review/SKILL.md` immediately after the Step 9F staleness check block.

**Step 9G logic:**
1. If Step 9F detected staleness (KB > 7 days old):
2. Check if kb-autopopulate workflow is already running: `gh run list --workflow=kb-autopopulate.yml --status=in_progress --limit 1`
3. If NOT running: trigger `gh workflow run kb-autopopulate.yml`
4. Log: "Step 9G: KB self-healing trigger fired — kb-autopopulate.yml dispatched"
5. If already running: log "Step 9G: kb-autopopulate.yml already in progress — skipping trigger"

**SKILL.md insertion point:** After the existing Step 9F block (KB staleness alert), before Step 9H or the final commit step.

## Why This

- **Currently active:** KB is stale right now. This fix would have fired last night.
- **Zero new infrastructure:** `gh workflow run` uses the same token as every other `gh` command in the nightly routine. `.github/workflows/kb-autopopulate.yml` already exists.
- **Closes the Step 9F gap:** Alert without self-repair = incomplete channel. Step 9F + Step 9G = complete self-maintaining KB pipeline.
- **Atomic:** One SKILL.md edit, ~10 lines. No backend changes, no migrations, no frontend changes.
- **Mandated:** run_101_mandate item #1 explicitly asks "Step 9G present in SKILL.md?"

## Implementation Plan (for human executor)

1. Read `.claude/skills/nightly-commit-review/SKILL.md` in full
2. Find the Step 9F staleness detection block
3. Insert Step 9G immediately after:
   ```
   ## Step 9G — KB Self-Healing Trigger
   If Step 9F detected staleness:
   - Run: `gh run list --workflow=kb-autopopulate.yml --status=in_progress --limit 1`
   - If empty: run `gh workflow run kb-autopopulate.yml`
     - Log: "Step 9G: KB self-healing trigger fired"
   - If non-empty: log "Step 9G: already running — skip"
   ```
4. Commit: `ops: add Step 9G KB self-healing trigger to nightly SKILL.md`

## Success Criteria

- `grep "9G\|kb_autopopulate\|kb-autopopulate" .claude/skills/nightly-commit-review/SKILL.md` returns ≥1 result
- Next nightly run: if KB stale, kb-autopopulate.yml dispatched automatically
- KB staleness gap closes within 24h of implementation without manual intervention

## Risk

- LOW: `AUTOPILOT_GH_TOKEN` must have `workflow` scope for `gh workflow run`. Nightly routine already uses this token for other `gh` operations. If scope is missing, trigger fails silently — nightly continues, KB remains stale (no regression, no new failure mode).
- Mitigation: document the token scope requirement in the SKILL.md comment.
