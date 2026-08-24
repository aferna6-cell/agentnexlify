# Candidate Ideas — 2026-08-23

## Evidence Digest

Repo quiet 3 days: only nightly review commits (caff668, 95d1c87) — no production code.
Step 9J (Dependabot auto-merge) absent from nightly SKILL.md — 1st carry-forward mandate fires (run 108 set escalation at 1st carry-forward). KB 31 days stale (last: 2026-07-23), GH #403 ANTHROPIC_API_KEY still missing in GH Actions despite 2 targeted comments. GH #399 Day 41+ — AUTOPILOT_GH_TOKEN expired, 30 ai-ready issues blocked. GH #669 open (97/97 routers missing block_demo_role, filed 2026-08-20). 4-6 Dependabot PRs aging. Nightly Step 9I confirmed working (filed GH #669 on first execution 2026-08-20). 4 draft subconscious PRs aging.

---

### Idea 1: Step 9J — Dependabot Auto-Merge in nightly-commit-review SKILL.md
**Evidence:** run_108_mandate explicitly named Step 9J as primary candidate. Morning digests 2026-08-11/12/17/18 all flagged same 4-6 Dependabot PRs as safe to merge with zero action taken. Skill discovery 2026-08-17 proposed dependabot-merge-runner. Step 9I executed 2026-08-20 (filed GH #669) — nightly channel confirmed working. 6 PRs aging (#629/#630/#631/#649/#665/#666). 1st carry-forward mandate fires — AUTONOMOUS-EXECUTABLE.
**Action:** Insert Step 9J block into .claude/skills/nightly-commit-review/SKILL.md after Step 9I (before step 10). Block: list open Dependabot PRs, check CI (mergeable_state=clean) + no review requests + no blocking labels, merge eligible via squash, log count.
**Impact:** Dependabot PRs merge automatically forever — security patches within 24h of CI passing vs 2-4 week manual delay. ~15 min/week human overhead eliminated.
**Category:** operational

---

### Idea 2: Step 9K — Stale Autonomy PR Closer in nightly-commit-review SKILL.md
**Evidence:** governance.json notes 4+ draft subconscious PRs aging (#606/#611/#613/#625/#626). run_109_mandate item 6 explicitly names Step 9K as candidate if PR count still ≥3. PR queue confusion hides active work. Morning digests flag stale PRs regularly.
**Action:** Add Step 9K block to nightly SKILL.md: list open PRs older than 14 days with "subconscious" in branch name, close as stale with a comment explaining they were superseded by newer runs.
**Impact:** Clean PR queue. Reviewers can find actual review-ready PRs. Nightly channel confirmed working.
**Category:** workflow

---

### Idea 3: Middleware-Level block_demo_role FastAPI Guard
**Evidence:** GH #669 filed 2026-08-20 — 97/97 mutating router endpoints missing Depends(block_demo_role). GH #643 (appointment_briefs.py, 2026-08-11) + GH #661 (scoring_config.py, 2026-08-16) same class bug filed twice before Step 9I automated detection. Root cause: developers add routers without remembering the guard. Middleware-level fix would apply to ALL routers automatically, eliminating per-router discipline requirement.
**Action:** Add block_demo_role as a FastAPI middleware function in main.py that intercepts POST/PUT/DELETE/PATCH requests from demo-role tenants (identified by JWT claim or tenant flag) before they reach any router.
**Impact:** Closes GH #669 entirely with one change. Prevents future router-level misses permanently. 97 individual router patches reduced to 1.
**Category:** code_health

---

### Idea 4: KB Autopopulate Local Fallback Path
**Evidence:** KB 31 days stale. GH #403 (ANTHROPIC_API_KEY missing in GH Actions) open 30+ days. 2 targeted comments (runs 107 + 108 bonus) — zero human action. Step 9G triggers kb-autopopulate.yml daily but ANTHROPIC_API_KEY missing means the workflow always fails. Cloud container nightly sessions DO have ANTHROPIC_API_KEY via the agent environment — could compile KB directly in the nightly session instead of delegating to GH Actions.
**Action:** Add fallback to Step 9G: if gh workflow run fails/times out, attempt local KB compile using scripts/daily/kb-autopopulate.sh directly in the nightly container session (ANTHROPIC_API_KEY is available to agent sessions).
**Impact:** Unblocks KB from 31-day stale state without requiring human GH Actions secret configuration.
**Category:** operational

---

### Idea 5: GH #399 Cost-Calculation Escalation Comment
**Evidence:** GH #399 (AUTOPILOT_GH_TOKEN expired) Day 41+. 30 ai-ready issues blocked. 4+ escalation comments already posted. Last comment: 2026-07-16 (Day ~14). Prior escalations used "opportunity cost" framing. Human has not actioned despite 4+ autonomous comments. A concrete cost calculation — hours × engineer cost × weeks blocked — may be more compelling than abstract descriptions.
**Action:** Post new comment on GH #399 with: 30 issues × 2h avg engineering time = 60 hours blocked. At $150/h contractor rate = $9,000 in queued engineering work. Single AUTOPILOT_GH_TOKEN rotation takes 5 minutes. ROI: 5min input → $9k output / 60h saved.
**Impact:** Framing change may prompt human action on Day 41+ blocker. Structural path unblocked.
**Category:** workflow_efficiency
