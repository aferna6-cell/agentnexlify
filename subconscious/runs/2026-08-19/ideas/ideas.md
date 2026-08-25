# Candidate Ideas — 2026-08-19

## Evidence Digest
- Zero product code commits in 48h (last 2 nightlies: ops logs only)
- Step 9I ABSENT from SKILL.md (1st carry-forward, run 106 winner)
- Nightly-2026-08-18 ran the block_demo_role sweep manually via route-security-guard-audit; found 100+ routers with gap — confirms class problem is systemic, not just 2 GH issues
- 6 Dependabot PRs aging 1-15d, morning digest calls them safe-to-merge daily, zero automated action (skill-discovery 2026-08-17 proposes dependabot-merge-runner)
- KB 27 days stale (ANTHROPIC_API_KEY missing from GH Actions, #403 day 38+)
- GH #399 AUTOPILOT_GH_TOKEN expired (day 39+, 30 ai-ready issues blocked)
- SUPABASE_ACCESS_TOKEN last_rotated still "unknown" (human has not filled in)
- GH #661 (scoring_config.py block_demo_role) open, PR #660 ai-ready but not merged
- 8 open PRs (4 dependabot, 4 autonomy drafts) — PR pile-up growing

---

### Idea 1: Step 9I — Add nightly demo-role security sweep to nightly-commit-review SKILL.md (carry-forward, direct implementation)
**Evidence:** Step 9I ABSENT (1st carry-forward). nightly-2026-08-18 manually ran route-security-guard-audit and found 100+ routers missing block_demo_role — confirmed systemic gap. GH #643 (appointment_briefs.py, 2026-08-11) + GH #661 (scoring_config.py, 2026-08-16) = same class bug twice in 6 days. Autonomous-executable precedent: Steps 9C/9E/9F/9G all implemented by same SKILL.md-edit channel. Governance escalation at run 108 if still absent — direct implementation now skips a wasted cycle.
**Action:** Edit .claude/skills/nightly-commit-review/SKILL.md to add Step 9I block after Step 9H. Grep backend/routers/ for POST/PUT/DELETE/PATCH endpoints missing Depends(block_demo_role). Skip GET-only, admin/, auth, webhooks, widget routes. If new violation found (not already in open GH issue): file GH issue with labels security + ai-ready.
**Impact:** Catches new block_demo_role gaps within 24h of introduction. Closes class of recurring security bugs. Prevents the appointment_briefs.py pattern from repeating on future routers.
**Category:** code_health
**Effort:** S (SKILL.md edit, ~50 lines bash block)
**Status:** AUTONOMOUS-EXECUTABLE (same channel as Steps 9C/9E/9F/9G/9H)

---

### Idea 2: Create dependabot-merge-runner SKILL.md
**Evidence:** Morning digests 2026-08-11, 2026-08-12, 2026-08-17 all flag 4+ Dependabot PRs as safe-to-merge with zero automated action. Now 6 open dependabot PRs (#629-631, #649, #665, #666) aging 1-15d. Skill-discovery 2026-08-17 explicitly proposes this skill with detailed evidence. Dependabot PRs have clear merge-safe heuristic (CI green + no review request) requiring no human judgment call.
**Action:** Create .claude/skills/dependabot-merge-runner/SKILL.md — list open dependabot PRs via mcp__github__, check CI status, merge green ones (squash), label CI-failing ones, log results.
**Impact:** ~15 min/week saved, security patches merged faster, morning digest PR noise reduced, 6 current PRs unblocked.
**Category:** workflow
**Effort:** S (new SKILL.md, ~80 lines)
**Status:** AUTONOMOUS-EXECUTABLE by nightly once skill exists (requires nightly to invoke it, or human to run /dependabot-merge-runner)

---

### Idea 3: Create stale-autonomy-pr-closer SKILL.md
**Evidence:** 4 autonomy draft PRs 8-26d old (#575, #626, #648, #653). Skill-discovery 2026-08-17 proposes it. Morning digest flags them daily under "Action needed." PR pile grows because autopilot loop (#399) is blocked — each run opens a new PR but none close. Superseded PRs (#606, #611, #613 from earlier) already confirmed closed.
**Action:** Create .claude/skills/stale-autonomy-pr-closer/SKILL.md — inspect autonomy-authored draft PRs 10+ days old, close superseded ones with comment, label stale-but-valid ones as needs-human-review.
**Impact:** Reduces PR cognitive load for reviewer. Prevents false impression of 10 open items when only 2-3 are actionable.
**Category:** workflow
**Effort:** M (new SKILL.md, complex logic for superseding detection)
**Note:** Risk of closing a valid PR. Needs careful dedup logic.

---

### Idea 4: Post targeted comment on GH #403 with exact ANTHROPIC_API_KEY Railway path
**Evidence:** KB 27 days stale. Root cause: ANTHROPIC_API_KEY missing from GH Actions (#403, day 38+). Morning digest priority #1 for 38 days. Nightly confirms path: "Railway → agentnexlify backend service → Variables tab → ANTHROPIC_API_KEY." A specific, exact-path comment posted directly on GH #403 is more actionable than the morning digest prose.
**Action:** Post GH comment on #403 with exact steps: Railway → agentnexlify service → Variables tab → copy ANTHROPIC_API_KEY → GitHub Settings → Secrets → Actions → New secret → Name: ANTHROPIC_API_KEY.
**Impact:** If human reads and acts: KB goes from 27d stale to fresh in 30 minutes. Direct product quality improvement (AI chat answers use stale KB).
**Category:** operational
**Effort:** XS (one GH comment, no code)
**Note:** One-time action, not structural. Bonus action candidate.

---

### Idea 5: Step 9J — Add Dependabot PR staleness alert to nightly-commit-review SKILL.md
**Evidence:** 6 Dependabot PRs aging 1-15d with zero merge action. Morning digest flags daily. Skill-discovery 2026-08-17 proposes dependabot-merge-runner. Existing Step 9 pattern (9F→9G→9H→9I) proves this channel works for operational alerts. A nightly Step 9J could grep open Dependabot PRs, check CI, and auto-merge green ones (same pattern as Steps 9C/9F/9G).
**Action:** Edit .claude/skills/nightly-commit-review/SKILL.md to add Step 9J: list open Dependabot PRs via gh CLI, for each with CI green status and no requested changes, merge via gh pr merge --squash.
**Impact:** Eliminates Dependabot PR aging permanently. Security patches applied within 24h of bot opening PR.
**Category:** workflow
**Effort:** S (SKILL.md bash block, ~40 lines)
**Note:** Similar to Idea 2 but wired directly into nightly rather than a standalone skill.
