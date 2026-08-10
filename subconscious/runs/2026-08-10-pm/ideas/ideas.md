# Ideas — Run 102 (2026-08-10-pm)

## Evidence Digest

**KB 18 days stale.** Step 9G fired on 2026-08-07 (`gh workflow run` returned 204, queued). GH Actions showed runs #269-#271 `conclusion: success`. But KB log still shows 2026-07-23 as last run. Root cause: `continue-on-error: true` in kb-autopopulate.yml allows the workflow to exit 0 even when ANTHROPIC_API_KEY / VOYAGE_API_KEY / SUPABASE_ACCESS_TOKEN are missing — no articles compiled, no error surfaced. Step 9G's verification checks workflow `conclusion` only, not whether KB log advanced. Nightly-2026-08-07 identified this class explicitly.

**Detached HEAD incident (2026-08-07).** Nightly committed `block_demo_role` fix on detached HEAD. Commits orphaned (`97e1044`, `cbbaae5`, `7dff08b`). Fix had to be re-applied on 2026-08-08. Double nightly cycle spent on same bug.

**PR backlog: 10 open PRs.** 6 autonomy DRAFTs (oldest: 13d), 3 Dependabot (#629, #630, #631) ready-to-merge, 1 fastapi cap lift (#604). Morning digest has flagged this for multiple days as Top 3 Priority. PR #596 explicitly superseded by #604.

**Skill discovery (2026-08-10).** Proposed: `pr-backlog-triage` skill, `route-security-guard-audit` skill, nightly detached HEAD guard (exact bash code provided), `feature-build` 5-file pattern update.

**Recent bug patterns:** `block_demo_role` missing on new billing endpoint (MEDIUM, fixed twice). `connector_awareness` used `tenant_id` instead of `client_id` on `tenant_api_keys` (same column-naming bug class, again).

---

### Idea 1: Step 9G Amendment — Post-Workflow KB Freshness Verification
**Evidence:** nightly-2026-08-07 log explicitly diagnosed: "workflow exits 0 via `continue-on-error:true` despite missing ANTHROPIC_API_KEY / VOYAGE_API_KEY / SUPABASE_ACCESS_TOKEN." Runs #269-#271 show `conclusion: success` but KB log unchanged since 2026-07-23. Step 9G's 30s check sees `conclusion: success` and logs "SUCCESS" — but KB is still 18 days stale. The fix is one additional step: after the 30s wait, re-read `knowledge-base/log.md` and compare `last_run_date` to pre-trigger value.
**Action:** Amend Step 9G in SKILL.md to add a step 5b: after `conclusion: success`, read `knowledge-base/log.md` again. If `last_run_date` has NOT advanced, comment on GH #403 with "success-but-stale" diagnosis: "kb-autopopulate.yml exited 0 but KB log date unchanged — likely missing secrets (ANTHROPIC_API_KEY, VOYAGE_API_KEY, SUPABASE_ACCESS_TOKEN) in GitHub Actions. Run URL: {url}". Direct implementation (same channel as run 101 / Steps 9A-9G).
**Impact:** Closes the 18-day KB staleness loop. Every future silent-success failure becomes a human-visible alert within 90 seconds of the nightly run. Prevents the "workflow green, KB dead" class permanently.
**Category:** operational

---

### Idea 2: Add Detached HEAD Guard to nightly-commit-review SKILL.md
**Evidence:** 2026-08-07 incident: nightly committed on detached HEAD, 3 commits orphaned (`97e1044`, `cbbaae5`, `7dff08b`). 2026-08-08 nightly had to re-discover and re-apply the same fix (30+ min rework). Skill discovery 2026-08-10 provides exact 4-line bash guard with `git symbolic-ref HEAD` check + `git checkout main && git pull origin main` recovery.
**Action:** Add to nightly Pre-Commit section: `BRANCH=$(git symbolic-ref HEAD 2>/dev/null); if [ -z "$BRANCH" ]; then git checkout main && git pull origin main; fi`. Add post-commit verification: `git symbolic-ref HEAD # must output refs/heads/main`. Direct SKILL.md edit.
**Impact:** Prevents orphaned commits. Eliminates the double-rework pattern. Every headless session that lands on detached HEAD auto-recovers.
**Category:** workflow

---

### Idea 3: Create `pr-backlog-triage` Skill
**Evidence:** 10 open PRs. 6 autonomy DRAFTs clogging review queue (oldest 13d). 3 Dependabot ready-to-merge (#629, #630, #631, 7 days old each). Morning digest has flagged PR backlog as Top Priority 2 for multiple days. Skill discovery 2026-08-10 explicitly proposes this skill with step-by-step automation logic.
**Action:** Create `.claude/skills/pr-backlog-triage/SKILL.md`. Steps: (1) list all PRs, (2) classify into merge-ready/superseded/stale-draft/active, (3) auto-merge Dependabot PRs with CI green, (4) close superseded with comment, (5) add `needs-review` label to stale drafts, (6) write summary log.
**Impact:** Unblocks Dependabot security updates. Clears PR queue for human to review #626. Frees review attention. Saves ~20 min per triage. Recurring weekly problem.
**Category:** workflow

---

### Idea 4: Close PR #596 Autonomously (Superseded by #604)
**Evidence:** Morning digest 2026-08-10 explicitly states: "#596 | fastapi requirement bump (Dependabot) | 14d | Superseded by #604 — close this". PR #604 (fastapi <0.136 cap lift) is open and more current. Closing #596 reduces PR count 10→9 and unclutters review surface.
**Action:** Use `mcp__github__update_pull_request` to close #596 with state=closed and a comment explaining supersession by #604.
**Impact:** Immediate noise reduction. XS effort, autonomous executable now. No risk.
**Category:** operational

---

### Idea 5: Add Route-Security-Guard Check to Nightly Step 5 Criteria
**Evidence:** `block_demo_role` guard missed on `billing_usage.py` `POST /buy-usage` — detected by nightly-2026-08-07 but fix orphaned on detached HEAD, requiring 2 nightly cycles. Same guard class has hit 4+ routers historically. Nightly's Step 5 reviews code but has no explicit "new payment endpoints must have block_demo_role" criterion. Skill discovery 2026-08-10 proposes `route-security-guard-audit` skill — but a simpler fix is adding 1 bullet to nightly Step 5.
**Action:** Add to nightly Step 5 (security/code review): "For any new `@router.post` in `billing/`, `billing_usage/`, or `buy-usage`-named routes: verify `block_demo_role` is in `dependencies`. If missing: flag as MEDIUM, fix if <5 LOC, or file GH issue."
**Impact:** Prevents next `block_demo_role` gap from requiring nightly cycles to catch. Catches it on first review.
**Category:** code_health
