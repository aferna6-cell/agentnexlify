# Run 102 — Candidate Ideas

**Date:** 2026-08-11
**Evidence window:** 2026-08-06 → 2026-08-11

---

## Idea 1 — `pr-backlog-triage` skill (automate PR queue management)

**Category:** workflow
**Channel:** new skill in `.claude/skills/`
**Effort:** S (1 SKILL.md file, ~80 lines)

**Evidence:**
- morning-digest-2026-08-10: 10 open PRs, 6 stale DRAFT autonomy PRs, flagged as Top 2 priority for multiple consecutive days
- skill-discovery-2026-08-10 proposes this skill with full step spec (merge-ready → superseded → stale-draft → active buckets)
- 3 Dependabot PRs (#629, #630, #631) open 7 days, CI green, no one merged them
- PR backlog clog directly delays Step 9G fix (#626) which has been open 8 days
- Pattern recurs: morning-digest-2026-08-07 flagged 8 open PRs with same pattern

**Action:** Create `.claude/skills/pr-backlog-triage/SKILL.md` using the exact spec from skill-discovery-2026-08-10 (list PRs → classify 4 buckets → merge Dependabot → close superseded → label stale-drafts → write log)

**Impact:** 3 Dependabot PRs merge autonomously each week; stale PR pile stops growing; Step 9G fix in #626 would have been surfaced/merged days earlier

---

## Idea 2 — Amend Step 9G to use `mcp__github__actions_run_trigger` as primary path (fix gh CLI absence)

**Category:** operational
**Channel:** `.claude/skills/nightly-commit-review/SKILL.md` (proven XS edit channel)
**Effort:** XS (amend ~10 lines in existing SKILL.md Step 9G block)

**Evidence:**
- nightly-commit-review-2026-08-11 Step 9G output: "TRIGGERED — kb-autopopulate.yml queued on main (via MCP, gh CLI not available)"
- KB last updated 2026-07-23 — still 19 days stale despite Step 9G firing, indicating the trigger did not complete successfully
- Run 101 winning-concept.md specified `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify` as the trigger command — bash `gh` CLI is unavailable in nightly headless sessions
- Other nightly MCP calls confirmed working (GH issue comments via `mcp__github__add_issue_comment` succeed in same sessions)
- `mcp__github__actions_run_trigger` is the MCP equivalent of `gh workflow run` and is available in nightly sessions

**Action:** Amend Step 9G in SKILL.md:
1. Replace `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify` with MCP call `mcp__github__actions_run_trigger(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml", ref="main")`
2. Replace `gh run list` status check with `mcp__github__actions_list(owner="aferna6-cell", repo="agentnexlify", workflow_id="kb-autopopulate.yml", per_page=1)` after 30s
3. Keep the failure → `mcp__github__add_issue_comment` on #403 path unchanged

**Impact:** KB autopopulate fires correctly from nightly sessions; KB staleness alert clears; #403 resolves; 19-day stale KB starts refreshing on next nightly run

---

## Idea 3 — `route-security-guard-audit` skill (catch missing block_demo_role guards)

**Category:** code_health / workflow
**Channel:** new skill in `.claude/skills/`
**Effort:** S (1 SKILL.md file, ~100 lines)

**Evidence:**
- skill-discovery-2026-08-10 proposes this with full 6-step spec; evidence: cbbaae5 (2026-08-07) applied guard on detached HEAD, c204af2 (2026-08-08) re-applied correctly after orphaned commits discovered — same fix applied twice in 48h
- GH #643: "appointment_briefs.py missing block_demo_role + plan gate + ai_usage_guard" — open 4 days, no linked PR, loop is stalled (AUTOPILOT_GH_TOKEN expired), commented in nightly-2026-08-11
- Pattern: each new router is missing the guard until nightly review catches it; re-discovery from `billing.py:33` reference happens every occurrence
- 4 routers currently carry the guard; new routers keep omitting it

**Action:** Create `.claude/skills/route-security-guard-audit/SKILL.md` following 6-step spec from skill-discovery-2026-08-10

**Impact:** ~15 min saved per occurrence; eliminates re-discovery from billing.py:33; nightly review can invoke skill instead of re-deriving the pattern; appointment_briefs.py fix gets a reliable procedure

---

## Idea 4 — Fix appointment_briefs.py missing guards directly (bypass stalled loop)

**Category:** code_health
**Channel:** direct implementation (like Steps 9F/9G precedent)
**Effort:** XS (add 3 guards + structural test, 1 file)

**Evidence:**
- GH #643: "MEDIUM: appointment_briefs.py missing block_demo_role + plan gate + ai_usage_guard" — open 4 days
- nightly-2026-08-11 Step 9D: "STALLED — 5 consecutive failures; #643 open 4 days with no PR; commented #399 + #643"
- AUTOPILOT_GH_TOKEN expired → issue-to-pr-loop cannot generate PR for this issue
- security risk persists with each missed day
- Direct implementation precedent: Steps 9F and 9G both implemented directly after 3+ cycle misses in PR channel

**Action:** Open `backend/routers/appointment_briefs.py`, add `dependencies=[Depends(block_demo_role)]` + plan gate + `ai_usage_guard`, add structural assertion to test file, commit

**Impact:** Security gap closes immediately; #643 resolves; does not wait for AUTOPILOT_GH_TOKEN rotation

**Weakness:** Subconscious mandate is "recommend only, do not implement." Direct implementation breaks the channel boundary even if precedent exists. This issue requires human action or loop restart.

---

## Idea 5 — Add Step 9H: autonomous Dependabot PR merge (extend nightly skill)

**Category:** workflow / operational
**Channel:** `.claude/skills/nightly-commit-review/SKILL.md` (proven XS edit channel)
**Effort:** S (add ~20 lines Step 9H block to existing SKILL.md)

**Evidence:**
- PRs #629/#630/#631: Dependabot bumps open 7 days, CI green (implied by morning digest "ready to merge")
- morning-digest-2026-08-10 Top 2 priority: "Triage the PR backlog — 3 Dependabot PRs ready to merge"
- No current nightly step handles Dependabot PRs autonomously
- Dependabot PRs are the lowest-risk merge: bot-authored, single dependency, CI-gated

**Action:** Add Step 9H to SKILL.md after Step 9G: list PRs filtered by `dependabot` label + CI green + no blocking review → merge via `mcp__github__merge_pull_request`

**Impact:** 3 stale Dependabot PRs merge on next nightly run; queue drains autonomously going forward

**Weakness:** Overlaps significantly with proposed `pr-backlog-triage` skill (Idea 1). Adding Step 9H to SKILL.md while also creating pr-backlog-triage creates two competing automations for the same problem. Better to implement once in the skill.
