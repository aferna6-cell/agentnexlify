# Ideas — Run 111 (2026-08-29)

## Evidence Digest

- **Step 9J 0% effective:** nightly-2026-08-29 confirms 20+ Dependabot PRs in `mergeable_state: unknown`, 0 merged. Run 110 winning-concept.md has exact 10-15 line fix (add `@dependabot rebase` trigger). 1st carry-forward mandate fires → autonomous-executable.
- **Loop stalled Day 56+:** GH #399 (AUTOPILOT_GH_TOKEN expired). 3 ai-ready issues stalled (#643 22d, #660 14d, #669 9d). All block_demo_role class fixes blocked.
- **Brain connector 37d stale:** GH #684 open, SUPABASE_ACCESS_TOKEN not set in Railway. Step 9C fires WARNING every nightly.
- **KB healthy:** last run 2026-08-26 (3 days, under 7-day threshold) — Step 9F PASS.
- **No production code commits in 3 days:** all commits are ops/subconscious/kb state.
- **Competitive pressure:** KB articles compiled 2026-08-26 — vertical AI agents eating horizontal SaaS, GoHighLevel agency plan, churn benchmarks. Product momentum blocked by stalled loop.

---

### Idea 1: Fix Step 9J — Add `@dependabot rebase` trigger for `mergeable_state: unknown` PRs
**Evidence:** nightly-2026-08-29 Step 9J: "0 merged (all in unknown/stale state, no rebase trigger in current SKILL.md)". Run 110 winning-concept.md: exact implementation sketch. 20+ Dependabot PRs aging (oldest: #594, #595). CVE window: 2-3 weeks. 1st carry-forward autonomous-executable mandate fires this run.
**Action:** Edit Step 9J block in `.claude/skills/nightly-commit-review/SKILL.md`: after `mergeable_state != "clean" → skip`, add branch: if state == "unknown", check last 48h comments for existing `@dependabot rebase`, if absent post it, cap at 5 rebase triggers per run, log count.
**Impact:** Step 9J goes from 0% → ~80% effective within 24-48h of next nightly. 20+ security dep bumps unblocked. CVE window 2-3 weeks → <48h.
**Category:** workflow

---

### Idea 2: Add Step 9K — Stale Subconscious Draft PR report to nightly
**Evidence:** Run 109 mandate explicitly named Step 9K as a candidate. 3+ subconscious draft PRs aging in repo (governance tracking shows 5 open draft PRs as of run 102, no merge/close since). Nightly already tracks ai-ready issues in Step 9D — same pattern for PR staleness.
**Action:** Add Step 9K block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9J. List open PRs with head branches starting `subconscious/`. Flag any with `draft: true` and `updated_at > 14d`. Log count. If any >30d, post comment on PR and on the relevant governance run artifact.
**Impact:** Prevents PR queue from growing silently. Owner gets weekly actionable list. Prevents run 102's "5 draft PRs" pattern from recurring.
**Category:** workflow

---

### Idea 3: Escalate AUTOPILOT_GH_TOKEN (GH #399) with exact Railway remediation steps
**Evidence:** GH #399 open 56 days. 3 ai-ready security issues stalled (block_demo_role class). Loop health endpoint `/api/admin/loop-health` exists (PR #463). nightly-2026-08-29 Step 9D: "Loop likely stalled. UNKNOWN/STALLED." Prior escalation comments: 4+ over 56 days, zero human action.
**Action:** Post targeted comment on GH #399 with: (1) current stall consequence summary (3 issues, 56 days, CVE window 2-3 weeks), (2) exact Railway dashboard path to find AUTOPILOT_GH_TOKEN, (3) GitHub fine-grained PAT scopes required, (4) 2-minute remediation checklist. Reference concrete revenue impact (security issues shipped → trust).
**Impact:** Reduces human friction for the one action that unblocks 3 security fixes + future autonomy pipeline.
**Category:** operational

---

### Idea 4: Add Step 9D loop-health API diagnostic to nightly
**Evidence:** nightly-2026-08-29 Step 9D: "Loop health: GH Actions workflow status unavailable in this headless env. Loop status: UNKNOWN/STALLED." `/api/admin/loop-health` endpoint exists (PR #463, live since 2026-07-18). Currently unused by nightly. 5 vitals: ai_ready_count, oldest_issue_days, loop_status, last_run_at, consecutive_failures.
**Action:** Edit Step 9D in `.claude/skills/nightly-commit-review/SKILL.md`: add bash block to curl `/api/admin/loop-health` (Railway URL from env), parse JSON, log all 5 vitals. If loop_status != "running": surface exact diagnosis (vs "UNKNOWN") and post on GH #399.
**Impact:** Replaces "UNKNOWN/STALLED" with actionable diagnosis. Human can see *why* stalled (token expiry, infra failure, quota) without manual investigation.
**Category:** workflow_efficiency

---

### Idea 5: File escalation comment on GH #684 brain connector with exact Railway + GitHub Actions fix path
**Evidence:** Step 9C fire nightly-2026-08-29: "37 days stale (>14 day threshold)". GH #684 "Brain connector 33 days stale" open since 2026-08-25 (4 days). Prior run 107 bonus comment posted on GH #403 with ANTHROPIC_API_KEY path. KB now healthy (last 2026-08-26 — GH #403 ANTHROPIC_API_KEY resolved). Brain connector failure is SUPABASE_ACCESS_TOKEN specifically, different secret, different issue.
**Action:** Post comment on GH #684 with: (1) current state (37d stale, 23+ days since warning), (2) exact Railway Variables name: `SUPABASE_ACCESS_TOKEN`, (3) where to get the token (Supabase dashboard → Settings → Access Tokens), (4) which services depend on it (brain connector, Supabase MCP, Step 9E).
**Impact:** Concretely unblocks brain connector; reduces AI context degradation. SUPABASE_ACCESS_TOKEN is different from ANTHROPIC_API_KEY (which fixed KB) — this is the remaining blocker.
**Category:** operational
