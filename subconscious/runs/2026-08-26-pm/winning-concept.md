# Winning Concept — Run 110 (2026-08-26-pm)

## Recommendation
Fix Step 9J in `.claude/skills/nightly-commit-review/SKILL.md` to gate on commit check-run conclusions instead of `mergeable_state: "clean"`, so security dep bumps actually merge.

## Why This, Why Now
Step 9J landed in nightly-2026-08-24 and first executed on nightly-2026-08-25: 19 Dependabot PRs open, **0 merged**. Every minor/patch candidate returned `mergeable_state: "unknown"` — a known GitHub API laziness behavior where mergeability is computed on demand and resets to `unknown` after inactivity. PRs aging 4+ weeks (#629/#630/#631/#649) still showed `unknown`, proving this isn't transient. The correct CI gate for automated merging is to check the PR's head commit's check-run conclusions directly (all `status: "completed"` + `conclusion: "success"`). This is what GitHub Dependabot native auto-merge uses internally. One SKILL.md edit compounds indefinitely: every security patch will merge within 24h of CI completing, permanently, without further intervention.

## Implementation Sketch
1. Open `.claude/skills/nightly-commit-review/SKILL.md`, locate the Step 9J block.
2. Remove the `mergeable_state != "clean" → skip` check.
3. Replace with:
   ```
   b. CI gate: get PR head SHA → mcp__github__actions_list (or get_check_run) filtered to
      the PR's head SHA. Skip if any check: status != "completed" OR conclusion != "success".
      Skip if no check runs found (CI not yet triggered).
   ```
4. Keep all other guards unchanged: major-version bump skip, `requested_reviewers` skip, blocking labels skip.
5. Keep the log format: `Step 9J: {N} checked, {M} merged, {K} skipped (CI/review/label/major-version)`.
6. Update the `(CI/review/label)` log suffix to `(CI-not-green/review/label/major-version)` for clarity.

**Exact check-run gate logic (pseudocode for SKILL.md block):**
```
For each Dependabot PR:
  head_sha = pr.head.sha
  check_runs = mcp__github__actions_list(repo, workflow_id=None, head_sha=head_sha)
    OR use mcp__github__get_check_run approach for each run
  If no check_runs: skip ("CI not triggered")
  If any run: status != "completed" → skip ("CI pending")
  If any run: conclusion not in ["success", "skipped"] → skip ("CI failed/cancelled")
  If all checks pass → proceed to merge
```

## What This Replaces
Previous Step 9J implementation relied on `mergeable_state: "clean"` — the GitHub REST API field that computes lazily and resets to `unknown` for inactive PRs. That gate produced 0 merges on first execution despite 19 open PRs.

## Confidence
**HIGH** — Evidence is direct (nightly log), fix is well-understood (GitHub API behavior), mechanism is autonomous-executable (SKILL.md edit), and impact compounds from first successful execution.

---

## Run 111 Mandate
1. Verify Step 9J block updated in SKILL.md: grep for `conclusion.*success` or `check_run` in Step 9J block.
2. First nightly after update: how many Dependabot PRs merged? Log: `Step 9J: {N} checked, {M} merged, {K} skipped (CI-not-green/...)`.
3. If still 0 merges: read nightly log to diagnose — are check_runs empty (CI not wired to PRs)? Are conclusions all `failure`? Different triage per failure mode.
4. GH #687 voice addon double-billing: has a PR been opened? Implementation sketch added to issue?
5. GH #669 block_demo_role middleware: any PR opened? GH #399 resolved?
6. Step 9K candidate: count open subconscious PRs — if ≥3, add Step 9K to run 111 winner.
7. churn_watch.py: verify endpoint or CLI path before proposing as a Routine step.
