# Ideas — 2026-08-18 (Run 107)

## Evidence Summary
- Step 9I: **1st carry-forward** — absent from SKILL.md, not yet autonomous-executable (escalates at run 108)
- KB: 26 days stale (last: 2026-07-23); GH #403 (ANTHROPIC_API_KEY) unresolved 38d+
- Dependabot: 5 open PRs (#629/#630/#631 at 15d, #665/#666 at 1d); morning digest flags as "safe to merge" daily; skill discovery explicitly proposes `dependabot-merge-runner`
- Draft PR accumulation: 5 stale subconscious draft PRs (#575 at 26d, #613 at 18d, #626 at 16d, #648 at 8d, #653 at 6d); skill discovery proposes `stale-autonomy-pr-closer`
- SUPABASE_ACCESS_TOKEN: `last_rotated` still "unknown" after Step 9E added row in run 104; credential alerting blind to unconfigured tokens
- 0 product code commits in past 24h; nightly ran manual block_demo_role sweep, found 100+ pre-existing gaps, did not file bulk issues (pre-existing, not new violations)

---

## Idea 1 — Step 9I Carry-Forward: Nightly Demo-Role Security Sweep

**Category:** code_health / security  
**Source:** run_106_mandate item 1; carry-forward from run 106 winner  
**Evidence:** Step 9I absent from SKILL.md (grep=0). This is the **1st carry**. Per governance precedent, escalates to autonomous-executable at run 108 if still unimplemented.

**Action:** Add Step 9I block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9H:
- Grep `backend/routers/` for files containing POST/PUT/DELETE/PATCH routes
- For each file, check whether `block_demo_role` appears in `Depends(...)`
- If any mutating route lacks it AND no open GH issue exists for that file, file a GH issue with labels `security` + `ai-ready`
- Skip: GET-only routers, `backend/routers/admin/`, files already checked this week (cache by filename in run log)

**Impact:** Closes the entire class of demo-role security gaps going forward. GH #643 and #661 were both caught manually — Step 9I automates this.  
**Status:** PENDING_HUMAN_APPROVAL — escalates to autonomous-executable at run 108

---

## Idea 2 — Add `dependabot-merge-runner` SKILL.md

**Category:** workflow_efficiency / maintenance  
**Source:** Skill discovery 2026-08-17; morning digest consistently flags 5 Dependabot PRs as safe to merge  
**Evidence:**
- 3 Dependabot PRs at 15 days (#629 @playwright/test, #630 vite, #631 @vitejs/plugin-react)
- 2 Dependabot PRs at 1 day (#665 eslint, #666 @typescript-eslint/parser)
- Morning digest action item: "Merge #666, #665, #629, #630, #631 (dependabot, low-risk)"
- Skill discovery flagged this as "strong evidence" with clear implementation path
- Pattern of manual flagging without automated resolution = systematic inefficiency

**Action:** Create `.claude/skills/dependabot-merge-runner/SKILL.md` that:
1. Lists open Dependabot PRs by age
2. Classifies each as auto-safe (dev deps, patch/minor with passing CI) vs. needs-review (major, runtime deps)
3. Merges auto-safe PRs via `mcp__github__merge_pull_request`
4. Files nightly summary comment on any PR deferred to human review
5. Runs in nightly-commit-review Phase 7 (after security sweep, before commit)

**Impact:** Closes 5 PRs immediately (~15 min human time saved per week); prevents Dependabot PR debt from compounding; security deps merged faster.  
**Status:** NEW — PENDING_HUMAN_APPROVAL

---

## Idea 3 — Add `stale-autonomy-pr-closer` SKILL.md

**Category:** workflow_efficiency / housekeeping  
**Source:** Skill discovery 2026-08-17; 5 stale subconscious draft PRs visible in morning digest  
**Evidence:**
- PR #575 (DRAFT, 26d), #613 (DRAFT, 18d), #626 (DRAFT, 16d), #648 (DRAFT, 8d), #653 (DRAFT, 6d)
- Reviewer cognitive load from accumulating stale drafts
- Skill discovery explicitly proposed this with "superseded" detection logic

**Action:** Create `.claude/skills/stale-autonomy-pr-closer/SKILL.md` that:
1. Lists all draft PRs with age
2. Identifies clearly superseded ones (commits on branch already merged to main via other PRs)
3. Posts a closing comment explaining why it's superseded
4. Closes the PR

**Impact:** Reduces open draft PR count from 5+ to clean state. Low risk if scoped to clearly-superseded drafts only.  
**Caveat:** Risk of closing a PR the user intended to keep → mitigate with dry-run mode and 30-day minimum age threshold.  
**Status:** NEW — PENDING_HUMAN_APPROVAL

---

## Idea 4 — Extend Step 9E: Alert on Credentials with `unknown` last_rotated

**Category:** operational / security  
**Source:** SUPABASE_ACCESS_TOKEN gap; run 104 added row but last_rotated still "unknown" after 4 runs  
**Evidence:**
- `ops/credential-rotation-schedule.md`: SUPABASE_ACCESS_TOKEN row shows `last_rotated: unknown — not yet set in environment`
- Step 9E (already in SKILL.md) fires credential rotation alerts — but only for credentials with known last_rotated dates
- Credentials with `unknown` last_rotated are invisible to alerting; effectively unconfigured

**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9E block to:
- After parsing credential rows, check for any with `last_rotated: unknown` or empty
- If found: file a GH issue with label `ops-reminder` titled `[ops] credential last_rotated unknown: {name} — fill in rotation date to enable alerts`
- One issue per credential, dedup by checking for existing open issue with same title prefix

**Impact:** SUPABASE_ACCESS_TOKEN now surfaces as an actionable GH issue instead of silently missing rotation alerts. Generalizes to any future credential added without a rotation date.  
**Channel:** SKILL.md edit → proven autonomous-executable channel  
**Status:** AUTONOMOUS-EXECUTABLE (SKILL.md edit, same channel as 9C/9E/9F/9G/9H)

---

## Idea 5 — Post Targeted GH Comment on #403 with Exact ANTHROPIC_API_KEY Steps

**Category:** operational / unblocking  
**Source:** Bonus action from run 106; morning digest priority #1; KB 26 days stale  
**Evidence:**
- GH #403 open 38+ days; every nightly log and morning digest restates the setup steps
- KB autopopulate blocked on this single credential
- FTS fallback active — retrieval degraded, no new articles ingested since 2026-07-23
- Nightly-2026-08-18 reiterated exact steps again in its log but unclear if a direct GH comment was posted

**Action:** Post comment on GH #403 with:
- Exact Railway path: Railway → agentnexlify backend service → Variables tab → ANTHROPIC_API_KEY
- Exact GitHub path: repo Settings → Secrets and variables → Actions → New repository secret → Name: ANTHROPIC_API_KEY
- Estimated time: 5 minutes
- What it unblocks: KB autopopulate (blocked 26d), autopilot loop

**Impact:** Single comment that the user sees next time they check GitHub. Unblocks KB freshness and autopilot loop in ~5 min of user action.  
**Status:** AUTONOMOUS-EXECUTABLE (one-time GH comment, same channel as prior bonus actions)
