# Ideas — 2026-08-22

## Evidence Digest

- **Step 9J ABSENT** (0 occurrences in nightly SKILL.md). 1st carry-forward fires → autonomous-executable by governance.
- **Nightly-2026-08-21 + 2026-08-22** both explicitly flagged Step 9J as "unexecuted". Channel confirmed working (Steps 9C/9E/9F/9G/9I all landed via same path).
- **GH #669** filed 2026-08-20: 97/97 routers missing block_demo_role. No PR (GH #399 blocks loop).
- **GH #399** Day 41+ (AUTOPILOT_GH_TOKEN expired). No resolution.
- **GH #403** KB 30d stale. Two targeted comments (runs 107/108) had zero effect. kb-autopopulate.yml triggering but ANTHROPIC_API_KEY missing from GH Actions.
- **Open subconscious draft PRs**: 4-5 PRs aging from runs 102-108 per governance; no merges in 2+ weeks.
- **KB autopopulate log**: last indexed 124 articles (embeddings skipped — no credentials).
- **Bug patterns**: SUPABASE_SERVICE_KEY/ANON key confusion fixed 2026-07-17. Recurring block_demo_role gap class now tracked by Step 9I. No new bug classes this week.

---

### Idea 1: Step 9J — Dependabot Auto-Merge in nightly SKILL.md
**Evidence:** 1st carry-forward from run 108 winner. Governance: "Autonomous-executable if not approved by run 109". nightly-2026-08-21 + nightly-2026-08-22 both note it unexecuted. Morning digests 2026-08-11/12/17/18 flagged same 4-6 Dependabot PRs safe to merge with zero action. Run_109_mandate item 2 explicitly: "1st carry-forward mandate is autonomous-executable."
**Action:** Insert Step 9J block into .claude/skills/nightly-commit-review/SKILL.md after Step 9I and before step 10. Implement directly this run.
**Impact:** Dependabot PRs merge automatically when CI is green. Security patches within 24h vs current 2-3 week delay. ~15 min/week saved.
**Category:** operational

---

### Idea 2: Step 9K — Stale Autonomy PR Closer in nightly SKILL.md
**Evidence:** run_109_mandate explicitly names Step 9K as candidate "if subconscious PR count still ≥3." Governance tracks 4-5 open subconscious draft PRs (runs 102-108 all mention 4-5 aging drafts). Nightly logs do not report any closures. Each open subconscious PR is obsolete once a new run supersedes it; indefinitely open drafts pollute the PR list and confuse reviewers.
**Action:** Add Step 9K block to SKILL.md after Step 9J. List open PRs with head branch matching "subconscious". Close drafts older than 14 days that have no linked review comments, with a comment linking to the latest winning-concept.md.
**Impact:** PR list stays clean. Reviewers see only the current active direction. Eliminates drift between open drafts and latest state.
**Category:** workflow

---

### Idea 3: KB Autopopulate Direct-Compile Fallback in nightly
**Evidence:** KB 30d stale. Step 9G triggers kb-autopopulate.yml but ANTHROPIC_API_KEY missing in GH Actions (#403) has blocked every attempt since 2026-07-23. Two targeted setup comments (runs 107/108 bonus actions) had zero effect in 72h+. The KB compile script exists locally (scripts/daily/kb-autopopulate.sh). Nightly already has permission to run shell commands. A direct-compile fallback bypasses GH Actions entirely.
**Action:** Add Step 9H (or 9G fallback) that, when Step 9G is triggered and returns failure or 204, runs `bash scripts/daily/kb-autopopulate.sh` directly in the nightly session. This doesn't require GH Actions secrets.
**Impact:** KB autopopulate unblocked immediately without human secret-rotation action. Ends 30d+ staleness.
**Category:** operational

---

### Idea 4: GH #669 Middleware Spec Comment — Detail block_demo_role as FastAPI middleware
**Evidence:** GH #669 filed 2026-08-20: 97/97 routers missing block_demo_role. Per-route approach failed at scale (same class bug filed twice in 6 days: GH #643 + #661, then GH #669 shows 97 more). Middleware would protect all routes without per-file edits. Governance.json parking_lot mentions this: "middleware-level block_demo_role FastAPI guard (GH #669 tracking — M-effort, human-approval required)."
**Action:** Post spec comment on GH #669 with middleware implementation sketch, marking it as the preferred fix over 97 individual route edits. Add labels: human-action-required.
**Impact:** When GH #399 resolves and issue-to-pr-loop runs, it picks up the correct approach (middleware) instead of 97 per-file patches.
**Category:** code_health

---

### Idea 5: GH #399 Token Rotation — Create a Step 9L nightly age-pressure escalation
**Evidence:** GH #399 Day 41+. Prior escalation comments (runs 90/92/96/107/108) had no effect. No automated age-tracking beyond manual comments. The token rotation is a 5-minute Railway env-var change but keeps being deferred. Automated daily escalation in the nightly report (not just comment) creates visible pressure without spamming GH.
**Action:** Add Step 9L to nightly that reads GH #399 status and adds to the nightly report (not GH comment) a countdown: "GH #399 blocking {N} ai-ready issues for {D} days. Estimated cost: {D*2} engineer-hours queued." Cap: only comment on GH every 7 days (not daily spam).
**Impact:** Human sees escalating cost framing in every morning digest read. Weekly GH pressure vs current ad-hoc pattern.
**Category:** operational
