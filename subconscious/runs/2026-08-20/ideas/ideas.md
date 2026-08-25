# Ideas — Run 2026-08-20

## Evidence Digest

Step 9I first execution (nightly-2026-08-20): found 97 of 97 checked routers missing
`Depends(block_demo_role)` on mutating endpoints. Filed GH #669 as consolidated tracking
issue. Nightly explicitly recommended middleware-level fix over 95 individual patches.

Run 108 mandate status:
- Step 9I in SKILL.md: PASS (run 107)
- First nightly with Step 9I: PASS → GH #669 filed (97 violations, class-wide)
- GH #403 ANTHROPIC_API_KEY: still blocking KB autopopulate (28d stale, no human action)
- GH #399 AUTOPILOT_GH_TOKEN: Day 40+, 30 ai-ready issues blocked, still open
- Dependabot PRs: 6 aging (#629/#630/#631/#649/#665/#666) → Step 9J named as run 108 candidate

---

### Idea 1: Step 9J — Add Dependabot auto-merge to nightly-commit-review SKILL.md
**Evidence:** Skill discovery 2026-08-17 explicitly proposed `dependabot-merge-runner` with
4+ weeks of evidence (morning digests 2026-08-11/12/17/18 all flag same 4–6 Dependabot PRs
as "safe to merge" with zero action taken). Run 108 mandate named Step 9J as candidate.
6 PRs currently aging: #629/#630/#631/#649/#665/#666.
**Action:** Add Step 9J bash block to nightly-commit-review SKILL.md: list Dependabot PRs
via `mcp__github__list_pull_requests`, check CI status per PR, merge CI-green ones via
`mcp__github__merge_pull_request` (squash), log count. Skip PRs with failing checks or
review requests. Write summary line "Step 9J: {N} Dependabot PRs merged, {M} skipped."
**Impact:** Security patches applied weekly without human intervention. Each delay = wider
exposure window on known CVEs. Estimated 15 min/week saved. Compounds every merge cycle.
**Category:** operational

---

### Idea 2: Middleware-level `block_demo_role` FastAPI guard
**Evidence:** GH #669 (filed by Step 9I, 2026-08-20) — 97 of 97 checked routers missing
the guard. The nightly itself recommended: "middleware-level batch fix over per-file patching."
GH #643 + GH #661 were per-file patches that didn't prevent recurrence. Class-wide problem
confirmed by first Step 9I execution.
**Action:** Add FastAPI middleware to `backend/main.py` that intercepts POST/PUT/DELETE/PATCH
requests and applies `block_demo_role` check unless path matches an explicit allowlist
(auth/*, webhooks/*, widget/*). Remove per-file `Depends(block_demo_role)` from existing
files or leave as belt-and-suspenders. Add test in `backend/tests/test_demo_role_middleware.py`.
**Impact:** Closes GH #669 permanently. Every future router added gets the guard automatically.
No more Step 9I issues filed for new routers. One 30-line PR fixes 97 router files at once.
**Category:** code_health

---

### Idea 3: GH #399 Day-40 cost-of-delay escalation comment
**Evidence:** GH #399 (AUTOPILOT_GH_TOKEN expired) has been open 40+ days. 30 ai-ready
issues queued. Previous escalations: runs 96/97/98 posted comments with no result.
Opportunity cost: 40 days × 30 issues × ~2h each = 1,200 engineering-hours blocked.
**Action:** Post comment on GH #399 with Day-40 milestone framing + opportunity-cost
calculation + 3-step rotation instructions (Railway → token rotation → update env var).
**Impact:** If human rotates the token, 30 ai-ready issues start flowing through
issue-to-pr-loop. High potential leverage, low reliability (previous 4 escalations
produced no action).
**Category:** operational

---

### Idea 4: Step 9K — Stale autonomy PR closer in nightly
**Evidence:** Skill discovery 2026-08-17 proposed `stale-autonomy-pr-closer`. Ongoing
governance notes: #625/#626/#613/#611/#606 (5 draft PRs aging 10–19 days). Morning digests
consistently list them as "needs action." Pattern: subconscious PRs accumulate, never get
merged or closed by human.
**Action:** Add Step 9K block to nightly SKILL.md: list draft PRs by Claude/subconscious
authors 10+ days old. For clearly superseded ones (newer PR touches same files or same
skill), close with comment "Superseded by #N." For valid-but-stale: add `needs-human-review`
label. Never auto-merge draft PRs.
**Impact:** PR debt eliminated continuously. Reviewers see a clean queue. Prevents
governance.json "PR pile-up" notes from compounding indefinitely.
**Category:** workflow

---

### Idea 5: Targeted comment on GH #403 with SUPABASE_URL setup diagnostics
**Evidence:** KB 28 days stale. GH #403 has ANTHROPIC_API_KEY as the known blocker.
Run 107 posted 5-step ANTHROPIC_API_KEY setup instructions. KB still stale 24h later.
Possibility: ANTHROPIC_API_KEY was added but there's a second blocker (SUPABASE_URL
or SUPABASE_KEY missing from GH Actions). kb-autopopulate.yml needs both.
**Action:** Check kb-autopopulate.yml for all required env vars. Post follow-up comment
on GH #403 listing EVERY secret the workflow needs (ANTHROPIC_API_KEY + SUPABASE_URL +
SUPABASE_ANON_KEY or SERVICE_KEY) with exact setup steps for each.
**Impact:** KB autopopulate resumes → AI chat system gets fresh knowledge → customer
experience improves. Diagnoses whether additional secrets are blocking.
**Category:** operational
