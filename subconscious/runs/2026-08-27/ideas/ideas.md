# Candidate Ideas — Run 114 (2026-08-27)

## Evidence Digest

- **Step 9J fired but merged 0 PRs** — nightly-2026-08-27 ran Step 9J for the first time. 3 PRs checked (#679, #666, #629), all returned `mergeable_state: unknown`. Block requires `"clean"` — no merges. 19+ Dependabot PRs now aging (oldest from 2026-07-27). Root cause: GitHub returns `unknown` for stale-base PRs until mergeability is recomputed.
- **KB is healthy** — last run 2026-08-26 (1 day ago). GH #403 appears resolved.
- **Brain connector 35 days stale** — GH #684 open. Human action needed (rotate GitHub PAT + set SUPABASE_ACCESS_TOKEN in Railway).
- **3 ai-ready issues, 0 linked PRs** — #643 (20d), #660 (12d), #669 (7d). All security (block_demo_role). GH #399 blocking autopilot loop.
- **agent_escalation.py shipped but unwired** — 88 LOC + 128 tests committed (20079db) but 0 router callers. Nightly classified "LOW-MEDIUM — not yet wired."
- **Step 9K mandate condition** — run_109_mandate named Step 9K if ≥3 subconscious PRs open.

---

### Idea 1: Fix Step 9J — Handle `mergeable_state: unknown` in Dependabot Auto-Merge
**Evidence:** nightly-2026-08-27 Step 9J ran for first time: 3 PRs checked, 0 merged — all returned `mergeable_state: unknown`. 19+ Dependabot PRs aging (oldest 2026-07-27). `unknown` is documented GitHub behavior when mergeability hasn't been computed yet for stale-base PRs. Block currently requires `"clean"` and skips all others.
**Action:** Edit Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md`: when `mergeable_state == "unknown"`, call `mcp__github__update_pull_request_branch` to trigger recompute, re-read state; if still unknown, attempt merge via `mcp__github__merge_pull_request` and handle 405/422 errors gracefully. Log outcome.
**Impact:** 19+ PRs will start merging. CVE exposure window <24h. ~15 min/week manual overhead eliminated permanently.
**Category:** operational

---

### Idea 2: Step 9K — Stale Autonomy PR Closer (Report-Only)
**Evidence:** run_109_mandate named Step 9K with condition ≥3 subconscious PRs open. 5 subconscious draft PRs were open in run 102 (#575, #606, #611, #613, #626). PR dedup guard (added run 99) prevents new duplicates but existing idle drafts persist. No current count available without GitHub query.
**Action:** Add Step 9K block to SKILL.md after Step 9J: list open PRs with head branch containing `subconscious/`, age >14d, no commits last 7d. Log count. Post comment on oldest if >21d: "No activity for 21+ days — consider merging or closing."
**Impact:** Visibility into PR debt. Prompts human action on stale drafts.
**Category:** operational

---

### Idea 3: File GH Issue to Wire agent_escalation.py
**Evidence:** 20079db (nightly classified LOW-MEDIUM) shipped `backend/services/agent_escalation.py` (88 LOC) + 128-line test file with 0 router callers. Pattern: appointment_completion.py was similarly unwired for 3+ weeks before nightly couldn't auto-implement it. Services with tests but no callers = dead code risk.
**Action:** File GH issue (labels: `backend`, `ai-ready`) titled "Wire agent_escalation.py — service shipped with 128 tests but 0 router callers. Add endpoint or delete if intentionally deferred." Include `check_escalation` function signature from lines 51+.
**Impact:** Prevents dead code accumulation. Keeps production coverage honest.
**Category:** code_health

---

### Idea 4: Step 9D Enhancement — Escalate ai-ready Issues Stalled >14d
**Evidence:** Step 9D in nightly-2026-08-27 found 3 ai-ready issues with 0 linked PRs and loop health unknown. #643 is 20 days old with no linked PR. GH #399 is root blocker but no automated signal fires per-issue.
**Action:** Enhance Step 9D in SKILL.md: for each ai-ready issue >14d old with no linked PR and no recent (7d) comment from the loop, post comment: "Loop appears stalled — no linked PR after {N} days. Is AUTOPILOT_GH_TOKEN rotated (GH #399)?" Dedup: if same comment text already in last 3 comments, skip.
**Impact:** Automated pressure on the loop blockage. Reduces silent staleness.
**Category:** workflow

---

### Idea 5: Add Dead Service Detector Check to Nightly (Step 9L)
**Evidence:** agent_escalation.py is the second service file shipped with tests but 0 router callers (previous: appointment_completion.py). A nightly grep for `backend/services/*.py` files with 0 import references in `backend/routers/**/*.py` would catch this class of gap systematically.
**Action:** Add Step 9L block to SKILL.md: grep `backend/services/` for `.py` files not imported in `backend/routers/` or `backend/main.py`. Exclude `automation/scheduled/` (cron-triggered), `__init__.py`, `*_test.py`, files containing "helper", "utils", "base". If found: check for existing open issue, file new one with labels `backend` + `ai-ready` if none.
**Impact:** Systematic prevention of dead service accumulation. Catches the pattern before it becomes a 3-week delay.
**Category:** code_health
