# Winning Concept — Run 121 (2026-09-12)

**Winner:** Step 9G MCP Fix — Replace gh CLI with `mcp__github__actions_run_trigger`
**Category:** operational
**Effort:** XS (single block edit in SKILL.md)
**Confidence:** HIGH
**Source:** Run 120 mandate item 6 + KB staleness evidence (17d stale)
**Carry-forward count:** 0 (new winner this run — NOT a carry-forward)

---

## Recommendation

Replace `gh workflow run` / `gh run list` in Step 9G of `.claude/skills/nightly-commit-review/SKILL.md` with `mcp__github__actions_run_trigger` and `mcp__github__actions_list` so the KB autopopulate self-healing trigger works in cloud CCR sessions where gh CLI is unavailable.

---

## Why This, Why Now

Step 9G was implemented in run 101 using `gh workflow run kb-autopopulate.yml` — but the gh CLI is not installed in cloud-hosted CCR sessions (the environment where the nightly runs). Every nightly since run 101 has silently failed at Step 9G. The result: knowledge-base/log.md shows last run 2026-08-26 — 17 days stale against a 7-day staleness threshold. The KB feeds the `kb-first` rule, so stale KB means agents are operating without their knowledge substrate. The fix is XS effort: `mcp__github__actions_run_trigger` is available in CCR sessions (confirmed in MCP tool list) and is the correct tool for triggering GitHub Actions workflows from within this environment.

Run 120 mandate item 6 explicitly calls for this evaluation. The debate produced SURVIVES verdict with a tight causal chain and clear precedent (Step 9J was also a "fix" to an already-implemented step, accepted as run 112 winner).

---

## Implementation Sketch

Edit `.claude/skills/nightly-commit-review/SKILL.md`, Step 9G block (lines ~318–342):

**Replace:**
```
       Run: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`
       If command fails (exit non-zero): log "Step 9G: gh workflow run failed — check GH token or workflow name" and continue to step 10.
```

**With:**
```
       Call: `mcp__github__actions_run_trigger(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml", ref="main")`
       If call raises error: log "Step 9G: mcp__github__actions_run_trigger failed — check ANTHROPIC_API_KEY in GH Secrets or workflow file name" and continue to step 10.
```

**Replace:**
```
       Run: `gh run list --workflow=kb-autopopulate.yml -R aferna6-cell/agentnexlify --limit=1 --json conclusion,url`
```

**With:**
```
       Call: `mcp__github__actions_list(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml", per_page=1)`
       Read latest run: `conclusion` field (success/failure/cancelled) and `html_url` for GH issue body
```

**Dedup guard:** Step 9G should only trigger if Step 9F confirmed staleness > 7 days (this logic is already in the SKILL.md — preserve it).

---

## Prerequisites / Open Blockers

**This is a RECOMMENDATION ONLY.** Per subconscious SKILL.md design: "The subconscious RECOMMENDS but does NOT implement." Human approval and execution in a separate nightly session required.

Before implementing, two prerequisites must be resolved:

1. **Verify `mcp__github__actions_run_trigger` availability in nightly CCR sessions.** The tool appears in the deferred tool list during subconscious runs but its presence in the specific CCR environment used by nightly-commit-review has not been confirmed end-to-end. Verify before editing SKILL.md.

2. **GH #403 (ANTHROPIC_API_KEY missing from GitHub Actions secrets) must be resolved.** The `kb-autopopulate.yml` workflow calls the Anthropic API — it will fail even after Step 9G is fixed if the `ANTHROPIC_API_KEY` secret is absent from the repository Actions secrets. Step 9G fix is **necessary but not sufficient** for KB health restoration. Both this fix and #403 must be resolved together.

The Step 9G MCP fix is the right recommendation — the gh CLI root cause is real and confirmed. But the end-to-end chain includes #403 as a second required fix. Run 122 mandate items 1-3 explicitly verify both.

---

## Verification After Implementation

```bash
grep 'mcp__github__actions_run_trigger' .claude/skills/nightly-commit-review/SKILL.md
grep 'mcp__github__actions_list' .claude/skills/nightly-commit-review/SKILL.md
# Both must return results in Step 9G block
# Also confirm gh workflow run is NO LONGER in Step 9G:
grep 'gh workflow run' .claude/skills/nightly-commit-review/SKILL.md
# Must return 0 results
```

---

## What This Replaces

Previous active direction: Step 9E credential expiry escalation (run 119/120 winner — **implemented** as of run 120. Mandate items confirmed complete. No pending escalation needed for that direction.)

---

## Run 122 Mandate

1. Verify grep: `mcp__github__actions_run_trigger` present, `gh workflow run` absent from Step 9G
2. Did Step 9G fire in next nightly after implementation? Check nightly log for "Step 9G: kb-autopopulate triggered — SUCCESS"
3. Has knowledge-base/log.md received a new entry? (confirms end-to-end flow)
4. AUTOPILOT_GH_TOKEN: check days_since_rotation — at ~76d threshold expects Step 9E to fire and GH #399 comment added
5. SUPABASE_ACCESS_TOKEN: has human filled in rotation date? If not → file GH issue directly (parking lot Idea 4)
6. os_tool_executions.py line count: if ≥480L → consider Step 9M (parking lot Idea 3)

---

## Escalation Path

- Run 121 (this run): recommend
- Run 122: if not implemented → 1st carry-forward → recommend with escalation flag
- Run 123: if not implemented → 2nd carry-forward
- Run 124: if not implemented → autonomous-executable (precedent: Steps 9F/9G/9I/9J/9K/9L)
