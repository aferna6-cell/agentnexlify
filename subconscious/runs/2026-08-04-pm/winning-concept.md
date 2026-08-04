# Winning Concept — 2026-08-04-pm (Run 101)

## Recommendation
Replace the prose-only dedup guard in `.claude/skills/subconscious/SKILL.md` Phase 8 with a mandatory STEP 0 tool-call sequence that calls `mcp__github__list_pull_requests`, filters for any open `subconscious/*` branch, and commits artifacts to that branch instead of creating a new PR.

## Why This, Why Now
Morning digest 2026-08-04 Priority 1: 5 open draft subconscious PRs, with #625 and #626 both implementing the same Step 9G KB self-heal. The existing prose guard added in run 100 ("BEFORE creating any branch or PR, list open PRs…") has already been ignored twice by headless sessions — both created new branches instead of committing to the existing one. Root cause: prose instructions in SKILL.md are not reliably followed in stateless headless contexts. The same pattern broke the moratorium escalation system across 10+ runs. Replacing prose with explicit tool-call instructions closes this failure mode structurally.

## Implementation Sketch

In `.claude/skills/subconscious/SKILL.md`, Phase 8 (Commit), insert at the TOP, before any git or PR operations:

```markdown
### STEP 0 — PR Dedup Pre-flight (MANDATORY — run before ANY git branch or PR operation)

1. Call `mcp__github__list_pull_requests` with repo=aferna6-cell/agentnexlify, state=open
2. Filter the result: find entries where `head.ref` starts with `subconscious`
3. **If ANY open subconscious PR found:**
   a. Record the branch name (e.g., `subconscious/run-101`)
   b. `git fetch origin <branch-name>`
   c. `git checkout <branch-name>` (or create if local doesn't exist: `git checkout -b <branch-name> origin/<branch-name>`)
   d. Write all run artifacts to `subconscious/runs/{date}/` on this branch
   e. `git add subconscious/ && git commit -m "subconscious: run {date} — {winner title}"`
   f. `git push origin <branch-name>`
   g. **DO NOT open a new PR.** The existing PR absorbs the new run.
   h. Call `mcp__github__update_pull_request` to append a note to PR body: "Run {date} artifacts added."
   i. **STOP** — do not continue to STEP 1 or beyond.
4. **If NO open subconscious PR found:**
   a. Proceed to STEP 1 below (create new branch + one draft PR)
```

The remaining Phase 8 steps become STEP 1 (branch creation) and STEP 2 (PR creation), executed only when STEP 0 finds nothing.

**Total new lines:** ~20 markdown lines in SKILL.md. No code changes.

## What This Replaces
The prose-only dedup guard added at the bottom of Phase 8 in run 100 (2026-07-23). That guard was correct in intent but ineffective in execution. This replaces the intent with a tool-call enforcement path.

## Confidence
**HIGH** — Same channel (SKILL.md edit) proven across Steps 9A–9F, moratorium-sprint skill, god-class-splitter skill. All delivered in 1 cycle. Tool calls (`mcp__github__list_pull_requests`) are already available in headless sessions (subconscious and nightly both have MCP access). Failure surface: if MCP is unavailable, the step fails with a visible error rather than silently creating a duplicate PR. Structural fix, not behavioral nudge.

## Run 101 Mandate Results

Items from run_101_mandate:
1. **Step 9G in SKILL.md?** `grep -c "Step 9G" .claude/skills/nightly-commit-review/SKILL.md` = **0 — FAIL.** Two competing PRs (#625, #626) unmerged. Root cause of this run's winner.
2. **KB freshness since 2026-07-13?** Last `knowledge-base/log.md` entry: 2026-07-23. Stale **12 days** as of today.
3. **Step 9G fired?** Cannot fire — Step 9G absent from SKILL.md.
4. **GH #403 Step 9G diagnostic?** None — Step 9G never ran.
5. **Agent OS tenant count:** ~2-3 (LoopHealthPage data, below 5-tenant promote threshold).
6. **MCP tenant count:** 1 (below 5-tenant Step 9H revisit threshold).

## Run 102 Mandate

1. **Dedup guard present in SKILL.md?** grep for STEP 0 / `mcp__github__list_pull_requests` in Phase 8 of `.claude/skills/subconscious/SKILL.md`. SHOULD PASS (this run's winner, delivered to existing open PR).
2. **Typed KB notes retrieval audit:** grep `backend/services/` and `backend/routers/tenant_kb.py` for `tenant_kb_documents` queries. Verify no `source=` filter excludes `source='note'` from chat retrieval path. If filter found: file LOW-risk GH issue with line reference.
3. **Step 9G still absent from SKILL.md?** If still 0: escalate to human-action GH issue with exact implementation sketch from `subconscious/runs/2026-07-23/winning-concept.md`.
4. **VOYAGE_API_KEY diagnostic:** check `knowledge-base/log.md` for "SKIPPED" or "no credentials" — if present, note in run 102 artifacts for Step 9J consideration.
5. **Open subconscious PRs:** count — should be ≤1 after this run's dedup guard lands and human resolves #625/#626.
