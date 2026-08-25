# Ideas — Run 2026-08-24 (Run 109)

## Evidence Digest

**Context (2026-08-24):**
- 0 production commits in last 24h (repo quiet since 2026-08-22 nightly log)
- 2 nightly logs this period (2026-08-22, 2026-08-24) — both clean with no bugs found
- Step 9J ABSENT from nightly SKILL.md (0 grep hits) — 1st carry-forward mandate fires
- GH #399: AUTOPILOT_GH_TOKEN expired, Day 41+, 30 ai-ready issues blocked
- GH #403: ANTHROPIC_API_KEY + SUPABASE_URL missing in GH Actions, KB 29d+ stale
- GH #669: 97/97 routers missing block_demo_role (filed 2026-08-20, awaiting fix)
- Dependabot PRs: 6 aging (#629/#630/#631/#649/#665/#666), flagged in 4 morning digests
- Step 9K (stale autonomy PR closer) named in run_109_mandate as candidate

---

### Idea 1: Step 9J — Dependabot Auto-Merge in nightly SKILL.md (autonomous-executable, 1st carry-forward)

**Evidence:** run_108_mandate explicitly named Step 9J. Morning digests 2026-08-11/12/17/18 flagged same 4-6 Dependabot PRs as safe to merge with zero action. Skill discovery 2026-08-17 proposed `dependabot-merge-runner`. Step 9I first execution filed GH #669 (97/97 violations) — nightly sweep channel proven. 6 PRs aging: #629/#630/#631/#649/#665/#666. 1st carry-forward triggers autonomous-executable escalation per governance precedent (runs 99/101/105/107).

**Action:** Add Step 9J block to .claude/skills/nightly-commit-review/SKILL.md after Step 9I. Block lists open Dependabot PRs, checks CI (mergeable_state=clean) + no review requests + no blocking labels, merges eligible via squash, logs count. **IMPLEMENT DIRECTLY THIS RUN.**

**Impact:** Security dep bumps applied within 24h of CI green, indefinitely. Estimated 15 min/week manual overhead eliminated. CVE exposure window shrinks from 2-3 weeks to <24h.

**Category:** operational

---

### Idea 2: Step 9K — Stale Autonomy PR Closer in nightly SKILL.md

**Evidence:** run_109_mandate named Step 9K as candidate "if subconscious PR count still ≥3". nightly-2026-08-22 lists GH #669 still open (filed 2026-08-20). 5 subconscious draft PRs were open as of run 102 (#575, #606, #611, #613, #626). Each idle draft PR wastes contributor attention and clutters the PR list. PR dedup guard (added run 99) prevents new duplicates but doesn't close existing idle ones.

**Action:** Add Step 9K block to SKILL.md: list open PRs with head branch starting `subconscious/`, check if >14d old AND no commits in last 7d AND no review activity, close stale ones with comment "Superseded by active subconscious run — closing stale draft."

**Impact:** Clean PR list, reduces reviewer confusion, eliminates accumulated draft debt. Structural: runs forever once added.

**Category:** operational

---

### Idea 3: Middleware-Level block_demo_role FastAPI Guard (addresses GH #669 root cause)

**Evidence:** GH #669 (filed 2026-08-20): 97/97 routers missing block_demo_role — Step 9I found ALL non-admin mutating endpoints are unguarded. GH #643 (appointment_briefs.py) and GH #661 (scoring_config.py) were one-off fixes for the same class problem, but the root cause is no middleware guard. A FastAPI middleware approach would retroactively protect all existing and future endpoints without per-router edits.

**Action:** Create GH issue proposing FastAPI middleware (or dependency injection at app-level in main.py) that calls block_demo_role logic once for all mutating routes, eliminating need for per-router Depends() calls. File as M-effort, human-approval required, include implementation sketch.

**Impact:** Closes all 97 violations at once. Prevents regression as new routers are added. Eliminates 97-issue GH backlog.

**Category:** code_health

---

### Idea 4: Add SUPABASE_URL + SUPABASE_ANON_KEY Diagnostic to GH #403 Comment

**Evidence:** nightly-2026-08-22 confirms GH #403 still open, KB 29d stale. Run 107 posted ANTHROPIC_API_KEY setup steps. Run 108 bonus posted all three secrets. KB still stale 4 days after run 108 comment. If ANTHROPIC_API_KEY was added but the workflow still fails, SUPABASE_URL or SUPABASE_ANON_KEY may be the second blocker.

**Action:** Add targeted follow-up comment on GH #403 asking human to confirm GH Actions run URL from kb-autopopulate.yml so we can diagnose which specific secret is missing from the failure message.

**Impact:** Unblocks KB autopopulate (29d stale). KB feeds AI chat system — dark KB = stale AI answers.

**Category:** operational

---

### Idea 5: Step 9K as Nightly Autonomy PR Check (variant — report-only, no auto-close)

**Evidence:** Same as Idea 2, but a lighter version: instead of auto-closing stale PRs, Step 9K reports the count and lists branch names. Auto-close risks closing a PR the human intended to keep (even if draft). Report-only is safer, less likely to be blocked by governance uncertainty.

**Action:** Add Step 9K block that lists open `subconscious/` PRs older than 14d, logs count and names, posts comment on oldest if > 21d stale. No auto-close.

**Impact:** Human visibility into PR debt. Prompts action without risk of premature close.

**Category:** operational
